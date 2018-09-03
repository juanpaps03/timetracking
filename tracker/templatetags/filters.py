from django import template

from tracker.models import LogHour

register = template.Library()


@register.filter
def sum_hours(logs):
    return LogHour.sum_hours(logs)

@register.filter
def ellipsize(things, amount):
    x = ""
    if len(things) > amount:
        x += str(things[0])
        for i in range(1, amount):
            x += ", " + str(things[i])
        x += " and " + str(len(things)-amount) + " more"
    elif things:
        x += str(things[0])
        for i in range(1, len(things)-1):
            x += ", " + str(things[i])
        if len(things) > 1:
            x += " and " + str(things[len(things)-1])
    return x
