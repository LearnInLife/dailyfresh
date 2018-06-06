# _*_ coding:utf-8 _*_
from django.shortcuts import render, redirect
from django.views.generic import View
from users.models import User
import re
from hashlib import sha1
from django.core.urlresolvers import reverse

import logging


# Create your views here.

class RegisterView(View):
    """注册类"""

    def get(self, request):
        # 显示注册页面
        return render(request, 'user/register.html')

    def post(self, request):
        """注册提交处理"""

        # 接收参数
        username = request.POST.get('user_name')
        pwd = request.POST.get('pwd')
        email = request.POST.get('email')

        print(pwd)

        # 数据检验
        if not all([username, pwd, email]):
            return render(request, 'user/register.html', {'errmsg': '数据不完整'})

        # 邮箱校验
        if not re.match(r'^[a-z0-9][\w.\-]*@[a-a0-9\-]+(\.[a-z]{2,5}){1,2}$', email):
            return render(request, 'user/register.html', {'errmsg': '邮箱格式不正确'})

        # 校验是否存在相同的用户名
        if User.objects.filter(username=username):
            return render(request, 'user/register.html', {'errmsg': '用户名已存在'})

        sh1 = sha1()
        sh1.update(str(pwd).encode('utf-8'))
        user = User.objects.create_user(username, email, sh1.hexdigest())
        user.is_active = 0
        user.save()

        return redirect(reverse('user:login'))


class LoginView(View):
    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''
        return render(request, 'user/login.html', {'username': username, 'checked': checked})

    def post(self, request):
        pass
