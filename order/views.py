# _*_ coding:utf-8 _*_
from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import *
from users.models import Address
from order.models import OrderInfo, OrderGoods
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django_redis import get_redis_connection
from utils.util import LoginRequiredMixin
from django.http import JsonResponse
from django.db import transaction
from datetime import datetime
from alipay import AliPay
from django.conf import settings
from django.views.decorators.csrf import csrf_exempt
from alipay.compat import urlopen
import ssl
import os


# Create your views here.


class OrderCreateView(LoginRequiredMixin, View):
    """订单提交页面"""

    def get(self, request):
        user = request.user
        # 从商品详情页进入订单
        count = request.GET['count']
        sku_id = request.GET['sku_id']
        # 校验参数
        if not all([count, sku_id]):
            return JsonResponse({'res': 0, 'errmsg': '数据错误'})

        conn = get_redis_connection('default')
        order_key = 'order_%d' % user.id
        keys = conn.hkeys(order_key)
        print(keys)
        if keys:
            conn.hdel(order_key, *keys)

        conn.hset(order_key, sku_id, count)
        # 商品列表
        skus = []
        # 购物车中商品总数量，总价
        total_count = 0
        total_price = 0

        # 根据id,获取商品信息
        sku = GoodsSKU.objects.get(id=sku_id)
        # 计算商品的小计
        amount = sku.price * int(count)
        # 动态给商品对象增加小计属性
        sku.amount = amount
        # 动态增加商品数量的属性
        sku.count = count

        skus.append(sku)
        total_count += int(count)
        total_price += amount

        # 运费
        transit_price = 0

        # 实际付款
        total_pay = transit_price + total_price

        # 收货地址
        addrs = Address.objects.filter(user=user)

        content = {
            'sku_ids': sku_id,
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'transit_price': transit_price
        }
        return render(request, 'order/order_submit.html', content)

    def post(self, request):
        # 获取用户
        user = request.user

        # 从购物车进入提交订单页
        # 校验参数
        # 获取提交的商品sku
        sku_ids = request.POST.getlist('sku_ids')
        if not sku_ids:
            return redirect(reverse('cart:create'))

        # 从redis中获取订单提交的商品
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # 每次在提交订单页先清空上次的提交订单数据
        order_key = 'order_%d' % user.id
        keys = conn.hkeys(order_key)
        print(keys)
        if keys:
            conn.hdel(order_key, *keys)

        # 商品列表
        skus = []
        # 购物车中商品总数量，总价
        total_count = 0
        total_price = 0

        # 遍历商品信息
        for sku_id in sku_ids:
            # 根据id,获取商品信息
            sku = GoodsSKU.objects.get(id=sku_id)
            count = conn.hget(cart_key, sku_id)
            conn.hset(order_key, sku_id, count)
            # 计算商品的小计
            amount = sku.price * int(count)
            # 动态给商品对象增加小计属性
            sku.amount = amount
            # 动态增加商品数量的属性
            sku.count = count

            skus.append(sku)
            total_count += int(count)
            total_price += amount

        # 运费
        transit_price = 0

        # 实际付款
        total_pay = transit_price + total_price

        # 收货地址
        addrs = Address.objects.filter(user=user)

        sku_ids = ','.join(sku_ids)
        content = {
            'sku_ids': sku_ids,
            'skus': skus,
            'total_count': total_count,
            'total_price': total_price,
            'total_pay': total_pay,
            'addrs': addrs,
            'transit_price': transit_price
        }
        return render(request, 'order/order_submit.html', content)


