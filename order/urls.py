# _*_ coding:utf-8 _*_
from django.conf.urls import url
from order.views import OrderCreateView, OrderCommitView

urlpatterns = [
    url(r'^$', OrderCreateView.as_view(), name='create'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit')
]
