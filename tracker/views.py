from django.http import JsonResponse
from django.shortcuts import render
from django.utils import timezone
from django.utils.decorators import method_decorator
from django.utils.translation import ugettext_lazy as _
from django.views import View
from django.contrib import messages as django_messages


from config import constants, messages
from tracker.models import Building, Workday, LogHour, Task, Worker
from itertools import groupby
from operator import itemgetter, attrgetter
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
        # workers = []
        user = request.user
        is_old_workday = False

        # Select the building related to the overseer then obtain its tasks and workers
        building = Building.objects.get_by_overseer(user)
        if building:
            tasks = building.tasks.all()

            tasks = sorted(tasks, key=attrgetter('code'))

            workers = building.workers.all()
            workers_objetos = []
            for w1 in workers:
                print(w1)
                workers_objetos.append(w1)

            date = timezone.localdate(timezone.now())

            wda_entrada_activa = ""
            wda_entrada_reactiva = ""
            wda_salida_activa = ""
            wda_salida_reactiva = ""
            wda_ose_entrada = ""
            wda_ose_salida = ""
            try:
                try:
                    workdayAnterior = Workday.objects.filter(building=building, finished=True).order_by('-date')[0]

                    print('**wd anterior**')
                    print(workdayAnterior)
                    print('**fin wd anterior**')

                    wda_texto = workdayAnterior.comment
                    if wda_texto != None:
                        if "utefin" in wda_texto:
                            partes = wda_texto.split("utefin")
                            texto_ute = partes[0]

                            if "eact" in texto_ute:
                                partes_eact = texto_ute.split("eact")
                                wda_entrada_activa = partes_eact[1]

                            if "sact" in texto_ute:
                                partes_sact = texto_ute.split("sact")
                                wda_salida_activa = partes_sact[1]

                            if "ereact" in texto_ute:
                                partes_ereact = texto_ute.split("ereact")
                                wda_entrada_reactiva = partes_ereact[1]

                            if "sreact" in texto_ute:
                                partes_sreact = texto_ute.split("sreact")
                                wda_salida_reactiva = partes_sreact[1]

                            texto_restante = partes[1]
                            if "osesalfin" in texto_restante:
                                partes_ose = texto_restante.split("osesalfin")
                                texto_ose = partes_ose[0]
                                if "oseentfin" in texto_ose:
                                    partes_oseent = texto_ose.split("oseentfin")
                                    wda_ose_entrada = partes_oseent[0]
                                    wda_ose_salida = partes_oseent[1]

                        else:
                            if "osesalfin" in wda_texto:
                                partes_ose = wda_texto.split("osesalfin")
                                texto_ose = partes_ose[0]
                                if "oseentfin" in texto_ose:
                                    partes_oseent = texto_ose.split("oseentfin")
                                    wda_ose_entrada = partes_oseent[0]
                                    wda_ose_salida = partes_oseent[1]

                except IndexError:
                    print('LogHours() - No se encuentra workday anterior - Puede deberse a que la obra es nueva y aun no tiene ningun workday ingresado.')
            except IndexError:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)

            try:
                workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                expected = workday.expected_hours()

                logs = LogHour.objects.all().filter(workday=workday)
                for log in logs:
                    if log.worker not in workers_objetos:
                        workers_objetos.append(log.worker)


                # Se ordenan los workers
                codigos_workers = []
                for w in workers_objetos:
                    codigos_workers.append(int(w.code))

                codigos_workers.sort();

                workers_ordenados = []
                for codigo in codigos_workers:
                    for w2 in workers_objetos:
                        if (codigo == int(w2.code)):
                            workers_ordenados.append(w2)


                for worker in workers_ordenados:
                    worker.logs = list(logs.filter(worker=worker))
                    worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                    worker.passes_controls_string = LogHour.worker_passes_controls_string(workday, worker.logs)
                    worker.tiene_tarea_especial_todo_el_dia = LogHour.tiene_tarea_especial_todo_el_dia(worker.logs)
                    # expected = 0
                    # if expected > 0:
                    #     percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                    #     if (percent >= 100):
                    #         worker.hours_percent = 100
                    #     else:
                    #         worker.hours_percent = percent
                    # else:
                    #     worker.hours_percent = 100

                    # print("******************************************")
                    # print(workday.date.day)

                    day = str(workday.date.day)
                    if day.__len__() == 1:
                        day = "0" + day
                    month = str(workday.date.month)
                    if month.__len__() == 1:
                        month = "0" + month
                    year = str(workday.date.year)
                    dia = day + "/" + month + "/" + year

                    # print("dia es: " + dia)

                    if ((dia in constants.DIAS_DE_HORAS_EXTRA) or (workday.date.weekday() == 5 or workday.date.weekday() == 6)):
                        worker.passes_controls_string = "mayor"
                        expected = 9
                        percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                        if (percent >= 100):
                            worker.hours_percent = 100
                        else:
                            worker.hours_percent = percent

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

                entrada_activa = ""
                entrada_reactiva = ""
                salida_activa = ""
                salida_reactiva = ""
                ose_entrada = ""
                ose_salida = ""
                texto = workday.comment
                if texto != None:
                    if "utefin" in texto:
                        partes = texto.split("utefin")
                        texto_ute = partes[0]

                        if "eact" in texto_ute:
                            partes_eact = texto_ute.split("eact")
                            entrada_activa = partes_eact[1]

                        if "sact" in texto_ute:
                            partes_sact = texto_ute.split("sact")
                            salida_activa = partes_sact[1]

                        if "ereact" in texto_ute:
                            partes_ereact = texto_ute.split("ereact")
                            entrada_reactiva = partes_ereact[1]

                        if "sreact" in texto_ute:
                            partes_sreact = texto_ute.split("sreact")
                            salida_reactiva = partes_sreact[1]

                        texto_restante = partes[1]
                        if "osesalfin" in texto_restante:
                            partes_ose = texto_restante.split("osesalfin")
                            texto_ose = partes_ose[0]
                            if "oseentfin" in texto_ose:
                                partes_oseent = texto_ose.split("oseentfin")
                                ose_entrada = partes_oseent[0]
                                ose_salida = partes_oseent[1]



                    else:
                        if "osesalfin" in texto:
                            partes_ose = texto.split("osesalfin")
                            texto_ose = partes_ose[0]
                            if "oseentfin" in texto_ose:
                                partes_oseent = texto_ose.split("oseentfin")
                                ose_entrada = partes_oseent[0]
                                ose_salida = partes_oseent[1]




            except IndexError:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        # filter out useless data
        tasks = serialize_tasks_with_logs(tasks)
        keyfunc = itemgetter("category")
        grouped_tasks = [{'name': key, 'tasks': list(grp)} for key, grp in groupby(sorted(tasks, key=keyfunc), key=keyfunc)]
        print("+++++++ GROUPED TASKS +++++++")
        # print(grouped_tasks)
        #for gt in tasks:
            #print(gt['code'] + " - " + gt['name'])
        tareas_que_no_suman = constants.TAREAS_QUE_NO_SUMAN
        tareas_varios_trabajadores = constants.TAREAS_VARIOS_TRABAJADORES
        tareas_especiales_todo_el_dia = constants.TAREAS_ESPECIALES_TODO_EL_DIA

        mostrarUteOse = constants.MOSTRAR_UTE_OSE

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers_ordenados),
            'expected': expected,
            'workday': workday,
            'is_old_workday': is_old_workday,
            'tareas_que_no_suman': tareas_que_no_suman,
            'tareas_varios_trabajadores': tareas_varios_trabajadores,
            'tareas_especiales_todo_el_dia': tareas_especiales_todo_el_dia,
            'entrada_activa': entrada_activa,
            'entrada_reactiva': entrada_reactiva,
            'salida_activa': salida_activa,
            'salida_reactiva': salida_reactiva,
            'ose_entrada': ose_entrada,
            'ose_salida': ose_salida,
            'mostrarUteOse': mostrarUteOse,
            'wda_entrada_activa': wda_entrada_activa,
            'wda_entrada_reactiva': wda_entrada_reactiva,
            'wda_salida_activa': wda_salida_activa,
            'wda_salida_reactiva': wda_salida_reactiva,
            'wda_ose_entrada': wda_ose_entrada,
            'wda_ose_salida': wda_ose_salida
        }

        return render(request, 'tracker/log_hours.html', context)