class OrderCommitView(View):
    """点击提交订单，生成订单数据"""

    # 开启事务
    @transaction.atomic
    def post(self, request):
        # 创建订单
        # 判断是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        # 获取数据
        # sku_ids:  '1,2,3'
        sku_ids = request.POST.get('sku_ids')
        addr_id = request.POST.get('addr_id')
        pay_method = request.POST.get('pay_method')

        # 检验数据
        if not all([sku_ids, addr_id, pay_method]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        if pay_method not in OrderInfo.PAY_METHODS.keys():
            return JsonResponse({'res': 2, 'errmsg': '非法支付方式'})

        # 检查售后地址
        try:
            addr = Address.objects.get(id=addr_id)
        except Exception:
            return JsonResponse({'res': 3, 'errmsg': '收货地址非法'})

        # 创建节点
        save_id = transaction.savepoint()
        # 创建订单
        try:
            # 订单id:时间+用户id:20180620182030+id
            order_id = datetime.now().strftime('%Y%m%d%H%M%S') + str(user.id)

            # 运费
            transit_price = 0

            # 总数和中金额
            total_count = 0
            total_price = 0

            # 创建一条订单记录
            order = OrderInfo.objects.create(order_id=order_id,
                                             user=user,
                                             addr=addr,
                                             pay_method=pay_method,
                                             total_count=total_count,
                                             total_price=total_price,
                                             transit_price=transit_price)

            # 通过sku_ids从redis获取商品的数量
            conn = get_redis_connection('default')
            cart_key = 'cart_%d' % user.id
            order_key = 'order_%d' % user.id

            sku_ids = sku_ids.split(',')
            for sku_id in sku_ids:
                for i in range(3):
                    # 乐观锁
                    # 当数据更新的的时候，采取判断此数据是否更改
                    try:
                        sku = GoodsSKU.objects.get(id=sku_id)
                    except GoodsSKU.DoesNotExist:
                        # 回滚到节点
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 4, 'errmsg': '商品部存在'})

                    # 从redis中获取用户所要购买的商品数量
                    count = conn.hget(order_key, sku_id)

                    # 判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # 想order_goods表中添加一条记录
                    OrderGoods.objects.create(order=order,
                                              sku=sku,
                                              count=count,
                                              price=sku.price)

                    # 更新商品库存和销量
                    orgin_stock = sku.stock
                    new_stock = orgin_stock - int(count)
                    new_sales = sku.sales + int(count)

                    # 返回受影响的行数
                    res = GoodsSKU.objects.filter(id=sku_id, stock=orgin_stock).update(stock=new_stock, sales=new_sales)
                    if res == 0:
                        # 如果受影响的行数为0,则说明此数据已经被修改，重新进行库存更新
                        # 防止并发
                        if i == 2:
                            # 尝试三次
                            transaction.savepoint_rollback(save_id)
                            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})
                        continue

                    # 累加计算订单商品的总数量和总价格
                    amount = sku.price * int(count)
                    total_count += int(count)
                    total_price += amount

                    # 跳出循环
                    break

                # 更新订单信息表中的商品的总数量和总价格
                order.total_price = total_price
                order.total_count = total_count
                order.save()


        except Exception:
            transaction.savepoint_rollback(save_id)
            return JsonResponse({'res': 7, 'errmsg': '下单失败'})

        # 提交到数据库
        transaction.savepoint_commit(save_id)

        # 清除用户购物车中相对应的记录
        conn.hdel(cart_key, *sku_ids)
        # 清除临时订单的记录
        conn.hdel(order_key, *sku_ids)

        return JsonResponse({'res': 5, 'errmsg': '创建成功'})


class OrderPayView(View):
    """订单支付"""

    def post(self, request):

        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        order_id = request.POST.get('order_id')

        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单不存在'})

        # 使用python-alipay-sdk 调用阿里支付
        alipay = AliPay(
            appid='2016091300502975',  # 应用id
            app_notify_url=None,  # 默认回调url,异步调用
            app_private_key_path=os.path.join(settings.BASE_DIR, 'order/rsa_private_key.pem'),
            # 支付宝公钥，验证支付宝回传消息使用
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'order/alipay_public_key.pem'),
            sign_type='RSA2',
            debug=True
        )

        # 调用支付接口
        # 电脑网站支付，需要跳转到https://openapi.alipaydev.com/gateway.do?+order_string

        total_pay = order.total_price + order.transit_price
        order_string = alipay.api_alipay_trade_page_pay(
            subject='dailyfresh%s' % order_id,
            out_trade_no=order_id,
            total_amount=str(total_pay),
            return_url=None,  # 同步返回参数
            notify_url=None  # 可选，不填使用默认的notify url
        )

        pay_url = 'https://openapi.alipaydev.com/gateway.do?' + order_string
        return JsonResponse({'res': 3, 'pay_url': pay_url})


