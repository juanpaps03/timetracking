from django.utils.decorators import method_decorator

from django.shortcuts import render

from django.http import HttpResponse
from django.views import View

from sabyltimetracker.users.models import User
from sabyltimetracker.users.users_permissions_decorator import user_permissions


@method_decorator([user_permissions([User.OVERSEER, User.WORKER])], name='dispatch')
class MyView(View):
    def get(self, request):
        # <view logic>
        return HttpResponse('result')
