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


# Create your views here.


class OrderCreateView(LoginRequiredMixin, View):
    """订单提交页面"""

    def post(self, request):
        # 获取用户
        user = request.user
        # 获取提交的商品sku
        sku_ids = request.POST.getlist('sku_ids')
        # 校验参数
        if not sku_ids:
            return redirect(reverse('cart:create'))

        # 从redis中获取订单提交的商品
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

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
        transit_price = 10

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
            transit_price = 10

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
                    count = conn.hget(cart_key, sku_id)

                    # 判断商品的库存
                    if int(count) > sku.stock:
                        transaction.savepoint_rollback(save_id)
                        return JsonResponse({'res': 6, 'errmsg': '商品库存不足'})

                    # 想order_goods表中添加一条几率
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

        return JsonResponse({'res': 5, 'errmsg': '创建成功'})
