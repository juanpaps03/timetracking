from django.contrib import messages as django_messages
from django.http import HttpResponse, JsonResponse
from django.shortcuts import redirect
from django.template.defaultfilters import wordcount
from django.utils import timezone
from django.utils.formats import date_format
from django.utils.translation import ugettext_lazy as _
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
            print("volvio***")
            if workday.assign_logs(task_id, hours_per_user):
                print("volvio*** if")
                django_messages.success(request, messages.LOGS_UPDATED)
                return JsonResponse({'message': messages.LOGS_UPDATED}, status=200)
            else:
                print("volvio*** else")
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
        print("Entra en EndDay views api")
        user = request.user
        building = Building.objects.get_by_overseer(user)
        comment = request.data.get('comment', None)

        print("Entra en EndDay comment: " + comment)
        if comment is not None:
            if comment == '':
                comment = None
            else:
                # Chequear si tiene comentarios de ute y ose. Si tiene, hay que declarar comment = None
                # para que se pueda controlar el comentario obligatrio para poder cerrar el workday
                if 'utefin' in comment:
                    partes = comment.split("utefin")
                    if partes[1] == '':
                        comment = None
                    else:
                        if 'osesalfin' in partes[1]:
                            partes2 = partes[1].split("osesalfin")
                            if partes2[1] == '':
                                comment = None
                else:
                    if 'osesalfin' in comment:
                        partes3 = comment.split("osesalfin")
                        if partes3[1] == '':
                            comment = None

        print("Entra en EndDay views api 2")
        # comment is empty unless the day end needs to bypass controls.
        try:
            workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]
            print(workday)
            comentario = workday.comment
            print("Entra en EndDay views api 3")
            print(comentario)
            comentarioUteOse = None

            if comentario is not None:
                if "osesalfin" in comentario:
                    partesOse = comentario.split("osesalfin")
                    comentarioUteOse = partesOse[0]+"osesalfin"
                    print("Entra en EndDay views api 4")
                else:
                    if "utefin" in comentario:
                        partesUte = comentario.split("utefin")
                        comentarioUteOse = partesUte[0]+"utefin"
                        print("Entra en EndDay views api 5")
                    else:
                        comentarioUteOse = None
                        print("Entra en EndDay views api 6")
            else:
                print("Comentario actual del workday es vacío")

            print("Entra en EndDay views api 7")

            if workday.end(comment, comentarioUteOse):
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

        partes = wkday.split("-")
        anio = partes[0]
        mes = partes[1]
        dia = partes[2]
        fecha = dia + "_" + mes + "_" + anio

        user = request.user
        building = Building.objects.get_by_overseer(user)
        if wkday:
            date = datetime.datetime.strptime(wkday, "%Y-%m-%d").date()
            try:
                workday = Workday.objects.get(building=building, date=date)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('Parte_Diario'), building, fecha)
                xlsx_data = workday.get_report()
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)



class DailyReportFromPastDay(APIView):
    def post(self, request, username):
        try:
            print("entro en DailyReportFromPastDay!!!!!!!!")
            workdayDate = request.data.get('workdaydate')

            if workdayDate:
                print(workdayDate)
                partes1 = workdayDate.split("/")
                dia1 = partes1[0]
                mes1 = partes1[1]
                anio1 = partes1[2]

                fecha = anio1 + "_" + mes1 + "_" + dia1

                wkday = datetime.date(int(anio1), int(mes1), int(dia1))

                user = request.user

                building = None
                if user.is_superuser or user.is_staff:
                    print("entra en el else de seleccionar obra")
                    if request.data.get('obra'):
                        codigo_obra_seleccionada = request.data.get('obra')
                        print("obra: ")
                        print(codigo_obra_seleccionada)
                        try:
                            building = Building.objects.get(code=codigo_obra_seleccionada)
                        except Building.DoesNotExist:
                            return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)
                    else:
                        return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)
                else:
                    try:
                        building = Building.objects.get_by_overseer(user)
                    except Building.DoesNotExist:
                        return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)


                if wkday:
                    # date = datetime.datetime.strptime(wkday, "%Y-%m-%d").date()
                    try:
                        workday = Workday.objects.get(building=building, date=wkday)
                        response = HttpResponse(content_type='application/vnd.ms-excel')
                        response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('Parte_Diario'), building, fecha)
                        xlsx_data = workday.get_report()
                        response.write(xlsx_data)
                        return response
                    except Workday.DoesNotExist:
                        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
                    except Exception:
                        return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            else:
                print('workdayDate es vacío')
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)


class DhtReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtReportApi!!!!!!!!")
        initialDay = request.data.get('initialDay')
        finishBiweeklyDay = request.data.get('finishBiweeklyDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishBiweeklyDay)
        print(finishDay)

        user = request.user

        building = None
        print("antes del if")
        if user.is_superuser or user.is_staff:
            print("entra en el else de seleccionar obra")
            codigo_obra_seleccionada = request.data.get('obra')
            print("obra: ")
            print(codigo_obra_seleccionada)
            building = Building.objects.get(code=codigo_obra_seleccionada)
        else:
            building = Building.objects.get_by_overseer(user)

        # building = Building.objects.get_by_overseer(user)

        print("antes del if initial day")

        if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):
            print("despues del if initial day")

            fechaFinal = ""
            if finishDay:
                partes2 = finishDay.split("/")
                dia2 = partes2[0]
                mes2 = partes2[1]
                anio2 = partes2[2]
                fechaFinal = dia2 + "_" + mes2 + "_" + anio2

            print("despues del if initial day")

            partes1 = initialDay.split("/")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            print("despues del if initial day")

            partes3 = finishBiweeklyDay.split("/")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]

            print("despues del if initial day")
            # start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            # end_date = datetime.date(int(anio2), int(mes2), int(dia2))


            # workdays = Workday.objects.filter(overseer=user, date__range=(start_date, end_date))
            # print("Primer for:")
            # for wd in workdays:
            #     print(wd.date)


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


            if fechaFinal:
                rango = fechaInicial + "_a_" + fechaFinal
            else:
                rango = fechaInicial + "_a_" + fechaFinalQuincena

            print("despues del if initial day - " + rango)

            try:
                response = HttpResponse(content_type='application/vnd.ms-excel')
                print("despues del if initial day 2- " + rango)
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_General'), building, rango)
                print("despues del if initial day 2- " + rango)
                xlsx_data = building.get_dht_report_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                print("despues del if initial day 2- " + rango)
                response.write(xlsx_data)
                print("despues del if initial day 2- " + rango)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)



class DhtTasksReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtTasksReportApi!!!!!!!!")


        initialDay = request.data.get('initialDay')
        finishBiweeklyDay = request.data.get('finishBiweeklyDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishBiweeklyDay)
        print(finishDay)

        # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
        print("se obtiene user")
        user = request.user
        building = None
        if user.is_superuser or user.is_staff:
            print("entra en el else de seleccionar obra")
            codigo_obra_seleccionada = request.data.get('obra')
            print("obra: ")
            print(codigo_obra_seleccionada)
            building = Building.objects.get(code=codigo_obra_seleccionada)
        else:
            building = Building.objects.get_by_overseer(user)


        print(user)
        print(user.is_staff)
        print(user.full_name())
        print(user.email)

        if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):

            fechaFinal = ""
            if finishDay:
                partes2 = finishDay.split("/")
                dia2 = partes2[0]
                mes2 = partes2[1]
                anio2 = partes2[2]
                fechaFinal = dia2 + "_" + mes2 + "_" + anio2

            partes1 = initialDay.split("/")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]


            partes3 = finishBiweeklyDay.split("/")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


            if fechaFinal:
                rango = fechaInicial + "_a_" + fechaFinal
            else:
                rango = fechaInicial + "_a_" + fechaFinalQuincena

            try:
                # workday = Workday.objects.get(building=building, date=dateInitial)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_Tareas'), building, rango)
                xlsx_data = building.get_dht_tasks_report_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)



