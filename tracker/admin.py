from functools import update_wrapper

from django.conf.urls import url
from django.contrib import admin
from django.contrib.auth.models import Group, Permission
from django.contrib.contenttypes.models import ContentType
from django.http import HttpResponse, JsonResponse
from django.shortcuts import render
from django.urls import reverse
from django.utils import timezone
from django.utils.html import format_html
from django.utils.translation import ugettext_lazy as _
from rest_framework.decorators import api_view

from config import constants, messages
from tracker.models import Building, Workday, LogHour, Task
from .models import User

admin.site.register(LogHour)
admin.site.register(Task)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('code', 'address', 'report_buttons')

    def report_buttons(self, obj):
        return format_html('<a class="button" target="_blank" href="{}">{}</a>',
                           reverse('admin:building_reports', kwargs={'building': obj.code}),
                           _('Make Reports')
                           )
    report_buttons.short_description = 'Monthly Reports'

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = super().get_urls()
        my_urls = [
            url(r'(?P<building>\d+)/report/$', wrap(monthly_reports), name='building_reports'),
        ]
        return my_urls + urls


@admin.register(Workday)
class WorkdayAdmin(admin.ModelAdmin):
    def save_model(self, request, obj, form, change):
        obj.overseer = obj.building.overseer
        super().save_model(request, obj, form, change)

    def get_readonly_fields(self, request, obj=None):
        return 'overseer',

    list_display = ('date', 'building', 'report_buttons')

    def report_buttons(self, obj):
        return format_html('<a class="button" target="_blank" href="{}">{}</a>',
                           reverse('admin:workday_daily_report', kwargs={'building': obj.building, 'date': obj.date}),
                           _('Download Report')
                           )
    report_buttons.short_description = 'Daily Reports'

    def get_urls(self):
        def wrap(view):
            def wrapper(*args, **kwargs):
                return self.admin_site.admin_view(view)(*args, **kwargs)
            wrapper.model_admin = self
            return update_wrapper(wrapper, view)

        urls = super().get_urls()
        my_urls = [
            url(r'(?P<building>\d+)/(?P<date>\d{4}-\d{2}-\d{2})/report/$', wrap(daily_report_download), name='workday_daily_report'),
        ]
        return my_urls + urls


# Creating manager group and permissions
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

# absence task creation.
absence_task, created = Task.objects.get_or_create(code=constants.ABSENCE_CODE,
                                                   name=_('Absence'),
                                                   description=_('Auto-generated task that designates partial or total worker absence for a day.'))
absence_task.buildings = Building.objects.all()
absence_task.save()

# custom views
@api_view(['GET', 'POST'])
def monthly_reports(request, building):
    try:
        building = Building.objects.get(code=building)
        if request.method == 'POST':
            month = request.data.get('month', None)
            year = request.data.get('year', None)
            if month and year:
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s_%s.xlsx' % (
                    _('Monthly Report'), building, month, year)
                xlsx_data = building.get_report(month, year)
                response.write(xlsx_data)
                return response
            else:
                return JsonResponse({'message': messages.MESSAGES.MONTH_YEAR_ERROR}, status=400)
        else:
            context = {'building': building,
                       'title': _('Monthly Reports'), 'opts': Building._meta,
                       'change': True, 'is_popup': False, 'save_as': False,
                       'has_delete_permission': False, 'has_add_permission': False, 'has_change_permission': False,
                       'year_range': range(constants.START_YEAR, timezone.now().year + 1)}
            return render(request, 'admin/building_reports.html', context)
    except Building.DoesNotExist:
        return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)


def daily_report_download(request, building, date):
    try:
        workday = Workday.objects.get(building=building, date=date)
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('Daily_Report'), building, date)
        xlsx_data = workday.get_report()
        response.write(xlsx_data)
        return response
    except Workday.DoesNotExist:
        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
