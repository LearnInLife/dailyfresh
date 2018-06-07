# _*_ coding:utf-8 _*_
from django.shortcuts import render, redirect
from django.views.generic import View
from users.models import User
import re
from hashlib import sha1
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout

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
    """登陆"""

    def get(self, request):
        if 'username' in request.COOKIES:
            username = request.COOKIES.get('username')
            checked = 'checked'
        else:
            username = ''
            checked = ''

        context = {'error_name': 0, 'error_pwd': 0, 'username': username, 'checked': checked}
        return render(request, 'user/login.html', context)

    def post(self, request):
        """登录校验"""
        # 接收数据
        username = request.POST.get('username')
        pwd = request.POST.get('pwd')
        checked = request.POST.get('remember')

        # 校验数据
        if not all([username, pwd]):
            return render(request, 'user/login.html', {'errmsg': '数据不完整'})

        # 业务处理:登录校验
        sh1 = sha1()
        sh1.update(str(pwd).encode('utf-8'))
        sh1_pwd = sh1.hexdigest()
        user = authenticate(username=username, password=sh1_pwd)
        if user is not None:
            # 用户名密码正确
            # 记录用户的登录状态
            login(request, user)
            # 获取登录后所要跳转到的地址
            # 默认跳转到首页
            next_url = request.GET.get('next', reverse('goods:index'))
            response = redirect(next_url)

            if checked == 'on':
                # 记住用户名
                response.set_cookie('username', username, max_age=7 * 24 * 3600)
            else:
                # 清除用户名（实际上是给cookie设置过期时间）
                response.delete_cookie('username')
                # 跳转到next_url
            return response

        else:
            # 用户名或密码错误
            context = {'error_name': 1, 'error_pwd': 1, 'username': username}
            return render(request, 'user/login.html', context)


class LogOutView(View):
    def get(self, requeset):
        """退出登录"""
        logout(requeset)
        return redirect('/')
