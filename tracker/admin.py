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
from tracker.models import Building, Workday, LogHour, Task, TaskCategory, Worker, WorkerCategory
from .models import User
from django.db import IntegrityError

# Admin Site Config
admin.sites.AdminSite.site_header = _('Sabyl TimeTracker')
admin.sites.AdminSite.site_title = _('Sabyl TimeTracker')
admin.sites.AdminSite.index_title = _('Home')


admin.site.register(LogHour)
admin.site.register(Task)
admin.site.register(TaskCategory)
admin.site.register(WorkerCategory)
admin.site.register(Worker)


@admin.register(Building)
class BuildingAdmin(admin.ModelAdmin):
    list_display = ('code', 'address', 'report_buttons')

    def report_buttons(self, obj):
        return format_html('<a class="button" target="_blank" href="{}">{}</a>',
                           reverse('admin:building_reports', kwargs={'building': obj.code}),
                           _('Make Reports')
                           )
    report_buttons.short_description = _('Monthly Reports')

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
    report_buttons.short_description = _('Daily Reports')

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


def create_manager_group():
    # Creating manager group and permissions
    try:
        manager_group, created = Group.objects.get_or_create(name=_('Manager'))

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

        content_type = ContentType.objects.get_for_model(TaskCategory)
        permissions = Permission.objects.filter(content_type=content_type)
        for p in permissions:
            manager_group.permissions.add(p)

        content_type = ContentType.objects.get_for_model(WorkerCategory)
        permissions = Permission.objects.filter(content_type=content_type)
        for p in permissions:
            manager_group.permissions.add(p)

        content_type = ContentType.objects.get_for_model(Worker)
        permissions = Permission.objects.filter(content_type=content_type)
        for p in permissions:
            manager_group.permissions.add(p)

        content_type = ContentType.objects.get_for_model(User)
        permissions = Permission.objects.filter(content_type=content_type)
        for p in permissions:
            if p.codename != "delete_user":
                manager_group.permissions.add(p)

        manager_group.save()
    except:
        pass


