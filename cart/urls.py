# _*_ coding:utf-8 _*_
from django.conf.urls import url
from cart.views import CartInfoView, CartAddView, CartDeleteView, CartUpdateView

urlpatterns = [
    url(r'^$', CartInfoView.as_view(), name='cart'),
    url(r'^add$', CartAddView.as_view(), name='add_to_cart'),
    url(r'^update$', CartUpdateView.as_view(), name='update'),
    url(r'^delete$', CartDeleteView.as_view(), name='delete'),
]
