# _*_ coding:utf-8 _*_
from django.conf.urls import url
from users.views import RegisterView, LoginView,LogOutView

urlpatterns = [
    url(r'^register$', RegisterView.as_view(), name='register'),
    url(r'^login$', LoginView.as_view(), name='login'),
    url(r'logout',LogOutView.as_view(),name='logout')
]
