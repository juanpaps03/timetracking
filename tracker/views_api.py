from django.contrib import messages as django_messages
from django.http import JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.views import APIView

from tracker.models import Building, Workday, Task
from config import messages


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
            return JsonResponse({'message': messages.WORKDAY_FINISHED}, status=400)
        except Task.DoesNotExist:
            return JsonResponse({'message': messages.TASK_NOT_FOUND}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)

        django_messages.success(request, 'Hours added correctly.')
        return JsonResponse({'message': messages.LOGS_UPDATED}, status=200)


class EndDay(APIView):
    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        date = timezone.now().date()

        try:
            workday = Workday.objects.get(building=building, date=date, finished=False)
            if workday.end():
                django_messages.success(request, messages.DAY_ENDED)
                return redirect('tracker:dashboard', username=username)
            else:
                django_messages.warning(request, messages.HOURS_MISSING)
                return redirect('tracker:log_hours', username=username)
        except Workday.DoesNotExist:
            return JsonResponse({'message': messages.WORKDAY_FINISHED}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)


class LogsHoursCratePastDay(APIView):
    def post(self, request, date, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        task_id = request.data.get('task', None)
        hours_per_user = request.data.get('hours_list', [])
        try:
            work_day = Workday.objects.get(building=building, date=date)
            if work_day.is_editable_by_overseer():
                work_day.assign_logs(task_id, hours_per_user)
            else:
                return JsonResponse({'message': messages.WORKDAY_FORBIDDEN}, status=403)
        except Workday.DoesNotExist:
            return JsonResponse({'message': messages.WORKDAY_FINISHED}, status=400)
        except Task.DoesNotExist:
            return JsonResponse({'message': messages.TASK_NOT_FOUND}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)

        return JsonResponse({'message': messages.LOGS_UPDATED}, status=200)
