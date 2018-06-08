# _*_ coding:utf-8 _*_
from django.contrib import admin
from goods.models import *
from form_utils.widgets import ImageWidget

from utils.widgets import ThumbImageWidget

# Register your models here.
admin.site.site_header = '生鲜管理后台'


class GoodsSKUInLine(admin.TabularInline):
    model = GoodsSKU
    # 编辑页缩略图
    formfield_overrides = {models.ImageField: {'widget': ThumbImageWidget}}


class GoodsTypeAdmin(admin.ModelAdmin):
    list_display = ['id', 'name', 'image_show', 'is_delete']
    list_filter = ['is_delete']
    list_per_page = 20
    # 用于在编辑页面显示图片
    formfield_overrides = {models.ImageField: {'widget': ImageWidget}}
    inlines = [
        GoodsSKUInLine,
    ]


class GoodsAdmin(admin.ModelAdmin):
    list_display = ['id', 'name']
    list_per_page = 20
    inlines = [
        GoodsSKUInLine,
    ]


class GoodsSKUAdmin(admin.ModelAdmin):
    list_display = ['name', 'type', 'goods', 'price', 'stock', 'sales']
    list_filter = ['status', 'goods', 'type']

    list_per_page = 20


class IndexGoodsBannerAdmin(admin.ModelAdmin):
    list_display = ['id', 'sku', 'image_show', 'index']
    list_per_page = 20
    # 用于在编辑页面显示图片
    formfield_overrides = {models.ImageField: {'widget': ImageWidget}}


admin.site.register(GoodsType, GoodsTypeAdmin)
admin.site.register(IndexGoodsBanner, IndexGoodsBannerAdmin)
admin.site.register(IndexPromotionBanner)
admin.site.register(IndexTypeGoodsBanner)
admin.site.register(GoodsSKU, GoodsSKUAdmin)
admin.site.register(Goods, GoodsAdmin)
