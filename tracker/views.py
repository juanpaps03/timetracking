from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.contrib import messages as django_messages


from config import constants, messages
from tracker.models import Building, Workday, LogHour, Task
from itertools import groupby
from operator import itemgetter
from tracker.serializers import *

from constance import config
import datetime

class Dashboard(View):
    def get(self, request, username):
        # <view logic>
        workers = []
        workers_missing_logs = []
        user = request.user
        building = Building.objects.get_by_overseer(user)
        workday = None
        is_old_workday = False
        workers_with_logs = 0
        if building:
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workdays = Workday.objects.filter(building=building, finished=False).order_by('-date')
                workday = workdays[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker_logs = list(logs.filter(worker=worker))
                    # if worker_logs:
                    #     workers_with_logs += 1
                    if not LogHour.worker_passes_controls(workday, worker_logs):
                        workers_missing_logs.append(worker)
                    else:
                        workers_with_logs += 1
                if workers:
                    workers_ratio = round(100 * workers_with_logs / len(workers))
                else:
                    workers_ratio = 100

                context = {
                    'workers_missing_logs': workers_missing_logs,
                    'workday': workday,
                    'workers_ratio': workers_ratio,
                    'building': building,
                    'is_old_workday': is_old_workday
                }
                return render(request, 'tracker/dashboard.html', context)
            except IndexError:
                workdays = Workday.objects.filter(building=building, finished=True).order_by('-date')
                able_to_start = not workdays or workdays[0].date != date
                context = {'building': building, 'able_to_start': able_to_start}
                return render(request, 'tracker/start_day.html', context)
        else:
            context = {'building': None, 'able_to_start': False}

            if user.is_superuser or user.is_staff:
                return render(request, 'tracker/start_day.html', context)
            else:
                django_messages.warning(request, messages.NO_BUILDING)
                return render(request, 'tracker/start_day.html', context)


class LogHours(View):
    def get(self, request, username):
        tasks = []
        workers = []
        user = request.user
        is_old_workday = False

        # Select the building related to the overseer then obtain its tasks and workers
        building = Building.objects.get_by_overseer(user)
        if building:
            tasks = building.tasks.all()
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                expected = workday.expected_hours()
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker.logs = list(logs.filter(worker=worker))
                    worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                    worker.passes_controls_string = LogHour.worker_passes_controls_string(workday, worker.logs)
                    # expected = 0
                    # if expected > 0:
                    #     percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                    #     if (percent >= 100):
                    #         worker.hours_percent = 100
                    #     else:
                    #         worker.hours_percent = percent
                    # else:
                    #     worker.hours_percent = 100

                    print("******************************************")
                    print(workday.date.day)

                    day = str(workday.date.day)
                    if day.__len__() == 1:
                        day = "0" + day
                    month = str(workday.date.month)
                    if month.__len__() == 1:
                        month = "0" + month
                    year = str(workday.date.year)
                    dia = day + "/" + month + "/" + year

                    print("dia es: " + dia)

                    if ((dia in constants.DIAS_DE_HORAS_EXTRA) or (workday.date.weekday() == 5 or workday.date.weekday() == 6)):
                        worker.passes_controls_string = "mayor"
                        expected = 9
                        percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                        if (percent >= 100):
                            worker.hours_percent = 100
                        else:
                            worker.hours_percent = percent
                        print("entro al if de horas extra y modifica expected")

                    else:
                        if expected > 0:
                            percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                            if (percent >= 100):
                                worker.hours_percent = 100
                            else:
                                worker.hours_percent = percent
                        else:
                            #Si entra en el else es porque hubo un error, hay que imprimir el error
                            worker.hours_percent = 100

                for task in tasks:
                    task.logs = list(logs.filter(task=task))
            except IndexError:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        # filter out useless data
        tasks = serialize_tasks_with_logs(tasks)
        keyfunc = itemgetter("category")
        grouped_tasks = [{'name': key, 'tasks': list(grp)} for key, grp in groupby(sorted(tasks, key=keyfunc), key=keyfunc)]

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers),
            'expected': expected,
            'workday': workday,
            'is_old_workday': is_old_workday
        }

        return render(request, 'tracker/log_hours.html', context)


class DayReview(View):
    def get(self, request, username):
        overseer = request.user
        building = Building.objects.get_by_overseer(overseer)
        workers_missing_logs = []
        workday = None
        logs = None
        is_old_workday = False
        if building:
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                logs = LogHour.objects.all().filter(workday=workday)
                for worker in workers:
                    worker.logs = list(logs.filter(worker=worker))
                    if not LogHour.worker_passes_controls(workday, worker.logs):
                        workers_missing_logs.append(worker)
            except IndexError:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)

        context = {
            'logs': serialize_logs(logs, with_workers=True, with_tasks=True),
            'workers_missing_logs': workers_missing_logs,
            'workday': workday,
            'is_old_workday': is_old_workday
        }

        return render(request, 'tracker/day_review.html', context)


