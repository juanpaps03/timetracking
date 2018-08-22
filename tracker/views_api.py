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
            return JsonResponse({'message': 'There was a problem obtaining work day. Maybe it was finished.'}, status=400)
        except Task.DoesNotExist:
            return JsonResponse({'message': 'There was a problem obtaining task.'}, status=400)
        except Exception:
            return JsonResponse({'message': 'Something went wrong.'}, status=400)

        return JsonResponse({'message': 'Hours added correctly.'}, status=200)


class StartWorkday(APIView):

    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        date = timezone.now().date()

        last_work_day = Workday.objects.filter(building=building, date='date__lt').latest('date')
        work_day, _ = Workday.objects.get_or_create(building=building, date=date, finished=False)

        return JsonResponse({'message': 'Hours added correctly.'}, status=200)
