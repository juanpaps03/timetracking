from django import template

register = template.Library()


@register.filter
def plus(value):
    return value + 1


@register.filter
def sum_hours(logs):
    if logs:
        sum = 0
        for log in logs:
            sum += log.amount
        return sum
    else:
        return 0
