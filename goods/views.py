# _*_ coding:utf-8 _*_
from django.shortcuts import render, redirect
from django.views.generic import View
from goods.models import *
from django.core.urlresolvers import reverse
from django.core.cache import cache
from django_redis import get_redis_connection


# Create your views here.

class IndexView(View):
    """首页类"""

    def get(self, request):
        # 显示首页

        # 获取商品的种类信息
        types = GoodsType.objects.all()
        # 获取首页banner
        goods_banners = IndexGoodsBanner.objects.all().order_by('index')
        # 获取首页促销活动信息
        promotion_banners = IndexPromotionBanner.objects.all().order_by('index')

        # 获取分类商品的展示信息
        for type_list in types:
            # 获取分类商品中的图片展示信息
            image_banners = IndexTypeGoodsBanner.objects.filter(type=type_list, display_type=1).order_by('index')
            # 获取分类商品中的文字展示信息
            title_banners = IndexTypeGoodsBanner.objects.filter(type=type_list, display_type=0).order_by('index')

            type_list.image_banners = image_banners
            type_list.title_banners = title_banners

        # 组织模板上下文
        content = {
            'types': types,
            'goods_banners': goods_banners,
            'promotion_banners': promotion_banners
        }

        # 获取登录对象
        user = request.user
        print(user.is_authenticated())

        # 传入购物车数量
        content.update(cart_count=10)

        return render(request, 'goods/index.html', content)


class DetailView(View):
    """商品详情页"""

    def get(self, request, goods_id):
        # 通过id 查询商品id
        try:
            sku = GoodsSKU.objects.get(id=goods_id)
        except:
            # 商品不存在，返回首页
            return redirect(reverse('/'))

        # 获取商品分类信息
        types = GoodsType.objects.all()

        # 获取商品的评论信息
        sku_order_comment = []

        # 获取新品信息，添加时间最晚的两个为新品
        new_skus = GoodsSKU.objects.filter(type=sku.type).order_by('-create_time')[:2]
        # 获取同类商品信息
        same_sku = GoodsSKU.objects.filter(goods=sku.goods).exclude(id=goods_id)

        # 获取用户购物车数量
        user = request.user
        cart_count = 0
        if user.is_authenticated():
            # 用户购物车数量

            # 添加用户历史浏览记录
            conn = get_redis_connection('default')
            history_key = 'history_%d' % user.id
            # 删除列表中的存在的已经浏览的goods_id
            conn.lrem(history_key, 0, goods_id)
            # 将用户浏览记录添加进列表
            conn.lpush(history_key, goods_id)
            # 只保留用户最近浏览的10条记录
            conn.ltrim(history_key, 0, 9)

        content = {
            'types': types,
            'sku_order_comment': sku_order_comment,
            'new_skus': new_skus,
            'same_sku': same_sku,
            'sku': sku,
            'cart_count': cart_count
        }
        return render(request, 'goods/detail.html', content)