class DhtTasksReportResumenApi(APIView):
    def post(self, request, username):

        try:
            print("entro en DhtTasksReportResumenApi!!!!!!!!")
            print("data***")
            print(request.data)

            initialDay = request.data.get('initialDay')
            finishBiweeklyDay = request.data.get('finishBiweeklyDay')
            finishDay = request.data.get('finishDay')
            print(initialDay)
            print(finishBiweeklyDay)
            print(finishDay)

            # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
            print("se obtiene user")
            user = request.user
            building = None
            if user.is_superuser or user.is_staff:
                print("entra en el if de user is superuser or staff")
                if request.data.get('obra'):
                    codigo_obra_seleccionada = request.data.get('obra')
                    print("obra: ")
                    print(codigo_obra_seleccionada)
                    try:
                        building = Building.objects.get(code=codigo_obra_seleccionada)
                    except Building.DoesNotExist:
                        return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)
                else:
                    return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)
            else:
                try:
                    building = Building.objects.get_by_overseer(user)
                except Building.DoesNotExist:
                    return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)


            print(user)
            print(user.is_staff)
            print(user.full_name())
            print(user.email)

            if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):

                fechaFinal = ""
                if finishDay:
                    partes2 = finishDay.split("/")
                    dia2 = partes2[0]
                    mes2 = partes2[1]
                    anio2 = partes2[2]
                    fechaFinal = dia2 + "_" + mes2 + "_" + anio2

                partes1 = initialDay.split("/")
                dia1 = partes1[0]
                mes1 = partes1[1]
                anio1 = partes1[2]


                partes3 = finishBiweeklyDay.split("/")
                dia3 = partes3[0]
                mes3 = partes3[1]
                anio3 = partes3[2]


                fechaInicial = dia1 + "_" + mes1 + "_" + anio1
                fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


                if fechaFinal:
                    rango = fechaInicial + "_a_" + fechaFinal
                else:
                    rango = fechaInicial + "_a_" + fechaFinalQuincena

                try:
                    # workday = Workday.objects.get(building=building, date=dateInitial)
                    response = HttpResponse(content_type='application/vnd.ms-excel')
                    response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_Tareas_Resumen'), building, rango)
                    xlsx_data = building.get_dht_tasks_report_resumen_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                    response.write(xlsx_data)
                    return response
                except Exception:
                    return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
            return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)
        except Exception:
            print('entra en la excepcion general')
            # return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
            return JsonResponse({'message': 'Algo salió mal. Intente nuevamente.'}, status=500)




class ExistWorkday(APIView):
    def post(self, request, username):

        try:
            print("entro en ExistWorkday!!!!!!!!")
            print("data***")
            print(request.data)

            wd = request.data.get('fecha')
            print(wd)

            # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
            print("se obtiene user")
            user = request.user
            building = None
            if user.is_superuser or user.is_staff:
                print("entra en el if de user is superuser or staff")
                if request.data.get('obra'):
                    codigo_obra_seleccionada = request.data.get('obra')
                    print("obra: ")
                    print(codigo_obra_seleccionada)
                    try:
                        building = Building.objects.get(code=codigo_obra_seleccionada)
                    except Building.DoesNotExist:
                        return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)
                else:
                    return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)
            else:
                try:
                    building = Building.objects.get_by_overseer(user)
                except Building.DoesNotExist:
                    return JsonResponse({'message': messages.BUILDING_NOT_FOUND}, status=400)


            print(user)
            print(user.is_staff)
            print(user.full_name())
            print(user.email)

            print("Antes del if del wd")

            if wd:
                # partes1 = initialDay.split("_")
                # dia1 = partes1[0]
                # mes1 = partes1[1]
                # anio1 = partes1[2]
                # start_date = datetime.date(int(anio1), int(mes1), int(dia1))
                # day = start_date
                #
                # dia = day.day
                # mes = day.month
                # anio = day.year
                # wd = str(anio) + "-" + str(mes) + "-" + str(dia)

                # date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
                print("existe wd")
                print(wd)
                date = datetime.datetime.strptime(wd, "%d/%m/%Y").date()
                print("luego de obtener date")
                print(date)

                try:
                    print("antes de obtener workday")
                    workday = Workday.objects.get(building=building, date=date)
                    print("despues de obtener workday")
                except Workday.DoesNotExist:
                    workday = None
                except Exception:
                    print("entra en excepcion general porque fallo el obtener workday")
                    return JsonResponse({'message': 'Algo salió mal. Intente nuevamente.'}, status=500)

                if workday:
                    print("antes de imprimir workday")
                    print(workday)
                    print("despues de imprimir workday")
                    return JsonResponse({'message': 'Exito, se obtuvo workday'}, status=200)
                else:
                    print('No se obtuvo workday')
                    return JsonResponse({'message': 'El día de trabajo seleccionado no existe.'}, status=400)


            return JsonResponse({'message': 'Fecha es vacía'}, status=400)
        except Exception:
            print('entra en la excepcion general')
            # return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
            return JsonResponse({'message': 'Algo salió mal. Intente nuevamente.'}, status=500)



class DhtProdReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtProdReportApi!!!!!!!!")


        initialDay = request.data.get('initialDay')
        finishBiweeklyDay = request.data.get('finishBiweeklyDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishBiweeklyDay)
        print(finishDay)

        # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
        print("se obtiene user")
        user = request.user
        building = None
        if user.is_superuser or user.is_staff:
            print("entra en el else de seleccionar obra")
            codigo_obra_seleccionada = request.data.get('obra')
            print("obra: ")
            print(codigo_obra_seleccionada)
            building = Building.objects.get(code=codigo_obra_seleccionada)
        else:
            building = Building.objects.get_by_overseer(user)


        print(user)
        print(user.is_staff)
        print(user.full_name())
        print(user.email)

        if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):

            fechaFinal = ""
            if finishDay:
                partes2 = finishDay.split("/")
                dia2 = partes2[0]
                mes2 = partes2[1]
                anio2 = partes2[2]
                fechaFinal = dia2 + "_" + mes2 + "_" + anio2

            partes1 = initialDay.split("/")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]


            partes3 = finishBiweeklyDay.split("/")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


            if fechaFinal:
                rango = fechaInicial + "_a_" + fechaFinal
            else:
                rango = fechaInicial + "_a_" + fechaFinalQuincena

            try:
                # workday = Workday.objects.get(building=building, date=dateInitial)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_Produccion'), building, rango)
                xlsx_data = building.get_dht_prod_report_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)



class DhtLluviasReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtLluviasReportApi!!!!!!!!")


        initialDay = request.data.get('initialDay')
        finishBiweeklyDay = request.data.get('finishBiweeklyDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishBiweeklyDay)
        print(finishDay)

        # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
        print("se obtiene user")
        user = request.user
        building = None
        if user.is_superuser or user.is_staff:
            print("entra en el else de seleccionar obra")
            codigo_obra_seleccionada = request.data.get('obra')
            print("obra: ")
            print(codigo_obra_seleccionada)
            building = Building.objects.get(code=codigo_obra_seleccionada)
        else:
            building = Building.objects.get_by_overseer(user)


        print(user)
        print(user.is_staff)
        print(user.full_name())
        print(user.email)

        if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):

            fechaFinal = ""
            if finishDay:
                partes2 = finishDay.split("/")
                dia2 = partes2[0]
                mes2 = partes2[1]
                anio2 = partes2[2]
                fechaFinal = dia2 + "_" + mes2 + "_" + anio2

            partes1 = initialDay.split("/")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]


            partes3 = finishBiweeklyDay.split("/")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


            if fechaFinal:
                rango = fechaInicial + "_a_" + fechaFinal
            else:
                rango = fechaInicial + "_a_" + fechaFinalQuincena

            try:
                # workday = Workday.objects.get(building=building, date=dateInitial)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_Lluvias'), building, rango)
                xlsx_data = building.get_dht_lluvias_report_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)


class DhtBalancinReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtBalancinReportApi!!!!!!!!")


        initialDay = request.data.get('initialDay')
        finishBiweeklyDay = request.data.get('finishBiweeklyDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishBiweeklyDay)
        print(finishDay)

        # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
        print("se obtiene user")
        user = request.user
        building = None
        if user.is_superuser or user.is_staff:
            print("entra en el else de seleccionar obra")
            codigo_obra_seleccionada = request.data.get('obra')
            print("obra: ")
            print(codigo_obra_seleccionada)
            building = Building.objects.get(code=codigo_obra_seleccionada)
        else:
            building = Building.objects.get_by_overseer(user)


        print(user)
        print(user.is_staff)
        print(user.full_name())
        print(user.email)

        if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):

            fechaFinal = ""
            if finishDay:
                partes2 = finishDay.split("/")
                dia2 = partes2[0]
                mes2 = partes2[1]
                anio2 = partes2[2]
                fechaFinal = dia2 + "_" + mes2 + "_" + anio2

            partes1 = initialDay.split("/")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]


            partes3 = finishBiweeklyDay.split("/")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


            if fechaFinal:
                rango = fechaInicial + "_a_" + fechaFinal
            else:
                rango = fechaInicial + "_a_" + fechaFinalQuincena

            try:
                # workday = Workday.objects.get(building=building, date=dateInitial)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_Balancin'), building, rango)
                xlsx_data = building.get_dht_balancin_report_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)



class DhtPlataformaVoladaReportApi(APIView):
    def post(self, request, username):
        print("entro en DhtPlataformaVoladaReportApi!!!!!!!!")


        initialDay = request.data.get('initialDay')
        finishBiweeklyDay = request.data.get('finishBiweeklyDay')
        finishDay = request.data.get('finishDay')
        print(initialDay)
        print(finishBiweeklyDay)
        print(finishDay)

        # si user es admin: ver cual obra se eligió...sino obtener obra del capataz logueado
        print("se obtiene user")
        user = request.user
        building = None
        if user.is_superuser or user.is_staff:
            print("entra en el else de seleccionar obra")
            codigo_obra_seleccionada = request.data.get('obra')
            print("obra: ")
            print(codigo_obra_seleccionada)
            building = Building.objects.get(code=codigo_obra_seleccionada)
        else:
            building = Building.objects.get_by_overseer(user)


        print(user)
        print(user.is_staff)
        print(user.full_name())
        print(user.email)

        if initialDay and ((finishBiweeklyDay and finishDay) or finishBiweeklyDay):

            fechaFinal = ""
            if finishDay:
                partes2 = finishDay.split("/")
                dia2 = partes2[0]
                mes2 = partes2[1]
                anio2 = partes2[2]
                fechaFinal = dia2 + "_" + mes2 + "_" + anio2

            partes1 = initialDay.split("/")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]


            partes3 = finishBiweeklyDay.split("/")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]


            fechaInicial = dia1 + "_" + mes1 + "_" + anio1
            fechaFinalQuincena = dia3 + "_" + mes3 + "_" + anio3


            if fechaFinal:
                rango = fechaInicial + "_a_" + fechaFinal
            else:
                rango = fechaInicial + "_a_" + fechaFinalQuincena

            try:
                # workday = Workday.objects.get(building=building, date=dateInitial)
                response = HttpResponse(content_type='application/vnd.ms-excel')
                response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('DHT_Plataforma_volada'), building, rango)
                xlsx_data = building.get_dht_plataforma_volada_report_biweekly(fechaInicial, fechaFinalQuincena, fechaFinal)
                response.write(xlsx_data)
                return response
            except Workday.DoesNotExist:
                return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
            except Exception:
                return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
        return JsonResponse({'message': messages.INPUT_DHT_GENERAL_ERROR}, status=400)