class LogHoursVista(View):
    def post(self, request, username):
        print("LogHoursVista!")
        tasks = []
        # workers = []
        user = request.user
        is_old_workday = False

        print("se obtiene user")
        user = request.user
        building = None


        # codigo_obra_seleccionada = request.data.get('obra')
        codigo_obra_seleccionada = request.POST['obra']
        print("obra: ")
        print(codigo_obra_seleccionada)
        building = Building.objects.get(code=codigo_obra_seleccionada)

        wday = request.POST['day']
        print("wday: ")
        print(wday)

        # Select the building related to the overseer then obtain its tasks and workers
        #building = Building.objects.get_by_overseer(user)
        if building:
            tasks = building.tasks.all()

            tasks = sorted(tasks, key=attrgetter('code'))

            workers = building.workers.all()
            workers_objetos = []
            for w1 in workers:
                workers_objetos.append(w1)

            date = timezone.localdate(timezone.now())
            try:
                wdayDate = datetime.datetime.strptime(wday, "%d/%m/%Y").date()
                workday = Workday.objects.get(building=building, date=wdayDate)
                if workday.date != date:
                    django_messages.warning(request, messages.OLD_UNFINISHED_WORKDAY)
                    is_old_workday = True
                expected = workday.expected_hours()

                logs = LogHour.objects.all().filter(workday=workday)
                for log in logs:
                    if log.worker not in workers_objetos:
                        workers_objetos.append(log.worker)


                # Se ordenan los workers
                codigos_workers = []
                for w in workers_objetos:
                    codigos_workers.append(int(w.code))

                codigos_workers.sort();

                workers_ordenados = []
                for codigo in codigos_workers:
                    for w2 in workers_objetos:
                        if (codigo == int(w2.code)):
                            workers_ordenados.append(w2)


                for worker in workers_ordenados:
                    worker.logs = list(logs.filter(worker=worker))
                    worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                    worker.passes_controls_string = LogHour.worker_passes_controls_string(workday, worker.logs)
                    worker.tiene_tarea_especial_todo_el_dia = LogHour.tiene_tarea_especial_todo_el_dia(worker.logs)
                    # expected = 0
                    # if expected > 0:
                    #     percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                    #     if (percent >= 100):
                    #         worker.hours_percent = 100
                    #     else:
                    #         worker.hours_percent = percent
                    # else:
                    #     worker.hours_percent = 100

                    # print("******************************************")
                    # print(workday.date.day)

                    day = str(workday.date.day)
                    if day.__len__() == 1:
                        day = "0" + day
                    month = str(workday.date.month)
                    if month.__len__() == 1:
                        month = "0" + month
                    year = str(workday.date.year)
                    dia = day + "/" + month + "/" + year

                    # print("dia es: " + dia)

                    if ((dia in constants.DIAS_DE_HORAS_EXTRA) or (workday.date.weekday() == 5 or workday.date.weekday() == 6)):
                        worker.passes_controls_string = "mayor"
                        expected = 9
                        percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                        if (percent >= 100):
                            worker.hours_percent = 100
                        else:
                            worker.hours_percent = percent

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

                entrada_activa = ""
                entrada_reactiva = ""
                salida_activa = ""
                salida_reactiva = ""
                ose = ""
                texto = workday.comment
                if texto != None:
                    if texto.find("utefin") != -1:
                        partes = texto.split("utefin")
                        texto_ute = partes[0]

                        if "eact" in texto_ute:
                            partes_eact = texto_ute.split("eact")
                            entrada_activa = partes_eact[1]

                        if "sact" in texto_ute:
                            partes_sact = texto_ute.split("sact")
                            salida_activa = partes_sact[1]

                        if "ereact" in texto_ute:
                            partes_ereact = texto_ute.split("ereact")
                            entrada_reactiva = partes_ereact[1]

                        if "sreact" in texto_ute:
                            partes_sreact = texto_ute.split("sreact")
                            salida_reactiva = partes_sreact[1]

                        texto_restante = partes[1]
                        if "osefin" in texto_restante:
                            texto_ose = texto_restante.split("osefin")
                            ose = texto_ose[0]

                    else:
                        if "osefin" in texto:
                            texto_ose2 = texto.split("osefin")
                            ose = texto_ose2[0]




            except IndexError:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        # filter out useless data
        tasks = serialize_tasks_with_logs(tasks)
        keyfunc = itemgetter("category")
        grouped_tasks = [{'name': key, 'tasks': list(grp)} for key, grp in groupby(sorted(tasks, key=keyfunc), key=keyfunc)]
        print("+++++++ GROUPED TASKS +++++++")
        # print(grouped_tasks)
        for gt in tasks:
            print(gt['code'] + " - " + gt['name'])
        tareas_que_no_suman = constants.TAREAS_QUE_NO_SUMAN
        tareas_varios_trabajadores = constants.TAREAS_VARIOS_TRABAJADORES
        tareas_especiales_todo_el_dia = constants.TAREAS_ESPECIALES_TODO_EL_DIA

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers_ordenados),
            'expected': expected,
            'workday': workday,
            'is_old_workday': is_old_workday,
            'tareas_que_no_suman': tareas_que_no_suman,
            'tareas_varios_trabajadores': tareas_varios_trabajadores,
            'tareas_especiales_todo_el_dia': tareas_especiales_todo_el_dia,
            'entrada_activa': entrada_activa,
            'entrada_reactiva': entrada_reactiva,
            'salida_activa': salida_activa,
            'salida_reactiva': salida_reactiva,
            'ose': ose,
            'mostrarUteOse': mostrarUteOse
        }
        return render(request, 'tracker/log_hours_vista.html', context)

