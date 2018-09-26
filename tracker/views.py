from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View

from config import constants, messages
from sabyltimetracker.users.models import User
from sabyltimetracker.users.users_permissions_decorator import user_permissions
from tracker.models import Building, Workday, LogHour, Task


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
class Dashboard(View):
    def get(self, request, username):
        # <view logic>
        workers = []
        expected_hours = Workday.expected_hours()
        workers_missing_hours = []
        user = request.user
        building = Building.objects.get_by_overseer(user)
        workday = None
        workers_with_logs = 0
        if building:
            workers = building.workers.all()
            date = timezone.now().date()
            try:
                print(date)
                workday = Workday.objects.get(building=building, date=date, finished=False)
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker_logs = list(logs.filter(worker=worker))
                    if worker_logs:
                        workers_with_logs += 1
                    if not LogHour.worker_passes_controls(workday, worker_logs):
                        workers_missing_hours.append(worker)
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_FINISHED}, status=400)
        if workers:
            workers_ratio = round(100 * workers_with_logs / len(workers))
        else:
            workers_ratio = 100

        context = {
            'workers_missing_hours': workers_missing_hours,
            'workday': workday,
            'workers_ratio': workers_ratio,
            'building': building
        }
        return render(request, 'tracker/dashboard.html', context)


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
class LogHours(View):
    def get(self, request, username):
        tasks = []
        workers = []
        user = request.user

        # Select the building related to the overseer then obtain its tasks and workers
        building = Building.objects.get_by_overseer(user)
        if building:
            tasks = building.tasks.all()
            workers = building.workers.all()
            date = timezone.now().date()
            try:
                workday = Workday.objects.get(building=building, date=date, finished=False)
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
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_FINISHED}, status=400)
        # filter out useless data
        tasks = [
            {
                'id': task.id,
                'name': task.name,
                'code': task.code,
                'logs': [{'worker': {'code': log.worker.code}, 'amount': log.amount} for log in task.logs]
            }
            for task in tasks
        ]
        workers = [
            {
                'code': worker.code,
                'first_name': worker.first_name,
                'last_name': worker.last_name,
                'logs': [{'task': {'id': log.task.id, 'name': log.task.name, 'code': log.task.code}, 'amount': log.amount} for log in worker.logs],
                'passes_controls': worker.passes_controls,
                'hours_percent': worker.hours_percent
            }
            for worker in workers
        ]

        context = {'tasks': tasks, 'workers': workers, 'expected': expected, 'workday': workday, 'absence_code': constants.ABSENCE_CODE}

        return render(request, 'tracker/log_hours.html', context)


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
class DayReview(View):
    def get(self, request, username):
        overseer = request.user
        building = Building.objects.get_by_overseer(overseer)
        expected = Workday.expected_hours()
        workers_missing_hours = []
        workday = None
        logs = None
        if building:
            workers = building.workers.all()
            date = timezone.now().date()
            try:
                workday = Workday.objects.get(building=building, date=date, finished=False)
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker.logs = list(logs.filter(worker=worker))
                    if not LogHour.worker_passes_controls(workday, worker.logs):
                        workers_missing_hours.append(worker)
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_FINISHED}, status=400)

        context = {'logs': logs, 'workers_missing_hours': workers_missing_hours,
                   'workday': workday, 'absence_code': constants.ABSENCE_CODE}

        return render(request, 'tracker/day_review.html', context)


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
class PastDays(View):
    def get(self, request, username):
        user = request.user
        threshold = timezone.now() - timezone.timedelta(days=constants.DAYS_ABLE_TO_EDIT)
        workdays = Workday.objects.filter(overseer=user, date__gte=threshold, date__lt=timezone.now()).order_by('-date')

        context = {'workdays': workdays, 'days': constants.DAYS_ABLE_TO_EDIT}

        return render(request, 'tracker/past_days.html', context)


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
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
        tasks = [
            {
                'id': task.id,
                'name': task.name,
                'code': task.code,
                'logs': [{'worker': {'code': log.worker.code}, 'amount': log.amount} for log in task.logs]
            }
            for task in tasks
        ]
        workers = [
            {
                'code': worker.code,
                'first_name': worker.first_name,
                'last_name': worker.last_name,
                'logs': [{'task': {'id': log.task.id, 'name': log.task.name, 'code': log.task.code},
                          'amount': log.amount} for log in worker.logs],
                'passes_controls': worker.passes_controls,
                'hours_percent': worker.hours_percent
            }
            for worker in workers
        ]

        context = {'tasks': tasks, 'workers': workers, 'expected': expected, 'workday': workday,
                   'absence_code': constants.ABSENCE_CODE}

        return render(request, 'tracker/past_days_edit.html', context)
