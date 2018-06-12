# _*_ coding:utf-8 _*_
from django.conf.urls import url
from goods.views import IndexView, DetailView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
    url(r'detail/(?P<goods_id>\d+)$', DetailView.as_view(), name='detail'),
]
