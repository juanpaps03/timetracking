from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from collections import OrderedDict

from tracker.models import Building, Workday, LogHour, Task
from .models import User

admin.site.register(Building)
admin.site.register(LogHour)
admin.site.register(Task)


@admin.register(Workday)
class WorkdayAdmin(admin.ModelAdmin):

    def save_model(self, request, obj, form, change):
        obj.overseer = obj.building.overseer
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        return ('overseer',)



# Manager group and permissions
manager_group, created = Group.objects.get_or_create(name='Manager')

content_type = ContentType.objects.get_for_model(Building)
permissions = Permission.objects.filter(content_type=content_type)
for p in permissions:
    manager_group.permissions.add(p)

content_type = ContentType.objects.get_for_model(Workday)
permissions = Permission.objects.filter(content_type=content_type)
for p in permissions:
    manager_group.permissions.add(p)

content_type = ContentType.objects.get_for_model(LogHour)
permissions = Permission.objects.filter(content_type=content_type)
for p in permissions:
    manager_group.permissions.add(p)

content_type = ContentType.objects.get_for_model(Task)
permissions = Permission.objects.filter(content_type=content_type)
for p in permissions:
    manager_group.permissions.add(p)

content_type = ContentType.objects.get_for_model(User)
permissions = Permission.objects.filter(content_type=content_type)
for p in permissions:
    if p.codename != "delete_user":
        manager_group.permissions.add(p)

manager_group.save()
