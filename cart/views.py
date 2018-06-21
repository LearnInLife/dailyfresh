# _*_ coding:utf-8 _*_
from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import *
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django_redis import get_redis_connection
from django.core.paginator import Paginator
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt


class CartInfoView(View):
    """购物车页面"""

    def get(self, request):
        # 获取请求用户
        user = request.user
        # 根据用户从redis中获取购物车中的商品信息
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        # {'商品id':商品数量, ...}
        cart_dict = conn.hgetall(cart_key)

        # 商品列表
        skus = []
        # 购物车中商品总数量，总价
        total_count = 0
        total_price = 0

        # 遍历商品信息
        for sku_id, count in cart_dict.items():
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

        content = {
            'total_count': total_count,
            'total_price': total_price,
            'skus': skus
        }

        return render(request, 'cart/cart.html', content)


class CartAddView(View):
    """购物车添加"""

    def post(self, request):
        # 判断用户是否登录
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        # 获取接收的数据
        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        # 检查数据是否完整
        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            count = int(count)
        except Exception:
            return JsonResponse({'res': 2, 'errmsg': '商品数量输入有误'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoseNotExist:
            return JsonResponse({'res': 3, 'errmsg': '购买的商品不存在'})

        # 先尝试获取sku_id的值 -> hget cart_key 属性
        # 如果sku_id在hash中不存在，hget返回None
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        cart_count = conn.hget(cart_key, sku_id)
        if cart_count:
            count += int(cart_count)

        # 检查商品数量是否超出库存
        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 设置hash中sku_id对应的值
        # hset->如果sku_id已经存在，更新数据， 如果sku_id不存在，添加数据
        conn.hset(cart_key, sku_id, count)

        # 计算购物车的条目数
        total_count = conn.hlen(cart_key)

        return JsonResponse({
            'res': 5,
            'total_count': total_count,
            'errmsg': '添加成功'
        })

    @csrf_exempt
    def dispatch(self, request, *args, **kwargs):
        return super(CartAddView, self).dispatch(request, *args, **kwargs)


class CartUpdateView(View):
    """更新购物车"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        sku_id = request.POST.get('sku_id')
        count = request.POST.get('count')

        if not all([sku_id, count]):
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            count = int(count)
        except Exception:
            return JsonResponse({'res': 2, 'errmsg': '商品数量输入有误'})

        try:
            sku = GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoseNotExist:
            return JsonResponse({'res': 3, 'errmsg': '购买的商品不存在'})

        # 先尝试获取sku_id的值 -> hget cart_key 属性
        # 如果sku_id在hash中不存在，hget返回None
        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        if count > sku.stock:
            return JsonResponse({'res': 4, 'errmsg': '商品库存不足'})

        # 更新数量
        conn.hset(cart_key, sku_id, count)

        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({
            'res': 5,
            'total_count': total_count,
            'errmsg': '添加成功'
        })


class CartDeleteView(View):
    """删除购物车商品"""

    def post(self, request):
        user = request.user
        if not user.is_authenticated():
            return JsonResponse({'res': 0, 'errmsg': '请登录'})

        # 获取接收的数据
        sku_id = request.POST.get('sku_id')

        # 检查数据是否完整
        if not sku_id:
            return JsonResponse({'res': 1, 'errmsg': '数据不完整'})

        try:
            GoodsSKU.objects.get(id=sku_id)
        except GoodsSKU.DoseNotExist:
            return JsonResponse({'res': 2, 'errmsg': '购买的商品不存在'})

        conn = get_redis_connection('default')
        cart_key = 'cart_%d' % user.id

        conn.hdel(cart_key, sku_id)

        total_count = 0
        vals = conn.hvals(cart_key)
        for val in vals:
            total_count += int(val)

        return JsonResponse({
            'res': 3,
            'total_count': total_count,
            'errmsg': '添加成功'
        })