class CheckPayView(View):
    """订单支付结果查询"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        order_id = request.POST.get('order_id')

        if not order_id:
            return JsonResponse({'res': 1, 'errmsg': '无效的订单'})

        try:
            order = OrderInfo.objects.get(order_id=order_id,
                                          user=user,
                                          order_status=1)
        except OrderInfo.DoesNotExist:
            return JsonResponse({'res': 2, 'errmsg': '订单不存在'})

        # 使用python-alipay-sdk 调用阿里支付
        alipay = SSLAliPay(
            appid='2016091300502975',  # 应用id
            app_notify_url=None,  # 默认回调url,异步调用
            app_private_key_path=os.path.join(settings.BASE_DIR, 'order/rsa_private_key.pem'),
            # 支付宝公钥，验证支付宝回传消息使用
            alipay_public_key_path=os.path.join(settings.BASE_DIR, 'order/alipay_public_key.pem'),
            sign_type='RSA2',
            debug=True
        )

        for i in range(5):
            print(order_id)
            response = alipay.api_alipay_trade_query(order_id)
            print(response)

            code = response.get('code')

            if code == '10000' and response.get('trade_status') == 'TRADE_SUCCESS':
                # 获取支付宝交易号
                trade_no = response.get('trade_no')
                order.trade_no = trade_no
                order.order_status = 4  # 待评价
                order.save()
                return JsonResponse({'res': 3, 'errmsg': '支付成功'})
            elif code == '40004' or (code == '10000' and response.get('trade_status') == 'WAIT_BUYER_PAY'):
                # 等待买家付款
                # 业务处理失败，可能一会才会成功
                if i == 4:
                    print(code)
                    return JsonResponse({'res': 4, 'errmsg': '支付失败'})
                else:
                    import time
                    time.sleep(5)
                    continue

            else:
                print(code)
                return JsonResponse({'res': 4, 'errmsg': '支付失败'})

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(CheckPayView, self).dispatch(request, *args, **kwargs)


class CommentView(LoginRequiredMixin, View):
    """订单评论"""

    def get(self, request, order_id):
        user = request.user

        if not order_id:
            return redirect(reverse('user:order', kwargs={'page': 1}))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order', kwargs={'page': 1}))

        order.status_name = OrderInfo.ORDER_STATUS[order.order_status]

        order_skus = OrderGoods.objects.filter(order_id=order_id)

        for order_sku in order_skus:
            amount = order_sku.count * order_sku.price
            order_sku.amount = amount

        order.order_skus = order_skus

        return render(request, 'order/order_comment.html', {'order': order})

    def post(self, request, order_id):
        user = request.user

        if not order_id:
            return redirect(reverse('user:order', kwargs={'page': 1}))

        try:
            order = OrderInfo.objects.get(order_id=order_id, user=user)
        except OrderInfo.DoesNotExist:
            return redirect(reverse('user:order'))

        total_count = request.POST.get('total_count')
        for i in range(1, int(total_count) + 1):
            sku_id = request.POST.get('sku_%d' % i)
            content = request.POST.get('content_%d' % i)
            try:
                order_goods = OrderGoods.objects.get(order=order, sku_id=sku_id)
            except OrderGoods.DoesNotExist:
                continue
            order_goods.comment = content
            order_goods.save()

        order.order_status = 5
        order.save()

        return redirect(reverse('user:order', kwargs={'page': 1}))


context = ssl._create_unverified_context()


class SSLAliPay(AliPay):
    def api_alipay_trade_query(self, out_trade_no=None, trade_no=None):
        """
        response = {
          "alipay_trade_query_response": {
            "trade_no": "2017032121001004070200176844",
            "code": "10000",
            "invoice_amount": "20.00",
            "open_id": "20880072506750308812798160715407",
            "fund_bill_list": [
              {
                "amount": "20.00",
                "fund_channel": "ALIPAYACCOUNT"
              }
            ],
            "buyer_logon_id": "csq***@sandbox.com",
            "send_pay_date": "2017-03-21 13:29:17",
            "receipt_amount": "20.00",
            "out_trade_no": "out_trade_no15",
            "buyer_pay_amount": "20.00",
            "buyer_user_id": "2088102169481075",
            "msg": "Success",
            "point_amount": "0.00",
            "trade_status": "TRADE_SUCCESS",
            "total_amount": "20.00"
          },
          "sign": ""
        }
        """
        assert (out_trade_no is not None) or (trade_no is not None), \
            "Both trade_no and out_trade_no are None"

        biz_content = {}
        if out_trade_no:
            biz_content["out_trade_no"] = out_trade_no
        if trade_no:
            biz_content["trade_no"] = trade_no
        data = self.build_body("alipay.trade.query", biz_content)

        url = self._gateway + "?" + self.sign_data(data)
        raw_string = urlopen(url, timeout=15, context=context).read().decode("utf-8")
        return self._verify_and_return_sync_response(raw_string, "alipay_trade_query_response")
