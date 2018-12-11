from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.contrib import messages as django_messages


from config import constants, messages
from tracker.models import Building, Workday, LogHour, Task
from itertools import groupby
from operator import itemgetter
from tracker.serializers import *

from constance import config


class Dashboard(View):
    def get(self, request, username):
        # <view logic>
        workers = []
        workers_missing_logs = []
        user = request.user
        building = Building.objects.get_by_overseer(user)
        workday = None
        is_old_workday = False
        workers_with_logs = 0
        if building:
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workdays = Workday.objects.filter(building=building, finished=False).order_by('-date')
                workday = workdays[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker_logs = list(logs.filter(worker=worker))
                    if worker_logs:
                        workers_with_logs += 1
                    if not LogHour.worker_passes_controls(workday, worker_logs):
                        workers_missing_logs.append(worker)
                if workers:
                    workers_ratio = round(100 * workers_with_logs / len(workers))
                else:
                    workers_ratio = 100

                context = {
                    'workers_missing_logs': workers_missing_logs,
                    'workday': workday,
                    'workers_ratio': workers_ratio,
                    'building': building,
                    'is_old_workday': is_old_workday
                }
                return render(request, 'tracker/dashboard.html', context)
            except IndexError:
                workdays = Workday.objects.filter(building=building, finished=True).order_by('-date')
                able_to_start = not workdays or workdays[0].date != date
                context = {'building': building, 'able_to_start': able_to_start}
                return render(request, 'tracker/start_day.html', context)
        else:
            context = {'building': None, 'able_to_start': False}
            django_messages.warning(request, messages.NO_BUILDING)
            return render(request, 'tracker/start_day.html', context)


class LogHours(View):
    def get(self, request, username):
        tasks = []
        workers = []
        user = request.user
        is_old_workday = False

        # Select the building related to the overseer then obtain its tasks and workers
        building = Building.objects.get_by_overseer(user)
        if building:
            tasks = building.tasks.all()
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                expected = workday.expected_hours()
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker.logs = list(logs.filter(worker=worker))
                    worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                    if expected > 0:
                        worker.hours_percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                    else:
                        worker.hours_percent = 100
                for task in tasks:
                    task.logs = list(logs.filter(task=task))
            except IndexError:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        # filter out useless data
        tasks = serialize_tasks_with_logs(tasks)
        keyfunc = itemgetter("category")
        grouped_tasks = [{'name': key, 'tasks': list(grp)} for key, grp in groupby(sorted(tasks, key=keyfunc), key=keyfunc)]

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers),
            'expected': expected,
            'workday': workday,
            'is_old_workday': is_old_workday
        }

        return render(request, 'tracker/log_hours.html', context)


class DayReview(View):
    def get(self, request, username):
        overseer = request.user
        building = Building.objects.get_by_overseer(overseer)
        workers_missing_logs = []
        workday = None
        logs = None
        is_old_workday = False
        if building:
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker.logs = list(logs.filter(worker=worker))
                    if not LogHour.worker_passes_controls(workday, worker.logs):
                        workers_missing_logs.append(worker)
            except IndexError:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)

        context = {
            'logs': serialize_logs(logs, with_workers=True, with_tasks=True),
            'workers_missing_logs': workers_missing_logs,
            'workday': workday,
            'is_old_workday': is_old_workday
        }

        return render(request, 'tracker/day_review.html', context)


class PastDays(View):
    def get(self, request, username):
        user = request.user
        view_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_VIEW)
        edit_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_EDIT)
        workdays = Workday.objects.filter(overseer=user, date__lt=timezone.localdate(timezone.now()), date__gte=view_threshold)
        editable_workdays = workdays.filter(date__gte=edit_threshold).order_by('-date')
        workdays = workdays.difference(editable_workdays).order_by('-date')

        context = {'editable_workdays': editable_workdays, 'non_editable_workdays': workdays, 'days': config.DAYS_ABLE_TO_EDIT}

        return render(request, 'tracker/past_days.html', context)


class PastDaysEdit(View):
    def get(self, request, date, username):
        user = request.user
        date = date
        workers = []
        tasks = []
        workday = None
        try:
            workday = Workday.objects.filter(overseer=user, date=date).first()
            expected = workday.expected_hours()
            building = workday.building
            workers = building.workers.all()
            logs = LogHour.objects.all().filter(workday=workday)
            tasks = Task.objects.get_by_building(building)
            for worker in workers:
                worker.logs = list(logs.filter(worker=worker))
                worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                if expected > 0:
                    worker.hours_percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                else:
                    worker.hours_percent = 100
            for task in tasks:
                task.logs = list(logs.filter(task=task))
        except Workday.DoesNotExist:
            return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)

        # filter out useless data
        tasks = serialize_tasks_with_logs(tasks)
        keyfunc = itemgetter("category")
        grouped_tasks = [{'name': key, 'tasks': list(grp)} for key, grp in groupby(sorted(tasks, key=keyfunc), key=keyfunc)]

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers),
            'expected': expected,
            'workday': workday
        }

        return render(request, 'tracker/past_days_edit.html', context)
