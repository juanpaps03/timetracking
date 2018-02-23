import datetime

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.parsers import JSONParser

from django.http import JsonResponse

from tracker.models import Building, Workday


class LogsHoursCrate(APIView):

    def post(self, request, username):
        user = request.user
        building = Building.objects.filter(overseer=user).last()
        date = datetime.date.today()
        try:
            work_day = Workday.objects.get(building=building, date=date, finished=False)
        except Workday.DoesNotExist:
            return JsonResponse({'error': 'There was a problem obtaining work day. Maybe it was finished.'})

        return JsonResponse({'test': 'test'})