class PastDays(View):
    def get(self, request, username):
        user = request.user
        view_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_VIEW)
        edit_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_EDIT)
        workdays = Workday.objects.filter(overseer=user, date__lte=timezone.localdate(timezone.now()), date__gte=view_threshold)
        editable_workdays = workdays.filter(date__gte=edit_threshold).order_by('-date')
        workdays = workdays.difference(editable_workdays).order_by('-date')
        buildings = Building.objects.all()

        context = {'editable_workdays': editable_workdays, 'non_editable_workdays': workdays, 'days': config.DAYS_ABLE_TO_EDIT, 'obras': buildings, 'error': ''}

        return render(request, 'tracker/past_days.html', context)


class PastDaysEdit(View):
    def get(self, request, username):
        user = request.user


        print("Entra en PastDaysEdit!!!")
        print(user)
        print(request)

        dia = request.GET['wkday']
        print("diaaaa")
        print(dia)
        partes1 = dia.split("/")
        dia1 = partes1[0]
        mes1 = partes1[1]
        anio1 = partes1[2]

        start_date = datetime.date(int(anio1), int(mes1), int(dia1))

        date = start_date

        hayError = False
        workers = []
        tasks = []
        workday = None
        try:
            print('entra al try')

            workday = Workday.objects.filter(overseer=user, date=date).first()

            if workday:
                expected = workday.expected_hours()
                building = workday.building
                workers = building.workers.all()
                logs = LogHour.objects.all().filter(workday=workday)
                tasks = Task.objects.get_by_building(building)
                for worker in workers:
                    worker.logs = list(logs.filter(worker=worker))
                    worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                    worker.passes_controls_string = LogHour.worker_passes_controls_string(workday, worker.logs)

                    day = str(workday.date.day)
                    if day.__len__() == 1:
                        day = "0" + day
                    month = str(workday.date.month)
                    if month.__len__() == 1:
                        month = "0" + month
                    year = str(workday.date.year)
                    dia = day + "/" + month + "/" + year

                    if ((dia in constants.DIAS_DE_HORAS_EXTRA) or (
                        workday.date.weekday() == 5 or workday.date.weekday() == 6)):
                        worker.passes_controls_string = "mayor"
                        expected = 9
                        percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                        if (percent >= 100):
                            worker.hours_percent = 100
                        else:
                            worker.hours_percent = percent
                        print("entro al if de horas extra y modifica expected")

                    else:
                        if expected > 0:
                            percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                            if (percent >= 100):
                                worker.hours_percent = 100
                            else:
                                worker.hours_percent = percent
                        else:
                            # Si entra en el else es porque hubo un error, hay que imprimir el error
                            worker.hours_percent = 100
                    # if expected > 0:
                    #     worker.hours_percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                    # else:
                    #     worker.hours_percent = 100
                for task in tasks:
                    task.logs = list(logs.filter(task=task))
            else:
                print('Error al obtener el workday')
                mensaje_error = messages.WORKDAY_NOT_FOUND
                hayError = True
                context = {'error': mensaje_error, 'hayError': hayError}
                return render(request, 'tracker/past_days_edit.html', context)

        except Workday.DoesNotExist:
            print('se captura la excepcion Workday.DoesNotExist')
            mensaje_error = messages.WORKDAY_NOT_FOUND
            hayError = True
            context = {'error': mensaje_error, 'hayError': hayError}
            return render(request, 'tracker/past_days_edit.html', context)

        except Exception:
            print('se captura la excepcion generica')
            view_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_VIEW)
            edit_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_EDIT)
            workdays = Workday.objects.filter(overseer=user, date__lte=timezone.localdate(timezone.now()),
                                              date__gte=view_threshold)
            editable_workdays = workdays.filter(date__gte=edit_threshold).order_by('-date')
            workdays = workdays.difference(editable_workdays).order_by('-date')
            buildings = Building.objects.all()
            mensaje_error = messages.GENERIC_ERROR
            hayError = True
            context = {'error': mensaje_error, 'hayError': hayError}

            return render(request, 'tracker/past_days_edit.html', context)

        # filter out useless data
        tasks = serialize_tasks_with_logs(tasks)
        keyfunc = itemgetter("category")
        grouped_tasks = [{'name': key, 'tasks': list(grp)} for key, grp in groupby(sorted(tasks, key=keyfunc), key=keyfunc)]

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers),
            'expected': expected,
            'workday': workday,
            'hayError': hayError
        }

        return render(request, 'tracker/past_days_edit.html', context)



class DhtReport(View):
    def get(self, request, username):
        user = request.user
        view_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_VIEW)
        workdays = Workday.objects.filter(overseer=user, date__lte=timezone.localdate(timezone.now()), date__gte=view_threshold)
        buildings = Building.objects.all()
        context = {'workdays': workdays, 'obras': buildings}
        return render(request, 'tracker/dht_report.html', context)



class DhtTasksReport(View):
    def get(self, request, username):
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/dht_tasks_report.html', context)


class DhtTasksReportResumen(View):
    def get(self, request, username):
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/dht_tasks_report_resumen.html', context)