class UpdateUteOse(APIView):
    def post(self, request, username):
        print("UpdateUteOse")
        user = request.user
        building = Building.objects.get_by_overseer(user)
        entrada_activa = request.data.get('entrada_activa', None)
        entrada_reactiva = request.data.get('entrada_reactiva', None)
        salida_activa = request.data.get('salida_activa', None)
        salida_reactiva = request.data.get('salida_reactiva', None)
        ose_entrada = request.data.get('ose_entrada', None)
        ose_salida = request.data.get('ose_salida', None)

        print("entrada_activa: " + entrada_activa)
        print("entrada_reactiva: " + entrada_reactiva)
        print("salida_activa: " + salida_activa)
        print("salida_reactiva: " + salida_reactiva)
        print("ose_entrada: " + ose_entrada)
        print("ose_salida: " + ose_salida)

        comentarioUteOse = "eact"+entrada_activa+"eactsact"+salida_activa+"sactereact"+entrada_reactiva+"ereactsreact"+salida_reactiva+"sreactutefin"+ose_entrada+"oseentfin"+ose_salida+"osesalfin"

        print("UpdateUteOse - comentarioUteOse: " + comentarioUteOse)
        # comment is empty unless the day end needs to bypass controls.
        try:
            workday = Workday.objects.filter(building=building, finished=False).order_by('-date')[0]

            comentarioDelDia = ""
            texto = workday.comment
            if texto != None:
                if "utefin" in texto:
                    partes = texto.split("utefin")
                    if partes[1] != None:
                        if "osesalfin" in partes[1]:
                            partes2 = texto.split("osesalfin")
                            if partes2[1] != None:
                                comentarioDelDia = partes2[1]
                else:
                    if "osesalfin" in texto:
                        partes3 = texto.split("osesalfin")
                        if partes3[1] != None:
                            comentarioDelDia = partes3[1]
            if workday.updateUteOse(comentarioUteOse, comentarioDelDia):
                print("UpdateUteOse - entro en if workday updateUteOse")
                django_messages.success(request, messages.UTE_OSE_EMPTY_UPDATE_OK)
                return redirect('tracker:log_hours', username=username)
            else:
                django_messages.warning(request, messages.UTE_OSE_EMPTY)
                return redirect('tracker:log_hours', username=username)
        except IndexError:
            return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)


class ReporteUteOseApi(APIView):
    def post(self, request, username):
        try:
            print("entro en ReporteUteOseApi!!!!!!!!")
            initialDay = request.data.get('initialDay')
            print(initialDay)

            finishDay = request.data.get('finishDay')
            print(finishDay)

            user = request.user

            building = None
            print("antes del if")
            if user.is_superuser or user.is_staff:
                print("entra en el if de usuario oficinista")
                codigo_obra_seleccionada = request.data.get('obra')
                if codigo_obra_seleccionada:
                    print("obra: ")
                    print(codigo_obra_seleccionada)
                    building = Building.objects.get(code=codigo_obra_seleccionada)
                else:
                    return JsonResponse({'message': 'Falta seleccionar obra'}, status=400)
            else:
                # building = Building.objects.get_by_overseer(user)
                print("el usuario no es oficinista ni super user")

            if initialDay:
                partes1 = initialDay.split("/")
                dia1 = partes1[0]
                mes1 = partes1[1]
                anio1 = partes1[2]
                fechaInicial = dia1 + "_" + mes1 + "_" + anio1
                wkday = anio1+"-"+mes1+"-"+dia1
                date = datetime.datetime.strptime(wkday, "%Y-%m-%d").date()

                if finishDay:
                    partes2 = finishDay.split("/")
                    dia2 = partes2[0]
                    mes2 = partes2[1]
                    anio2 = partes2[2]
                    fechaFinal = dia2 + "_" + mes2 + "_" + anio2
                    wkday2 = anio2 + "-" + mes2 + "-" + dia2
                    date2 = datetime.datetime.strptime(wkday2, "%Y-%m-%d").date()

                    diferencia_entre_fechas = date2-date
                    print("diferencia entre fechas:")
                    print(diferencia_entre_fechas)
                    cant_dias = diferencia_entre_fechas.days
                    print("cant_dias:")
                    print(cant_dias)

                    try:
                        workdayInicial = Workday.objects.get(building=building, date=date)
                        workdayFinal = Workday.objects.get(building=building, date=date2)
                        response = HttpResponse(content_type='application/vnd.ms-excel')
                        response['Content-Disposition'] = 'attachment; filename=%s_%s_%s.xlsx' % (_('Reporte_Ute_Ose'), building, fechaInicial)
                        xlsx_data = building.get_reporte_ute_ose(fechaInicial, workdayInicial, fechaFinal, workdayFinal, (cant_dias+1))
                        response.write(xlsx_data)
                        return response
                    except Workday.DoesNotExist:
                        return JsonResponse({'message': messages.WORKDAY_NOT_FOUND}, status=400)
                    except Exception:
                        return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)

                else:
                    return JsonResponse({'message': 'Falta ingresar fecha de fin'}, status=400)

            else:
                return JsonResponse({'message': 'Falta ingresar fecha de inicio'}, status=400)
        except Exception:
            return JsonResponse({'message': messages.GENERIC_ERROR}, status=500)
