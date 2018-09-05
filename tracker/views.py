from django.utils import timezone
from django.contrib import messages

from django.utils.decorators import method_decorator

from django.shortcuts import render

from django.http import HttpResponse, JsonResponse
from django.views import View

from sabyltimetracker.users.models import User
from tracker.models import Building, Workday, LogHour, Task
from sabyltimetracker.users.users_permissions_decorator import user_permissions

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
                workday = Workday.objects.get(building=building, date=date, finished=False)
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker_logs = list(logs.filter(user=worker))
                    if worker_logs:
                        workers_with_logs += 1
                    hours = LogHour.sum_hours(worker_logs)
                    if hours < expected_hours:
                        workers_missing_hours.append(worker)
            except Workday.DoesNotExist:
                return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'},
                                    status=400)
        if workers:
            workers_ratio = round(workers_with_logs / len(workers))
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
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    if logs:
                        worker.logs = list(logs.filter(user=worker))
                    else:
                        worker.logs = []
                for task in tasks:
                    if logs:
                        task.logs = list(logs.filter(task=task))
                    else:
                        task.logs = []
            except Workday.DoesNotExist:
                return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'},
                                    status=400)

        # filter out useless data
        tasks = [
            {
                'id': task.id,
                'name': task.name,
                'code': task.code,
                'logs': [{'user': {'id': log.user.id}, 'amount': log.amount} for log in task.logs]
            }
            for task in tasks
        ]
        workers = [
            {
                'id': worker.id,
                'first_name': worker.first_name,
                'last_name': worker.last_name,
                'logs': [{'task': {'id': log.task.id}, 'amount': log.amount} for log in worker.logs]
            }
            for worker in workers
        ]

        context = {'tasks': tasks, 'workers': workers}

        return render(request, 'tracker/log_hours.html', context)


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
class DayReview(View):
    def get(self, request, username):
        # <view logic>
        workers = []
        expected_hours = Workday.expected_hours()
        workers_missing_hours = []
        user = request.user
        building = Building.objects.get_by_overseer(user)
        workday = None
        if building:
            workers = building.workers.all()
            date = timezone.now().date()
            try:
                workday = Workday.objects.get(building=building, date=date, finished=False)
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker.logs = list(logs.filter(user=worker))
                    if LogHour.sum_hours(worker.logs) < expected_hours:
                        workers_missing_hours.append(worker)
                tasks = Task.objects.get_by_building(building)
                for task in tasks:
                    task.logs = list(logs.filter(task=task))
            except Workday.DoesNotExist:
                return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'},
                                    status=400)

        context = {'workers': workers, 'tasks': tasks, 'workers_missing_hours': workers_missing_hours, 'workday': workday}

        return render(request, 'tracker/day_review.html', context)
