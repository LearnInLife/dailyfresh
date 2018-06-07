# _*_ coding:utf-8 _*_
from django.conf.urls import url
from goods.views import IndexView

urlpatterns = [
    url(r'^$', IndexView.as_view(), name='index'),
]
