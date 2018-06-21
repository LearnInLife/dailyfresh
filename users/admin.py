# _*_ coding:utf-8 _*_
from django.contrib import admin
from users.models import User,Address

# Register your models here.

admin.site.register(User)
admin.site.register(Address)
