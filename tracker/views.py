from django.utils import timezone
from django.contrib import messages

from django.utils.decorators import method_decorator

from django.shortcuts import render

from django.http import HttpResponse, JsonResponse
from django.views import View

from sabyltimetracker.users.models import User
from tracker.models import Building, Workday, LogHour
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
        if building:
            workers = building.workers.all()
            date = timezone.now().date()
            try:
                workday = Workday.objects.get(building=building, date=date, finished=False)
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker_logs = list(logs.filter(user=worker))
                    hours = LogHour.sum_hours(worker_logs)
                    if hours < expected_hours:
                        workers_missing_hours.append(worker)
            except Workday.DoesNotExist:
                return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'},
                                    status=400)

        context = {'workers_missing_hours': workers_missing_hours}

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
                if logs:
                    for worker in workers:
                        worker.logs = list(logs.filter(user=worker))
            except Workday.DoesNotExist:
                return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'},
                                    status=400)
        context = {'tasks': tasks, 'workers': workers}

        return render(request, 'tracker/log_hours.html', context)
