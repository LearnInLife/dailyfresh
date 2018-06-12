# _*_ coding:utf-8 _*_
from django.db import models
from db.base_model import BaseModel
from tinymce.models import HTMLField


# Create your models here.


class GoodsType(BaseModel):
    """商品类型模型类"""
    name = models.CharField(max_length=20, verbose_name='种类名称')
    logo = models.CharField(max_length=20, verbose_name='标识')
    image = models.ImageField(upload_to='type', verbose_name='商品类型图片')

    class Meta:
        db_table = 'df_goods_type'
        verbose_name = '商品种类'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    # 用于在列表页面显示图片
    def image_show(self):
        return '<img src="/media/%s" width=100px height=100px/>' % self.image

    image_show.allow_tags = True
    image_show.short_description = '类型图片'


class GoodsSKU(BaseModel):
    """
    商品SKU模型类
    SKU是库存量单位，区分单品
    通常表示一个产品的属性比如规格，尺寸，颜色等
    SKU就是商品的“件”
    """
    status_choices = (
        (0, '下线'),
        (1, '上线')
    )

    type = models.ForeignKey('GoodsType', verbose_name='商品种类')
    goods = models.ForeignKey('Goods', verbose_name='商品spu')
    name = models.CharField(max_length=20, verbose_name='商品名称')
    desc = models.CharField(max_length=256, verbose_name='商品简介')
    price = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='商品价格')
    unite = models.CharField(max_length=20, verbose_name='商品单位')
    image = models.ImageField(upload_to='goods', verbose_name='商品图片')
    stock = models.IntegerField(default=1, verbose_name='商品库存')
    sales = models.IntegerField(default=0, verbose_name='商品销量')
    status = models.SmallIntegerField(default=1, choices=status_choices, verbose_name='商品状态')

    class Meta:
        db_table = 'df_goods_sku'
        verbose_name = '商品'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name

    def image_show(self):
        return '<img src="/media/%s" width=100px height=100px/>' % self.image

    image_show.allow_tags = True
    image_show.short_description = '商品图片'


class Goods(BaseModel):
    """
    商品SPU模型
    SPU是标准化产品单元，区分品种
    通常被称作父产品，下面存在一个或者多个sku
    SPU就是俗称的“款”
    """
    name = models.CharField(max_length=20, verbose_name='商品spu名称')
    # 富文本类型:带有格式的文本
    detail = HTMLField(blank=True, verbose_name='商品详情')

    class Meta:
        db_table = 'df_goods'
        verbose_name = '商品SPU'
        verbose_name_plural = verbose_name

    def __str__(self):
        return self.name


class GoodsImage(BaseModel):
    """商品图片模型类"""
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品')
    image = models.ImageField(upload_to='goods', verbose_name='图片路径')

    class Meta:
        db_table = 'df_goods_image'
        verbose_name = '商品图片'
        verbose_name_plural = verbose_name


class IndexGoodsBanner(BaseModel):
    """首页轮播商品展示模型类"""
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品')
    image = models.ImageField(upload_to='banner', verbose_name='图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'df_index_banner'
        verbose_name = '首页轮播商品'
        verbose_name_plural = verbose_name

    def image_show(self):
        return '<img src="/media/%s" width=200px height=100px/>' % self.image

    image_show.allow_tags = True
    image_show.short_description = '首页轮播图片'


class IndexTypeGoodsBanner(BaseModel):
    """首页分类商品展示模型类"""
    DISPLAY_TYPE_CHOICES = (
        (0, "标题"),
        (1, "图片")
    )

    type = models.ForeignKey('GoodsType', verbose_name='商品类型')
    sku = models.ForeignKey('GoodsSKU', verbose_name='商品SKU')
    display_type = models.SmallIntegerField(default=1, choices=DISPLAY_TYPE_CHOICES, verbose_name='展示类型')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'df_index_type_goods'
        verbose_name = "主页分类展示商品"
        verbose_name_plural = verbose_name


class IndexPromotionBanner(BaseModel):
    """首页促销活动模型类"""
    name = models.CharField(max_length=20, verbose_name='活动名称')
    url = models.CharField(max_length=256, verbose_name='活动链接')
    image = models.ImageField(upload_to='banner', verbose_name='活动图片')
    index = models.SmallIntegerField(default=0, verbose_name='展示顺序')

    class Meta:
        db_table = 'df_index_promotion'
        verbose_name = "主页促销活动"
        verbose_name_plural = verbose_name

    def image_show(self):
        return '<img src="/media/%s" width=200px height=100px/>' % self.image

    image_show.allow_tags = True
    image_show.short_description = '促销图片'
