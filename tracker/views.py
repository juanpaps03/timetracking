from django.utils.decorators import method_decorator

from django.shortcuts import render

from django.http import HttpResponse
from django.views import View

from sabyltimetracker.users.models import User
from tracker.models import Task, Building
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

        # Select the last building related to the overseer then obtain its tasks and workers
        building = Building.objects.filter(overseer=user).last()
        if building:
            tasks = building.tasks.all()
            workers = building.workers.all()

        context = {'tasks': tasks, 'workers': workers}

        return render(request, 'tracker/log_hours.html', context)
