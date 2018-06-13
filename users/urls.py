# _*_ coding:utf-8 _*_
from django.conf.urls import url
from users.views import RegisterView, LoginView, LogOutView, UserInfoView,AddressView

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),  # 注册页面
    url(r'^login$', LoginView.as_view(), name='login'),  # 登录页面
    url(r'^logout$', LogOutView.as_view(), name='logout'),  # 登出
    url(r'^$', UserInfoView.as_view(), name='user'),  # 用户中心-信息页面
    url(r'^address$', AddressView.as_view(), name='address'),  # 用户中心-地址信息

]
