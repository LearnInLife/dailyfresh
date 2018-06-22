# _*_ coding:utf-8 _*_
from django.shortcuts import render, redirect
from django.views.generic import View
from users.models import User, Address
from goods.models import GoodsSKU
from order.models import OrderInfo, OrderGoods
import re
from hashlib import sha1
from django.core.urlresolvers import reverse
from django.contrib.auth import authenticate, login, logout
from utils.util import LoginRequiredMixin
from django_redis import get_redis_connection
from django.core.paginator import Paginator


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


class UserInfoView(LoginRequiredMixin, View):
    """用户个人中心-基本信息"""

    def get(self, request):
        """显示"""
        # Django会给request对象添加一个属性request.user
        # 如果用户未登录->user是AnonymousUser类的一个实例对象
        # 如果用户登录->user是User类的一个实例对象
        # request.user.is_authenticated()

        # 获取用户的个人信息
        user = request.user
        addr = Address.objects.get_default_address(user)

        # 获取用户的历史浏览记录
        conn = get_redis_connection('default')

        # 根据用户id生成的存储key值
        history_key = 'history_%d' % user.id
        # 得到用户最近浏览的10个商品id
        sku_ids = conn.lrange(history_key, 0, 9)

        goods_li = []
        for id in sku_ids:
            good = GoodsSKU.objects.get(id=id)
            goods_li.append(good)

        content = {'page': 'user', 'address': addr, 'goods_li': goods_li}

        return render(request, 'user/user_center_info.html', content)


class AddressView(LoginRequiredMixin, View):
    """用户个人中-地址信息"""

    def get(self, request):
        # 获取当前登录用户
        user = request.user
        # 查询是该用户关联的地址
        address_li = user.address_set.all()
        print(address_li)
        return render(request, 'user/user_center_site.html', {'page': 'address', 'address_li': address_li})

    def post(self, request):
        """添加收货地址"""
        # 获取上传数据
        receiver = request.POST.get('receiver')
        addr = request.POST.get('addr')
        zip_code = request.POST.get('zip_code')
        phone = request.POST.get('phone')

        # 检验数据是否完整
        if not all([receiver, addr, phone]):
            return render(request, 'user/user_center_site.html', {'errmsg': '数据不完整'})
        # 校验手机是否正确
        if not re.match(r'^1[3|4|5|7|8][0-9]{9}$', phone):
            return render(request, 'user/user_center_site.html', {'errmsg': '手机号不正确'})

        user = request.user
        # 查询是否存在默认地址
        address = Address.objects.get_default_address(user)
        if address:
            is_default = False
        else:
            is_default = True

        # 添加收货地址
        Address.objects.create(user=user,
                               receiver=receiver,
                               addr=addr,
                               phone=phone,
                               zip_code=zip_code,
                               is_default=is_default)
        return redirect(reverse('user:address'))


class UserCenterOrderView(LoginRequiredMixin, View):
    """用户中心订单类"""

    def get(self, request, page):

        user = request.user
        orders = OrderInfo.objects.filter(user=user).order_by('-create_time')

        for order in orders:
            # 根据订单信息查询订单商品信息
            order_skus = OrderGoods.objects.filter(order_id=order.order_id)

            # 计算订单商品中的商品小计
            for order_sku in order_skus:
                amount = order_sku.count * order_sku.price
                order_sku.amount = amount

            # 保存订单状态的标志
            order.status_name = OrderInfo.ORDER_STATUS[order.order_status]
            # 保存订单商品信息
            order.order_skus = order_skus

        # 分页
        paginator = Paginator(orders, 3)

        # 获取第page页的内容
        try:
            page = int(page)
        except Exception:
            page = 1

        if page > paginator.num_pages:
            page = 1

        order_page = paginator.page(page)

        #  进行页码的控制，页面上最多显示5个页码
        # 1.总页数小于5页，页面上显示所有页码
        # 2.如果当前页是前3页，显示1-5页
        # 3.如果当前页是后3页，显示后5页
        # 4.其他情况，显示当前页的前2页，当前页，当前页的后2页

        # 获取分页总数
        num_pages = paginator.num_pages
        if num_pages < 5:
            pages = range(1, num_pages + 1)
        elif page <= 3:
            pages = range(1, 6)
        elif num_pages - page >= 2:
            pages = range(num_pages - 4, num_pages + 1)
        else:
            pages = range(page - 2, page + 3)

        content = {
            'pages': pages,
            'order_page': order_page,
            'page': 'order'
        }

        return render(request, 'user/user_center_order.html', content)
