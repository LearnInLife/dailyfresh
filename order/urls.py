# _*_ coding:utf-8 _*_
from django.conf.urls import url
from order.views import OrderCreateView, OrderCommitView, OrderPayView, CheckPayView, CommentView

urlpatterns = [
    url(r'^$', OrderCreateView.as_view(), name='create'),
    url(r'^commit$', OrderCommitView.as_view(), name='commit'),
    url(r'^pay$', OrderPayView.as_view(), name='pay'),
    url(r'^check$', CheckPayView.as_view(), name='check'),
    url(r'^comment/(?P<order_id>.+)$', CommentView.as_view(), name='comment')
]
