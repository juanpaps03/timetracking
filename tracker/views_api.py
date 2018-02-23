from django.utils import timezone

from rest_framework.views import APIView
from rest_framework import generics
from rest_framework.parsers import JSONParser

from django.http import JsonResponse

from tracker.models import Building, Workday, Task


class LogsHoursCrate(APIView):

    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        date = timezone.now().date()
        task_id = request.data.get('task', None)
        hours_per_user = request.data.get('hours_list', [])

        try:
            work_day = Workday.objects.get(building=building, date=date, finished=False)
            work_day.assign_logs(task_id, hours_per_user)
        except Workday.DoesNotExist:
            return JsonResponse({'error': 'There was a problem obtaining work day. Maybe it was finished.'}, status=404)
        except Task.DoesNotExist:
            return JsonResponse({'error': 'There was a problem obtaining task.'}, status=404)


        error = []
        info = []

        return JsonResponse({'error': error, 'info': info}, status=200)


