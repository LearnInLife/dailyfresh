from django.template import Library

register = Library()


@register.filter
def my_add(a, b):
    return a * b
