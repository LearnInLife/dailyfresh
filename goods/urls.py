# _*_ coding:utf-8 _*_
from django.conf.urls import url
from goods.views import IndexView, DetailView, GoodsListView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'detail/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'),
    url(r'list/(?P<type_id>\d+)/(?P<page>\d+)$', GoodsListView.as_view(), name='list')
]