class DayReview(View):
    def get(self, request, username):
        overseer = request.user
        building = Building.objects.get_by_overseer(overseer)
        workers_missing_logs = []
        workday = None
        logs = None
        is_old_workday = False
        hay_comentario_ute_ose = False
        hay_comentario_ute = False
        hay_comentario_ose = False
        if building:
            workers = building.workers.all()
            date = timezone.localdate(timezone.now())
            try:
                workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]

                # borrar
                texto = workday.comment
                comentario = ""

                if texto != None:
                    print('texto: ' + texto)
                    if "utefin" in texto:
                        hay_comentario_ute = True
                        partes = texto.split("utefin")
                        texto_restante = partes[1]
                        if "osesalfin" in texto_restante:
                            hay_comentario_ose = True
                            texto_ose = texto_restante.split("osesalfin")
                            comentario = texto_ose[1]

                    else:
                        if "osesalfin" in texto:
                            hay_comentario_ose = True
                            texto_ose2 = texto.split("osesalfin")
                            comentario = texto_ose2[1]
                print('comentario: ' + comentario)
                #fin borrar

                if hay_comentario_ute and hay_comentario_ose:
                    hay_comentario_ute_ose = True;
                    print('hay comentario de ute y ose')
                else:
                    print('no hay comentario de ute y ose')

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
            'is_old_workday': is_old_workday,
            'comentario': comentario,
            'hay_comentario_ute_ose': hay_comentario_ute_ose
        }

        return render(request, 'tracker/day_review.html', context)


