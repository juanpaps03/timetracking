from django.contrib import messages as django_messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.defaultfilters import wordcount
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
from pip._internal.locations import write_delete_marker_file
from pip._vendor.pyparsing import unicode_set
from rest_framework.views import APIView

from tracker.models import Building, Workday, Task
from config import messages

import datetime
import convertapi

convertapi.api_secret = 'OeuVcz0cyMNL9tTh'


class CreateLogHours(APIView):
    def post(self, request, username):

        user = request.user
        print("request.user: " + request.user.full_name())
        building = Building.objects.get_by_overseer(user)
        print(f'building: {building.code}')
        task_id = request.data.get('task', None)
        print(f'tarea: {task_id}')
        hours_per_user = request.data.get('hours_list', [])

        for x in hours_per_user:
            print(float(x['amount']))

        # comment = request.data.get('comment', None)
        # if comment == '':
        #     comment = None

        try:
            workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
            if workday.assign_logs(task_id, hours_per_user):
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
        if Workday.start(building):
            return redirect('tracker:dashboard', username=username)
        else:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)


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
        print("entro en DailyReport!!!!!!!!")
        workdayDate = request.data.get('workdaydate')
        print(workdayDate)
        x = workdayDate.split(" - ")
        wkday = x[0]
        user = request.user
        building = Building.objects.get_by_overseer(user)
        if wkday:
            date = datetime.datetime.strptime(wkday, "%Y-%m-%d").date()
            try:
                workday = Workday.objects.get(building=building, date=date)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('Daily_Report'), building, date)
                xlsx_data = workday.get_report()
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)



class DhtReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtReportApi!!!!!!!!")
        initialDay = request.data.get('initialDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishDay)

        user = request.user
        building = Building.objects.get_by_overseer(user)

        if initialDay and finishDay:
            # dateInitial = datetime.datetime.strptime(initialDay, "%Y-%m-%d").date()
            # dateFinish = datetime.datetime.strptime(finishDay, "%Y-%m-%d").date()

            partes1 = initialDay.split("-")
            anio1 = partes1[0]
            mes1 = partes1[1]
            dia1 = partes1[2]

            partes2 = finishDay.split("-")
            anio2 = partes2[0]
            mes2 = partes2[1]
            dia2 = partes2[2]


            # start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            # end_date = datetime.date(int(anio2), int(mes2), int(dia2))


            # workdays = Workday.objects.filter(overseer=user, date__range=(start_date, end_date))
            # print("Primer for:")
            # for wd in workdays:
            #     print(wd.date)


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinal = dia2 + "_" + mes2 + "_" + anio2
            rango = fechaInicial + "_a_" + fechaFinal

            try:
                # workday = Workday.objects.get(building=building, date=dateInitial)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_General'), building, rango)
                xlsx_data = building.get_dht_report(fechaInicial, fechaFinal)
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
