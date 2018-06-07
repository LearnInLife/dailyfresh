# _*_ coding:utf-8 _*_
from django.shortcuts import render
from django.views.generic import View
from django.contrib.auth.models import AbstractUser


# Create your views here.

class User(AbstractUser):
    pass
class IndexView(View):
    """首页类"""

    def get(self, request):
        # 显示首页
        user = request.user
        print(user.is_authenticated())

        # 获取登录对象

        return render(request, 'goods/index.html', {'cart_count': 1})