def create_default_tasks():
    # 'General' task creation for each non-special category
    standard_categories = TaskCategory.objects.exclude(name=constants.SPECIAL_CATEGORY_NAME)
    for category in standard_categories:
        code = '%s-%s' % (category.name, constants.GENERAL_CODE_SUFFIX)
        name = _('%s/General') % category.name
        description = _('General task for the %s category') % category.name
        try:
            task, created = Task.objects.get_or_create(code=code,
                                                       name=name,
                                                       description=description,
                                                       category=category,
                                                       requires_comment=True)
            task.buildings = Building.objects.all()
            task.save()
        except IntegrityError:
            pass
    # special category creation.
    try:
        special_category, created = TaskCategory.objects.get_or_create(name=constants.SPECIAL_CATEGORY_NAME)
        special_category.save()
    except:
        return # If we can't create the special_category, we can't create any special task

    try:
        # union assembly task creation.
        union_assembly_task, created = Task.objects.get_or_create(code=constants.UNION_ASSEMBLY_CODE,
                                                             name=_('Union Assembly'),
                                                             description=_(
                                                             'Auto-generated task that designates a worker in an union assembly.'),
                                                             category=special_category,
                                                             in_monthly_report=False)
        union_assembly_task.buildings = Building.objects.all()
        union_assembly_task.save()
    except IntegrityError:
        pass

    try:
        # blood donation task creation.
        blood_donation_task, created = Task.objects.get_or_create(code=constants.BLOOD_DONATION_CODE,
                                                             name=_('Blood Donation'),
                                                             description=_(
                                                             'Auto-generated task that designates a worker on leave for blood donation.'),
                                                             category=special_category,
                                                             is_boolean=True,
                                                             whole_day=True,
                                                             in_monthly_report=False)
        blood_donation_task.buildings = Building.objects.all()
        blood_donation_task.save()
    except IntegrityError:
        pass

    try:
        # sick task creation.
        sick_task, created = Task.objects.get_or_create(code=constants.SICK_CODE,
                                                        name=_('Sick'),
                                                        description=_('Auto-generated task that designates a sick worker.'),
                                                        category=special_category,
                                                        is_boolean=True,
                                                        in_monthly_report=False)
        sick_task.buildings = Building.objects.all()
        sick_task.save()
    except IntegrityError:
        pass

    try:
        # absence task creation.
        absence_task, created = Task.objects.get_or_create(code=constants.ABSENCE_CODE,
                                                           name=_('Absence'),
                                                           description=_('Auto-generated task that designates worker absence for a day.'),
                                                           category=special_category,
                                                           is_boolean=True,
                                                           whole_day=True,
                                                           in_monthly_report=False)
        absence_task.buildings = Building.objects.all()
        absence_task.save()
    except IntegrityError:
        pass

    try:
        # notified absence task creation.
        notified_absence_task, created = Task.objects.get_or_create(code=constants.NOTICED_ABSENCE_CODE,
                                                           name=_('Notified Absence'),
                                                           description=_('Auto-generated task that designates worker absence for a day, with previous notice.'),
                                                           category=special_category,
                                                           is_boolean=True,
                                                           whole_day=True)
        notified_absence_task.buildings = Building.objects.all()
        notified_absence_task.save()
    except IntegrityError:
        pass

    try:
        # bereavement leave task creation.
        bereavement_task, created = Task.objects.get_or_create(code=constants.BEREAVEMENT_LEAVE_CODE,
                                                               name=_('Bereavement Leave'),
                                                               description=_('Auto-generated task that designates a worker on bereavement leave.'),
                                                               category=special_category,
                                                               is_boolean=True,
                                                               whole_day=True,
                                                               in_monthly_report=False)
        bereavement_task.buildings = Building.objects.all()
        bereavement_task.save()
    except IntegrityError:
        pass

    try:
        # study leave task creation.
        study_task, created = Task.objects.get_or_create(code=constants.STUDY_LEAVE_CODE,
                                                         name=_('Study Leave'),
                                                         description=_('Auto-generated task that designates a worker on study leave.'),
                                                         category=special_category,
                                                         is_boolean=True,
                                                         whole_day=True,
                                                         in_monthly_report=False)
        study_task.buildings = Building.objects.all()
        study_task.save()
    except IntegrityError:
        pass

    try:
        # disabled child leave task creation.
        disabled_child_leave_task, created = Task.objects.get_or_create(code=constants.DISABLED_CHILD_LEAVE_CODE,
                                                                  name=_('Disabled Child Leave'),
                                                                  description=_(
                                                                      'Auto-generated task that designates a worker on leave for having a disabled child.'),
                                                                  category=special_category,
                                                                  is_boolean=True,
                                                                  whole_day=True)
        disabled_child_leave_task.buildings = Building.objects.all()
        disabled_child_leave_task.save()
    except IntegrityError:
        pass

    try:
        # marriage leave task creation.
        marriage_leave_task, created = Task.objects.get_or_create(code=constants.MARRIAGE_LEAVE_CODE,
                                                                  name=_('Marriage Leave'),
                                                                  description=_(
                                                                      'Auto-generated task that designates a worker on marriage leave.'),
                                                                  category=special_category,
                                                                  is_boolean=True,
                                                                  whole_day=True,
                                                                  in_monthly_report=False)
        marriage_leave_task.buildings = Building.objects.all()
        marriage_leave_task.save()
    except IntegrityError:
        pass

    try:
        # paternity leave task creation.
        paternity_leave_task, created = Task.objects.get_or_create(code=constants.PATERNITY_LEAVE_CODE,
                                                                  name=_('Paternity Leave'),
                                                                  description=_(
                                                                      'Auto-generated task that designates a worker on paternity leave.'),
                                                                  category=special_category,
                                                                  is_boolean=True,
                                                                  whole_day=True,
                                                                  in_monthly_report=False)
        paternity_leave_task.buildings = Building.objects.all()
        paternity_leave_task.save()
    except IntegrityError:
        pass

    try:
        # union leave task creation.
        union_leave_task, created = Task.objects.get_or_create(code=constants.UNION_LEAVE_CODE,
                                                                  name=_('Union Leave'),
                                                                  description=_(
                                                                      'Auto-generated task that designates a worker on syndical leave.'),
                                                                  category=special_category)
        union_leave_task.buildings = Building.objects.all()
        union_leave_task.save()
    except IntegrityError:
        pass

    try:
        # strike task creation.
        strike_task, created = Task.objects.get_or_create(code=constants.STRIKE_CODE,
                                                          name=_('Strike'),
                                                          description=_('Auto-generated task that designates a worker on strike.'),
                                                          category=special_category,
                                                          in_monthly_report=False)
        strike_task.buildings = Building.objects.all()
        strike_task.save()
    except IntegrityError:
        pass

    try:
        # general strike task creation.
        general_strike_task, created = Task.objects.get_or_create(code=constants.GENERAL_STRIKE_CODE,
                                                          name=_('General strike'),
                                                          description=_(
                                                              'Auto-generated task that designates a worker on general strike.'),
                                                          category=special_category,
                                                          is_boolean=True,
                                                          whole_day=True,
                                                          in_monthly_report=False)
        general_strike_task.buildings = Building.objects.all()
        general_strike_task.save()
    except IntegrityError:
        pass

    try:
        # early leave task creation.
        early_leave_task, created = Task.objects.get_or_create(code=constants.EARLY_LEAVE_CODE,
                                                          name=_('Leaving Early'),
                                                          description=_(
                                                              'Auto-generated task that designates a worker that left early.'),
                                                          category=special_category,
                                                          is_boolean=True,
                                                          in_monthly_report=False)
        early_leave_task.buildings = Building.objects.all()
        early_leave_task.save()
    except IntegrityError:
        pass

    try:
        # FOCAP training task
        focap_task, created = Task.objects.get_or_create(code=constants.FOCAP_TRAINING_CODE,
                                                          name=_('FOCAP Training'),
                                                          description=_(
                                                              'Auto-generated task that designates a worker on FOCAP training.'),
                                                          category=special_category)
        focap_task.buildings = Building.objects.all()
        focap_task.save()
    except IntegrityError:
        pass

    try:
        # training task
        training_task, created = Task.objects.get_or_create(code=constants.TRAINING_CODE,
                                                          name=_('Training'),
                                                          description=_(
                                                              'Auto-generated task that designates a worker on training.'),
                                                          category=special_category)
        training_task.buildings = Building.objects.all()
        training_task.save()
    except IntegrityError:
        pass

    try:
        # antiquity leave task
        antiquity_task, created = Task.objects.get_or_create(code=constants.ANTIQUITY_LEAVE_CODE,
                                                          name=_('Antiquity leave'),
                                                          description=_(
                                                              'Auto-generated task that designates a worker on antiquity leave.'),
                                                          category=special_category,
                                                          is_boolean=True,
                                                          in_monthly_report=False)
        antiquity_task.buildings = Building.objects.all()
        antiquity_task.save()
    except IntegrityError:
        pass

    try:
        # suspended task creation.
        suspended_task, created = Task.objects.get_or_create(code=constants.SUSPENDED_CODE,
                                                             name=_('Suspended'),
                                                             description=_(
                                                             'Auto-generated task that designates a suspended worker.'),
                                                             category=special_category,
                                                             is_boolean=True,
                                                             in_monthly_report=False)
        suspended_task.buildings = Building.objects.all()
        suspended_task.save()
    except IntegrityError:
        pass

    try:
        # post_obra task creation.
        post_obra_task, created = Task.objects.get_or_create(code=constants.POST_OBRA_CODE,
                                                             name=_('Postobra'),
                                                             description=_(
                                                             'Auto-generated task that designates a worker on post-obra.'),
                                                             category=special_category,
                                                             in_monthly_report=False)
        post_obra_task.buildings = Building.objects.all()
        post_obra_task.save()
    except IntegrityError:
        pass


# custom views
@api_view(['GET', 'POST'])
def monthly_reports(request, building):
    try:
        building = Building.objects.get(code=building)
        if request.method == 'POST':
            month = int(request.data.get('month', None))
            year = int(request.data.get('year', None))
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
        workday = Workday.objects.get(date=date, building__code=building)
        response = HttpResponse(content_type='application/vnd.ms-excel')
        response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('Daily_Report'), building, date)
        xlsx_data = workday.get_report()
        response.write(xlsx_data)
        return response
    except Workday.DoesNotExist:
        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)


def create_defaults():
    create_manager_group()
    create_default_tasks()

