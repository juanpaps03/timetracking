from django.contrib import messages as django_messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from rest_framework.views import APIView

from tracker.models import Building, Workday, Task
from config import messages

import datetime
import convertapi

convertapi.api_secret = 'OeuVcz0cyMNL9tTh'


class CreateLogHours(APIView):
    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        task_id = request.data.get('task', None)
        hours_per_user = request.data.get('hours_list', [])
        comment = request.data.get('comment', None)
        if comment == '':
            comment = None

        try:
            workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
            if workday.assign_logs(task_id, hours_per_user, comment):
                django_messages.success(request, messages.LOGS_UPDATED)
                return JsonResponse({'message': messages.LOGS_UPDATED}, status=200)
            else:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
                # actually it's comment empty error, but is caught in frontend so this should never happen.
        except IndexError:
            return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        except Task.DoesNotExist:
            return JsonResponse({'message': messages.TASK_NOT_FOUND}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)


class CreateLogHoursPastDay(APIView):
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
            return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        except Task.DoesNotExist:
            return JsonResponse({'message': messages.TASK_NOT_FOUND}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)

        return JsonResponse({'message': messages.LOGS_UPDATED}, status=200)


class StartDay(APIView):
    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        Workday.start(building)
        return redirect('tracker:dashboard', username=username)


class EndDay(APIView):
    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        comment = request.data.get('comment', None)
        if comment == '':
            comment = None
        # comment is empty unless the day end needs to bypass controls.
        try:
            workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
            if workday.end(comment):
                django_messages.success(request, messages.DAY_ENDED)
                return redirect('tracker:dashboard', username=username)
            else:
                django_messages.warning(request, messages.HOURS_MISSING)
                return redirect('tracker:log_hours', username=username)
        except IndexError:
            return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)


class DailyReport(APIView):
    def post(self, request, username):
        user = request.user
        building = Building.objects.get_by_overseer(user)
        date_str = request.data.get('date', None)
        if date_str:
            date = datetime.datetime.strptime(date_str, "%Y-%m-%d").date()
            try:
                workday = Workday.objects.get(building=building, date=date)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (
                _('Daily_Report'), building, date)
                xlsx_data = workday.get_report()
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