class DayReviewSelect(View):
    def get(self, request, username):
        user = request.user
        # view_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_VIEW)
        # workdays = Workday.objects.filter(overseer=user, date__lte=timezone.localdate(timezone.now()), date__gte=view_threshold)
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/day_review_select.html', context)


class PastDays(View):
    def get(self, request, username):
        print('PastDays() - entro en PastDays')
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

        mostrarUteOse = constants.MOSTRAR_UTE_OSE

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

                workers_objetos = []
                for w1 in workers:
                    workers_objetos.append(w1)

                # codigos_workers = []
                # for w in workers:
                #     codigos_workers.append(int(w.code))
                #
                # codigos_workers.sort();
                #
                # workers_ordenados = []
                # for codigo in codigos_workers:
                #     for w2 in workers:
                #         if (codigo == int(w2.code)):
                #             workers_ordenados.append(w2)

                logs = LogHour.objects.all().filter(workday=workday)
                for log in logs:
                    if log.worker not in workers_objetos:
                        workers_objetos.append(log.worker)

                # Se ordenan los workers
                codigos_workers = []
                for w in workers_objetos:
                    codigos_workers.append(int(w.code))

                codigos_workers.sort();

                workers_ordenados = []
                for codigo in codigos_workers:
                    for w2 in workers_objetos:
                        if (codigo == int(w2.code)):
                            workers_ordenados.append(w2)

                tasks = Task.objects.get_by_building(building)
                for worker in workers_ordenados:
                    worker.logs = list(logs.filter(worker=worker))
                    worker.passes_controls = LogHour.worker_passes_controls(workday, worker.logs)
                    worker.passes_controls_string = LogHour.worker_passes_controls_string(workday, worker.logs)
                    worker.tiene_tarea_especial_todo_el_dia = LogHour.tiene_tarea_especial_todo_el_dia(worker.logs)

                    day = str(workday.date.day)
                    if day.__len__() == 1:
                        day = "0" + day
                    month = str(workday.date.month)
                    if month.__len__() == 1:
                        month = "0" + month
                    year = str(workday.date.year)
                    dia = day + "/" + month + "/" + year

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
                            # Si entra en el else es porque hubo un error, hay que imprimir el error
                            worker.hours_percent = 100
                    # if expected > 0:
                    #     worker.hours_percent = round(100 * LogHour.sum_hours(worker.logs) / expected)
                    # else:
                    #     worker.hours_percent = 100
                for task in tasks:
                    task.logs = list(logs.filter(task=task))

                entrada_activa = ""
                entrada_reactiva = ""
                salida_activa = ""
                salida_reactiva = ""
                ose = ""
                texto = workday.comment
                if texto != None:
                    if texto.find("utefin") != -1:
                        partes = texto.split("utefin")
                        texto_ute = partes[0]

                        if "eact" in texto_ute:
                            partes_eact = texto_ute.split("eact")
                            entrada_activa = partes_eact[1]

                        if "sact" in texto_ute:
                            partes_sact = texto_ute.split("sact")
                            salida_activa = partes_sact[1]

                        if "ereact" in texto_ute:
                            partes_ereact = texto_ute.split("ereact")
                            entrada_reactiva = partes_ereact[1]

                        if "sreact" in texto_ute:
                            partes_sreact = texto_ute.split("sreact")
                            salida_reactiva = partes_sreact[1]

                        texto_restante = partes[1]
                        if "osefin" in texto_restante:
                            texto_ose = texto_restante.split("osefin")
                            ose = texto_ose[0]

                    else:
                        if "osefin" in texto:
                            texto_ose2 = texto.split("osefin")
                            ose = texto_ose2[0]

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
        tareas_que_no_suman = constants.TAREAS_QUE_NO_SUMAN
        tareas_varios_trabajadores = constants.TAREAS_VARIOS_TRABAJADORES
        tareas_especiales_todo_el_dia = constants.TAREAS_ESPECIALES_TODO_EL_DIA

        context = {
            'grouped_tasks': grouped_tasks,
            'tasks': tasks,
            'workers': serialize_workers_with_logs(workers_ordenados),
            'expected': expected,
            'workday': workday,
            'hayError': hayError,
            'tareas_que_no_suman': tareas_que_no_suman,
            'tareas_varios_trabajadores': tareas_varios_trabajadores,
            'tareas_especiales_todo_el_dia': tareas_especiales_todo_el_dia,
            'entrada_activa': entrada_activa,
            'entrada_reactiva': entrada_reactiva,
            'salida_activa': salida_activa,
            'salida_reactiva': salida_reactiva,
            'ose': ose,
            'mostrarUteOse': mostrarUteOse
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


class DhtProdReport(View):
    def get(self, request, username):
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/dht_prod_report.html', context)


class DhtLluviasReport(View):
    def get(self, request, username):
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/dht_lluvias_report.html', context)


class DhtBalancinReport(View):
    def get(self, request, username):
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/dht_balancin_report.html', context)


class DhtPlataformaVoladaReport(View):
    def get(self, request, username):
        buildings = Building.objects.all()
        context = {'obras': buildings}
        return render(request, 'tracker/dht_plataforma_volada_report.html', context)


class ReporteUteOse(View):
    def get(self, request, username):
        print("view - entro en ReporteUteOse")
        user = request.user
        view_threshold = timezone.localdate(timezone.now()) - timezone.timedelta(days=config.DAYS_ABLE_TO_VIEW)
        workdays = Workday.objects.filter(overseer=user, date__lte=timezone.localdate(timezone.now()), date__gte=view_threshold)
        buildings = Building.objects.all()
        context = {'workdays': workdays, 'obras': buildings}
        return render(request, 'tracker/ute_ose_report.html', context)
