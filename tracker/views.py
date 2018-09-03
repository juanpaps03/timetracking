from django.utils import timezone

from django.utils.decorators import method_decorator

from django.shortcuts import render

from django.http import HttpResponse, JsonResponse
from django.views import View

from sabyltimetracker.users.models import User
from tracker.models import Building, Task, Workday, LogHour
from sabyltimetracker.users.users_permissions_decorator import user_permissions


@method_decorator([user_permissions([User.OVERSEER])], name='dispatch')
class Dashboard(View):
    def get(self, request, username):
        # <view logic>
        return render(request, 'tracker/dashboard.html')


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
                print(logs)
                if logs:
                    for worker in workers:
                        worker_logs = list(logs.filter(user=worker))
                        worker.logs = worker_logs
            except Workday.DoesNotExist:
                return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'},
                                    status=400)

        context = {'tasks': tasks, 'workers': workers}

        return render(request, 'tracker/log_hours.html', context)
