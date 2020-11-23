import datetime
import io
from distutils.command.build import build
from datetime import timedelta

import xlsxwriter
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext as __
from docutils.nodes import row

from config import constants
from sabyltimetracker.users.models import User
from tracker import utils
from django.db import IntegrityError

from constance import config
from operator import itemgetter, attrgetter


class BuildingManager(models.Manager):
    # In order to obtain the last building related to the oversee,
    # the queries are always ordered by assigned date.
    def get_queryset(self):
        return super().get_queryset().order_by('-assigned')

    def get_by_overseer(self, user):
        return self.get_queryset().filter(overseer=user).first()

    def get_by_code(self, cod):
        return self.get_queryset().filter(code=cod).first()

class Building(models.Model):
    class Meta:
        verbose_name = _('building')
        verbose_name_plural = _('buildings')

    code = models.PositiveIntegerField(_('code'), null=False, blank=False)
    address = models.CharField(_('address'), blank=True, max_length=255)
    overseer = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True, verbose_name=_('Overseer'))
    workers = models.ManyToManyField('Worker', related_name="buildings", verbose_name=_('Workers'))
    tasks = models.ManyToManyField('Task', related_name="buildings", verbose_name=_('Tasks'))
    assigned = models.DateTimeField(auto_now=False, auto_now_add=True)

    objects = BuildingManager()

    # If the overseer is modified, assigned date is updated.
    # The assigned date is used to get the last building
    # related to the overseer. The last building is used
    # to work along the project.
    def save(self, *args, **kwargs):
        if self.pk:
            old_user = Building.objects.get(pk=self.pk)
            if old_user.overseer != self.overseer:
                self.assigned = timezone.now()
        super(Building, self).save(*args, **kwargs)


    # def get_name(self):
    #     return self.code


    # Deprecated, no se utiliza
    def get_report(self, month, year, type='standard'):
        building = self
        workers = building.workers.all()
        workdays = []
        try:
            workdays = Workday.objects.filter(date__year=year, date__month=month, building=building)
            logs = LogHour.objects.filter(workday__in=workdays)
            for worker in workers:
                worker.logs = logs.filter(worker=worker)
        except ObjectDoesNotExist:
            for worker in workers:
                worker.logs = None

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Monthly Report"))
        title = workbook.add_format({ 'bold': True, 'font_size': 14, 'align': 'left' })
        header = workbook.add_format({ 'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1 })

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'static:images:logo.png')
        if type=='rain':
            r.merge_range('D1:AR1', __('Worked Hours Detail - Rain'), title)
        else:
            r.merge_range('D1:AR1', __('Worked Hours Detail'), title)
        building_info = '%s: %s' % (__('Building'), str(self))
        r.merge_range('D2:AR2', building_info, title)
        date_info = '%s: %s, %s: %s' % (__('Month'), str(month), __('Year'), str(year))
        r.merge_range('D3:AR3', date_info, title)

        # headers row
        r.merge_range('A4:A5', __('Code'), header)
        r.merge_range('B4:B5', __('Full Name'), header)
        r.merge_range('C4:C5', __('VL'), header)
        r.set_column('C:C', 2)
        r.merge_range('D4:D5', __('Cat'), header)
        r.merge_range('E4:E5', __('Holiday'), header)
        r.set_column('E:E', 7)
        r.merge_range('F4:H4', __('Worked Hours'), header)
        r.write('F5', __(u'1ºQ'), header)
        r.set_column('F:F', 4)
        r.write('G5', __(u'2ºQ'), header)
        r.set_column('G:G', 4)
        r.write('H5', __('Total'), header)
        r.set_column('H:H', 4)
        r.merge_range('I4:K4', __('Incentive Hours'), header)
        r.write('I5', __(u'1ºQ'), header)
        r.set_column('I:I', 4)
        r.write('J5', __(u'2ºQ'), header)
        r.set_column('J:J', 4)
        r.write('K5', __('Total'), header)
        r.set_column('K:K', 4)
        r.merge_range('L4:AP4', __('Days'), header)
        i = 1
        for c in range(ord('L'), ord('Z') + 1):
            col = chr(c)
            r.write('%s5' % col, i, header)
            r.set_column('%s:%s' % (col, col), 2)
            i += 1
        for c in range(ord('A'), ord('P') + 1):
            col = chr(c)
            r.write('A%s5' % col, i, header)
            r.set_column('A%s:A%s' % (col, col), 2)
            i += 1
        r.merge_range('AQ4:AR4', __('Ad 1/2 Hour'), header)
        r.write('AQ5', __(u'1ºQ'), header)
        r.set_column('AQ:AQ', 5)
        r.write('AR5', __(u'2ºQ'), header)
        r.set_column('AR:AR', 5)

        # holiday hours
        holidays = workdays.filter(holiday=True)
        holiday_hours = 0
        for holiday in holidays:
            holiday_hours += holiday.expected_hours()

        # cells
        code_width = constants.MIN_WORKER_CODE_WIDTH
        full_name_width = constants.MIN_FULL_NAME_WIDTH
        category_width = constants.MIN_WORKER_CATEGORY_WIDTH

        # username column
        row = 6
        for worker in workers:
            r.write('A%d' % row, worker.code, header)
            r.write('B%d' % row, worker.full_name(), header)
            r.write('D%d' % row, str(worker.category.code), header)
            r.write('E%d' % row, holiday_hours)
            r.write_formula('F%d' % row, '=sum(L%s:Z%s)' % (row, row))  # 1ºQ hours
            r.write_formula('G%d' % row, '=sum(AA%s:AP%s)' % (row, row))  # 2ºQ hours
            r.write_formula('H%d' % row, '=sum(F%s:G%s)' % (row, row))  # total hours
            r.write_formula('K%d' % row, '=sum(I%s:J%s)' % (row, row))  # total incentive

            if len(str(worker.category.code)) > category_width:
                category_width = len(str(worker.category.code))
            if len(worker.code) > code_width:
                code_width = len(worker.code)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name())
            first_additional_half_hours = 0  # first fortnight
            second_additional_half_hours = 0  # second fortnight
            first_incentive_hours = 0  # first fortnight
            second_incentive_hours = 0  # second fortnight
            for day in range(1, 32):
                if type == 'rain':
                    hours = LogHour.sum_hours(worker.logs.filter(workday__date__day=day, task__code=constants.RAIN_CODE))
                else:
                    hours = LogHour.sum_hours(worker.logs.filter(workday__date__day=day, task__in_monthly_report=True))
                r.write('%s%d' % (utils.column_letter(10 + day), row), hours)
                # no half additional hours on strike days.
                if hours >= Workday.additional_half_hour_threshold(day, month, year) and worker.logs.filter(task__code=constants.STRIKE_CODE).count == 0:
                    if day <= 15:
                        first_additional_half_hours += 0.5
                    else:
                        second_additional_half_hours += 0.5
                incentive_hours = Workday.calculate_incentive(day, month, year, building, worker)
                if day <= 15:
                    first_incentive_hours += incentive_hours
                else:
                    second_incentive_hours += incentive_hours
            r.write('AQ%d' % row, first_additional_half_hours)
            r.write('AR%d' % row, second_additional_half_hours)
            r.write('I%d' % row, float('%.2f' % first_incentive_hours))
            r.write('J%d' % row, float('%.2f' % second_incentive_hours))

            row += 1

        r.set_column('A:A', code_width)
        r.set_column('B:B', full_name_width)
        r.set_column('D:D', category_width)

        workbook.close()
        xlsx_data = output.getvalue()
        return xlsx_data



    # no se utiliza - deprecated
    def get_dht_report(self, initialDate, finishDate):
        print("Entro al reporte!!!!")

        building = self
        # tasks = building.tasks.all()
        workers = building.workers.all()

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        print("algo 1")

        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Reporte"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        header_center = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        format_align_left = workbook.add_format({'color': 'black', 'align': 'left', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'red'})
        background_color_number.set_num_format(2)

        print("algo 2")

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.merge_range('D1:J1', __('DHT General'), title)
        building_info = '%s: %s' % (__('Building'), str(building))
        r.merge_range('D2:J2', building_info, title)

        partes1 = initialDate.split("_")
        dia1 = partes1[0]
        mes1 = partes1[1]
        anio1 = partes1[2]
        partes2 = finishDate.split("_")
        dia2 = partes2[0]
        mes2 = partes2[1]
        anio2 = partes2[2]
        iDate = dia1 + "/" + mes1 + "/" + anio1
        fDate = dia2 + "/" + mes2 + "/" + anio2
        range = 'Rango de fechas: ' + iDate + " a " +  fDate
        r.merge_range('D3:J3', range, title)


        # general headers row
        r.merge_range('A4:D4', __('Workers'), header_center)
        r.merge_range('H4:J4', __('HORAS TRABAJADAS'), header_center)
        r.merge_range('K4:M4', __('HORAS INCENTIVOS'), header_center)
        r.merge_range('N4:P4', __('HORAS EXTRAS'), header_center)
        r.merge_range('Q4:S4', __('1/2 HORA ADICIONAL'), header_center)


        # specific headers row
        r.write('A5', __('Ordinal'), header_center)
        r.write('B5', __('Code'), header_center)
        r.write('C5', __('Full Name'), header_center)
        r.write('D5', __('Cat'), header_center)

        r.write('E5', __('VL1'), header_center)
        r.write('F5', __('VL2'), header_center)
        r.write('G5', __('Fer.'), header_center)

        r.write('H5', __('1ªQ'), header_center)
        r.write('I5', __('2ªQ'), header_center)
        r.write('J5', __('TOTAL'), header_center)

        r.write('K5', __('1ªQ'), header_center)
        r.write('L5', __('2ªQ'), header_center)
        r.write('M5', __('TOTAL'), header_center)

        r.write('N5', __('1ªQ'), header_center)
        r.write('O5', __('2ªQ'), header_center)
        r.write('P5', __('TOTAL'), header_center)

        r.write('Q5', __('1ªQ'), header_center)
        r.write('R5', __('2ªQ'), header_center)
        r.write('S5', __('TOTAL'), header_center)



        #Se cargan los días del rango seleccionado
        start_date = datetime.date(int(anio1), int(mes1), int(dia1))
        end_date = datetime.date(int(anio2), int(mes2), int(dia2))

        print("Se imprimen todos los días del rango")
        day = start_date
        col = 20
        indice = 20
        sinHoras = ""
        while day <= end_date:
            print("***NUEVO DÍA***")
            print(day)

            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(day.day), header_center)

            day_aux = day + timedelta(days=1)
            if day.month < day_aux.month or day == end_date:
                print("entro en if de cambio de mes")
                letterMonthStart = utils.column_letter(indice)
                letterMonthEnd = utils.column_letter(col)
                month = utils.traducir_mes(day.month)
                r.merge_range('%s4:%s4' % (letterMonthStart, letterMonthEnd), month + " - " + str(day.year), header_center)
                indice = col + 1


            print("algo por ahí")
            dia = day.day
            mes = day.month
            anio = day.year
            wd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wd:")
            print(wd)

            print("antes")
            date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
            print("despues")
            print("fecha a consultar:")
            print(date)

            try:
                workday = Workday.objects.get(building=building, date=date)
            except Workday.DoesNotExist:
                workday = None
            if workday == None:
                print("No trajo fecha la consulta")

                # Se cargan logs de los trabajadores
                row = 6
                for worker in workers:
                    print("Entro a for de los workers sin workday")
                    r.write('%s%d' % (letter, row), sinHoras)
                    row += 1
            else:
                print("workday no es vacío")
                print(workday)

                #Se cargan logs de los trabajadores
                row = 6
                for worker in workers:
                    print("Entro a for de los workers")
                    worker.logs = list(workday.logs.filter(worker=worker))
                    suma = 0
                    for log in worker.logs:

                        # col = None
                        if log.task.whole_day:
                            # se obtienen las horas esperadas para el día workday
                            text = log.workday.expected_hours()

                            # se controla tareas que no suman
                            # if (log.task.code != 'P'):
                            if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                                if (text == 9):
                                    suma = 9
                                else:
                                    suma = 8
                        else:
                            text = log.amount
                            # se controla tareas que no suman
                            # if (log.task.code != 'P'):
                            if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                                suma = suma + text

                    r.write('%s%d' % (letter, row), suma, number_format)
                    row += 1


            day = day + timedelta(days=1)
            col += 1



        # Se cargan los nombres de los trabajadores
        rowNames = 6
        letterEnd = utils.column_letter(col-1)
        print("letra final: " + letterEnd)
        for worker in workers:
            r.write('B%d' % rowNames, worker.code, header_center_without_bg)
            r.write('C%d' % rowNames, worker.full_name(), format_align_left)
            r.write('D%d' % rowNames, str(worker.category.code), header_center_without_bg)
            r.write_formula('J%d' % rowNames, '=sum(T%d:%s%d)' % (rowNames, letterEnd, rowNames))  # total hours
            rowNames += 1


        # let1 = utils.column_letter(col)
        # let2 = utils.column_letter(col+1)
        # let3 = utils.column_letter(col+2)
        # r.merge_range('%s4:%s4' % (let1, let3), __('1/2 HORAS ADICIONAL'), header_center)
        #
        # r.write('%s5' % let1, __('1ªQ'), header_center)
        # r.write('%s5' % let2, __('2ªQ'), header_center)
        # r.write('%s5' % let3, __('TOTAL'), header_center)



        workbook.close()
        xlsx_data = output.getvalue()

        print("algo 3")
        return xlsx_data






    def get_dht_report_biweekly(self, initialDate, finishBiweeklyDate, finishDate):
        print("Entro al dht general!!!!")

        building = self
        # workers = building.workers.all()
        #
        # q1 = LogHour.objects.filter(workday__gte=datetime.date.today()).filter(workday__lte=datetime.date.today())
        #
        #
        #
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


        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        print("algo 1")

        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Reporte"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        header_center = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg.set_num_format(1)
        format_align_left = workbook.add_format({'color': 'black', 'align': 'left', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'black'})
        background_color_number.set_num_format(2)

        print("algo 2")

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.merge_range('D1:L1', __('DHT General'), title)
        building_info = '%s: %s' % (__('Building'), str(building))
        r.merge_range('D2:L2', building_info, title)


        # general headers row
        r.merge_range('A4:D4', __('Workers'), header_center)
        r.merge_range('H4:J4', __('HORAS TRABAJADAS'), header_center)
        r.merge_range('K4:M4', __('HORAS INCENTIVOS'), header_center)
        r.merge_range('N4:P4', __('HORAS EXTRAS'), header_center)
        r.merge_range('Q4:S4', __('1/2 HORA ADICIONAL'), header_center)

        # specific headers row
        r.write('A5', __('Ordinal'), header_center)
        r.write('B5', __('Code'), header_center)
        r.write('C5', __('Full Name'), header_center)
        r.write('D5', __('Cat'), header_center)

        r.write('E5', __('VL1'), header_center)
        r.write('F5', __('VL2'), header_center)
        r.write('G5', __('Fer.'), header_center)

        r.write('H5', __('1ªQ'), header_center)
        r.write('I5', __('2ªQ'), header_center)
        r.write('J5', __('TOTAL'), header_center)

        r.write('K5', __('1ªQ'), header_center)
        r.write('L5', __('2ªQ'), header_center)
        r.write('M5', __('TOTAL'), header_center)

        r.write('N5', __('1ªQ'), header_center)
        r.write('O5', __('2ªQ'), header_center)
        r.write('P5', __('TOTAL'), header_center)

        r.write('Q5', __('1ªQ'), header_center)
        r.write('R5', __('2ªQ'), header_center)
        r.write('S5', __('TOTAL'), header_center)


        esConsultaDosQuincenas = False

        #Se chequea si se consulta por quincena o por mes
        #Si es por mes (dos quincenas)
        if finishBiweeklyDate and finishDate:
            esConsultaDosQuincenas = True
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]
            partes2 = finishDate.split("_")
            dia2 = partes2[0]
            mes2 = partes2[1]
            anio2 = partes2[2]


            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3
            fDate = dia2 + "/" + mes2 + "/" + anio2

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date = datetime.date(int(anio2), int(mes2), int(dia2))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))
            start_date_second_biweekly = end_date_biweekly + timedelta(days=1)

            diaStartSecondBiweekly = start_date_second_biweekly.day
            mesStartSecondBiweekly = start_date_second_biweekly.month
            anioStartSecondBiweekly = start_date_second_biweekly.year
            diaStartSecondBiweeklyString = str(diaStartSecondBiweekly)
            mesStartSecondBiweeklyString = str(mesStartSecondBiweekly)
            if diaStartSecondBiweeklyString.__len__() == 1:
                diaStartSecondBiweeklyString = "0" + diaStartSecondBiweeklyString
            if mesStartSecondBiweeklyString.__len__() == 1:
                mesStartSecondBiweeklyString = "0" + mesStartSecondBiweeklyString

            fBwStartSecondDate = str(diaStartSecondBiweeklyString) + "/" + str(mesStartSecondBiweeklyString) + "/" + str(anioStartSecondBiweekly)

            range = 'Consulta: ' + iDate + " al " + fBwDate + " y " + fBwStartSecondDate + " al " + fDate
            r.merge_range('D3:L3', range, title)



        else:
            #Sería el caso de finishBiweeklyDate and not finishDate (solo quincena)
            print("solo quincena")
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))

            range = 'Consulta: ' + iDate + " al " + fBwDate
            r.merge_range('D3:J3', range, title)

            end_date = end_date_biweekly

            #Fin de solo quincena

        workers_de_building = building.workers.all()
        workers_objetos = []
        for w1 in workers_de_building:
            workers_objetos.append(w1)

        print('antes del for consulta de logs')
        day_ini = start_date
        while day_ini <= end_date:
            dia = day_ini.day
            mes = day_ini.month
            anio = day_ini.year
            wdd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wdd:")
            print(wdd)

            datedd = datetime.datetime.strptime(wdd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=datedd)
            except Workday.DoesNotExist:
                workday = None

            logs = LogHour.objects.filter(workday=workday)
            for log in logs:
                if log.worker not in workers_objetos:
                    workers_objetos.append(log.worker)

            day_ini = day_ini + timedelta(days=1)

        print('despues del for consulta de logs')

        codigos_workers = []
        for w in workers_objetos:
            codigos_workers.append(int(w.code))

        codigos_workers.sort();

        workers_ordenados = []
        for codigo in codigos_workers:
            for w2 in workers_objetos:
                if (codigo == int(w2.code)):
                    workers_ordenados.append(w2)



        #Se cargan los días del rango seleccionado
        print("Se imprimen todos los días del rango")
        day = start_date
        col = 20
        indice = 20
        sinHoras = ""
        colFinPrimeraQuincena = 20
        diccionarioPrimeraQuincena = {}
        diccionarioSegundaQuincena = {}
        esPrimeraQuincena = True
        arreglo_tareas_varios_trabajadores = []
        while day <= end_date:
            print("***NUEVO DÍA***")
            print(day)
            comentario_del_dia = ""
            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(day.day), header_center)

            day_aux = day + timedelta(days=1)
            if day.month < day_aux.month or day == end_date:
                print("entro en if de cambio de mes")
                letterMonthStart = utils.column_letter(indice)
                letterMonthEnd = utils.column_letter(col)
                month = utils.traducir_mes(day.month)
                r.merge_range('%s4:%s4' % (letterMonthStart, letterMonthEnd), month + " - " + str(day.year), header_center)
                indice = col + 1


            # print("algo por ahí")
            dia = day.day
            mes = day.month
            anio = day.year
            wd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wd:")
            print(wd)

            print("antes")
            date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
            print("despues")
            print("fecha a consultar:")
            print(date)
            #Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=date)
            except Workday.DoesNotExist:
                workday = None
            if workday == None:
                print("No trajo fecha la consulta")

                # Se cargan logs de los trabajadores
                row = 6
                for worker in workers_ordenados:
                    # print("Entro a for de los workers sin workday")
                    r.write('%s%d' % (letter, row), sinHoras)
                    row += 1
            else:
                print("workday no es vacío")
                print(workday)

                # Se cargan logs de los trabajadores
                row = 6
                for worker in workers_ordenados:
                    print("Entro a for de los workers_ordenados")
                    print(worker)
                    print(worker.code)
                    worker.logs = list(workday.logs.filter(worker=worker))
                    suma = 0
                    comentario = ""
                    print("algooo1")
                    for log in worker.logs:
                        # col = None
                        if log.task.whole_day:
                            # se obtienen las horas esperadas para el día workday
                            text = log.workday.expected_hours()

                            print("algooo2")

                            # se controla tareas que no suman
                            if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                                if (text == 9):
                                    suma = 9
                                else:
                                    suma = 8

                        else:
                            print("algooo3")
                            text = log.amount
                            # se controla tareas que no suman
                            if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                                suma = suma + text

                        print("algooo4")
                        # Se cargan las notas. Si es una tarea especial se agrega el codigo de la tarea en el comentario.
                        if log.task.code in constants.TAREAS_VARIOS_TRABAJADORES:
                            print("algooo5")
                            if log.task.code not in arreglo_tareas_varios_trabajadores:
                                print("algooo6")
                                print(log)
                                print(log.task)
                                print(log.task.code)
                                comentario = ""
                                if log.comment:
                                    print(log.comment)
                                    comentario = log.comment
                                else:
                                    print("no hay comentario")
                                arreglo_tareas_varios_trabajadores.append(log.task.code)
                                if comentario_del_dia:
                                    print("algo61")
                                    comentario_del_dia = comentario_del_dia + " ** " + log.task.code + " - " + comentario
                                    print("comentario_del_dia")
                                    print(comentario_del_dia)
                                else:
                                    print("algo62")
                                    comentario_del_dia = log.task.code + " - " + comentario
                                    print("comentario_del_dia")
                                    print(comentario_del_dia)
                                print("algooo66")

                        else:
                            if log.task.code in constants.TAREAS_ESPECIALES:
                                print("algooo7")
                                if log.comment:
                                    if comentario:
                                        comentario = comentario + " ** " + log.task.code + " - " + log.comment
                                    else:
                                        comentario = log.task.code + " - " + log.comment
                                else:
                                    comentario = log.task.code
                            else:
                                print("algooo8")
                                if log.comment:
                                    if comentario:
                                        comentario = comentario + " ** " + log.comment
                                    else:
                                        comentario = log.comment

                    expected = workday.expected_hours()
                    print("algooo9")

                    # Se agrega la nota
                    if comentario:
                        r.write_comment('%s%d' % (letter, row), comentario)
                    print("algooo10")

                    if comentario_del_dia:
                        r.write_comment('%s5' % letter, comentario_del_dia)
                    print("algooo11")

                    # Se controla si se pinta la celda o no
                    if suma != expected:
                        format_cell = background_color_number
                    else:
                        format_cell = number_format

                    print("algooo12")
                    r.write('%s%d' % (letter, row), suma, format_cell)

                    # Para contar horas extras
                    if esPrimeraQuincena:
                        print("esPrimeraQuincenaaaa")
                        if row in diccionarioPrimeraQuincena:
                            if suma > expected:
                                diccionarioPrimeraQuincena[row] = diccionarioPrimeraQuincena[row] + (suma - expected)
                        else:
                            diccionarioPrimeraQuincena[row] = 0
                            if suma > expected:
                                diccionarioPrimeraQuincena[row] = diccionarioPrimeraQuincena[row] + (suma - expected)
                    else:
                        print("esSegundaQuincenaaaaaa")
                        if row in diccionarioSegundaQuincena:
                            if suma > expected:
                                diccionarioSegundaQuincena[row] = diccionarioSegundaQuincena[row] + (suma - expected)
                        else:
                            diccionarioSegundaQuincena[row] = 0
                            if suma > expected:
                                diccionarioSegundaQuincena[row] = diccionarioSegundaQuincena[row] + (suma - expected)

                    row += 1

            print("algooo20")
            if day == end_date_biweekly:
                colFinPrimeraQuincena = col
                esPrimeraQuincena = False

            arreglo_tareas_varios_trabajadores.clear()
            day = day + timedelta(days=1)
            print("algooo21")
            col += 1

        print("algooo22")
        #Se obtiene letra de columna de fin de primera quincena
        letterBiweeklyEnd = utils.column_letter(colFinPrimeraQuincena)
        print("letterBiweeklyEnd: " + letterBiweeklyEnd)


        # Se obtiene letra de columna de comienzo de segunda quincena
        if esConsultaDosQuincenas:
            letterSecondBiweeklyStart = utils.column_letter(colFinPrimeraQuincena+1)
            print("letterSecondBiweeklyStart: " + letterSecondBiweeklyStart)


        # Se cargan los nombres de los trabajadores
        rowNames = 6
        letterEnd = utils.column_letter(col-1)
        print("letra final: " + letterEnd)
        for worker in workers_ordenados:
            r.write('B%d' % rowNames, worker.code, code_header_center_without_bg)
            r.write('C%d' % rowNames, worker.full_name(), format_align_left)
            r.write('D%d' % rowNames, str(worker.category.code), header_center_without_bg)
            r.write_formula('H%d' % rowNames, '=sum(T%d:%s%d)' % (rowNames, letterBiweeklyEnd, rowNames), number_format)  # total hours first biweekly
            if esConsultaDosQuincenas:
                r.write_formula('I%d' % rowNames, '=sum(%s%d:%s%d)' % (letterSecondBiweeklyStart, rowNames, letterEnd, rowNames), number_format)  # total hours second biweekly
            r.write_formula('J%d' % rowNames, '=sum(T%d:%s%d)' % (rowNames, letterEnd, rowNames), number_format)  # total hours

            # Se imprimen horas extras cargadas en los diccionarios
            if diccionarioPrimeraQuincena:
                if rowNames in diccionarioPrimeraQuincena:
                    r.write('N%d' % rowNames, diccionarioPrimeraQuincena[rowNames], number_format)

            if diccionarioSegundaQuincena:
                if rowNames in diccionarioSegundaQuincena:
                    r.write('O%d' % rowNames, diccionarioSegundaQuincena[rowNames], number_format)

            r.write_formula('P%d' % rowNames, '=sum(N%d:O%d)' % (rowNames, rowNames), number_format)  # total horas extra

            rowNames += 1


        workbook.close()
        xlsx_data = output.getvalue()

        print("algo 3")
        return xlsx_data











    def get_dht_tasks_report_biweekly(self, initialDate, finishBiweeklyDate, finishDate):
        print("Entro al dht de tareas!!!!")

        building = self

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        print("algo 1")


        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Reporte"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        header_center = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg.set_num_format(1)
        format_align_left = workbook.add_format({'color': 'black', 'align': 'left', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'black'})
        background_color_number.set_num_format(2)

        print("algo 2")

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.merge_range('D1:L1', __('DHT Tareas'), title)
        building_info = '%s: %s' % (__('Building'), str(building))
        r.merge_range('D2:L2', building_info, title)


        # general headers row
        r.merge_range('C4:E4', __('Workers'), header_center)
        r.merge_range('I4:K4', __('HORAS TRABAJADAS'), header_center)
        r.merge_range('L4:N4', __('HORAS INCENTIVOS'), header_center)
        r.merge_range('O4:Q4', __('HORAS EXTRAS'), header_center)
        r.merge_range('R4:T4', __('1/2 HORA ADICIONAL'), header_center)

        # specific headers row
        r.write('A5', __('Ordinal'), header_center)
        r.write('B5', __('Tarea'), header_center)
        r.write('C5', __('Code'), header_center)
        r.write('D5', __('Full Name'), header_center)
        r.write('E5', __('Cat'), header_center)

        r.write('F5', __('VL1'), header_center)
        r.write('G5', __('VL2'), header_center)
        r.write('H5', __('Fer.'), header_center)

        r.write('I5', __('1ªQ'), header_center)
        r.write('J5', __('2ªQ'), header_center)
        r.write('K5', __('TOTAL'), header_center)

        r.write('L5', __('1ªQ'), header_center)
        r.write('M5', __('2ªQ'), header_center)
        r.write('N5', __('TOTAL'), header_center)

        r.write('O5', __('1ªQ'), header_center)
        r.write('P5', __('2ªQ'), header_center)
        r.write('Q5', __('TOTAL'), header_center)

        r.write('R5', __('1ªQ'), header_center)
        r.write('S5', __('2ªQ'), header_center)
        r.write('T5', __('TOTAL'), header_center)


        esConsultaDosQuincenas = False

        #Se chequea si se consulta por quincena o por mes
        #Si es por mes (dos quincenas)
        if finishBiweeklyDate and finishDate:
            esConsultaDosQuincenas = True
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]
            partes2 = finishDate.split("_")
            dia2 = partes2[0]
            mes2 = partes2[1]
            anio2 = partes2[2]


            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3
            fDate = dia2 + "/" + mes2 + "/" + anio2

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date = datetime.date(int(anio2), int(mes2), int(dia2))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))
            start_date_second_biweekly = end_date_biweekly + timedelta(days=1)

            diaStartSecondBiweekly = start_date_second_biweekly.day
            mesStartSecondBiweekly = start_date_second_biweekly.month
            anioStartSecondBiweekly = start_date_second_biweekly.year
            diaStartSecondBiweeklyString = str(diaStartSecondBiweekly)
            mesStartSecondBiweeklyString = str(mesStartSecondBiweekly)
            if diaStartSecondBiweeklyString.__len__() == 1:
                diaStartSecondBiweeklyString = "0" + diaStartSecondBiweeklyString
            if mesStartSecondBiweeklyString.__len__() == 1:
                mesStartSecondBiweeklyString = "0" + mesStartSecondBiweeklyString

            fBwStartSecondDate = str(diaStartSecondBiweeklyString) + "/" + str(mesStartSecondBiweeklyString) + "/" + str(anioStartSecondBiweekly)

            range = 'Consulta: ' + iDate + " al " + fBwDate + " y " + fBwStartSecondDate + " al " + fDate
            r.merge_range('D3:L3', range, title)



        else:
            #Sería el caso de finishBiweeklyDate and not finishDate (solo quincena)
            print("solo quincena")
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))

            range = 'Consulta: ' + iDate + " al " + fBwDate
            r.merge_range('D3:J3', range, title)

            end_date = end_date_biweekly

            #Fin de solo quincena

        tasks_de_building = building.tasks.all()
        tasks_objetos = []
        for t in tasks_de_building:
            tasks_objetos.append(t)

        workers_de_building = building.workers.all()
        workers_objetos = []
        for w1 in workers_de_building:
            workers_objetos.append(w1)

        print('antes del for consulta de logs')
        day_ini = start_date
        while day_ini <= end_date:
            dia = day_ini.day
            mes = day_ini.month
            anio = day_ini.year
            wdd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wdd:")
            print(wdd)

            datedd = datetime.datetime.strptime(wdd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=datedd)
            except Workday.DoesNotExist:
                workday = None

            logs = LogHour.objects.filter(workday=workday)
            for log in logs:
                if log.worker not in workers_objetos:
                    workers_objetos.append(log.worker)
                if log.task not in tasks_objetos:
                    tasks_objetos.append(log.task)

            day_ini = day_ini + timedelta(days=1)
        print('despues del for consulta de logs')




        #Se cargan los días del rango seleccionado
        day = start_date
        col = 21
        indice = 21
        sinHoras = ""
        colFinPrimeraQuincena = 21
        diccionarioPrimeraQuincena = {}
        diccionarioSegundaQuincena = {}
        esPrimeraQuincena = True

        logs_principal = {}

        while day <= end_date:
            print("***NUEVO DÍA***")
            # print(day)

            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(day.day), header_center)

            day_aux = day + timedelta(days=1)
            if day.month < day_aux.month or day == end_date:
                print("entro en if de cambio de mes")
                letterMonthStart = utils.column_letter(indice)
                letterMonthEnd = utils.column_letter(col)
                month = utils.traducir_mes(day.month)
                r.merge_range('%s4:%s4' % (letterMonthStart, letterMonthEnd), month + " - " + str(day.year), header_center)
                indice = col + 1



            # print("algo por ahí")
            dia = day.day
            mes = day.month
            anio = day.year
            wd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wd:")
            print(wd)

            # print("antes")
            date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
            #Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=date)
            except Workday.DoesNotExist:
                workday = None
            if workday == None:
                print("No trajo fecha la consulta")

                # Se cargan logs de los trabajadores
                row = 6
                for worker in workers_objetos:
                    # print("Entro a for de los workers sin workday")
                    r.write('%s%d' % (letter, row), sinHoras)
                    row += 1
            else:
                print("workday no es vacío")

                for tarea in tasks_objetos:
                    try:
                        logs = LogHour.objects.filter(workday=workday, task=tarea)
                    except LogHour.DoesNotExist:
                        logs = None

                    # print("despues de ir a buscar los logs")

                    if logs:
                        arreglo = []
                        for log in logs:
                            # print("for de logs")
                            tupla = (letter, log.worker, log.amount)
                            arreglo.append(tupla)



                        if tarea.code in logs_principal:
                            # print("entra al if tarea code")
                            for tup in arreglo:
                                arr = logs_principal[tarea.code]
                                arr.append(tup)
                                logs_principal[tarea.code] = arr
                        else:
                            logs_principal.update({tarea.code : arreglo})

            if day == end_date_biweekly:
                colFinPrimeraQuincena = col
                # esPrimeraQuincena = False


            day = day + timedelta(days=1)
            col += 1


        # Se obtiene letra de columna de fin de primera quincena
        letterBikeekyEnd = utils.column_letter(colFinPrimeraQuincena)
        print("letterBikeekyEnd: " + letterBikeekyEnd)

        # Se obtiene letra de columna de comienzo de segunda quincena
        if esConsultaDosQuincenas:
            letterSecondBikeekyStart = utils.column_letter(colFinPrimeraQuincena + 1)
            print("letterSecondBikeekyStart: " + letterSecondBikeekyStart)

        print("LOGS PRINCIPAL******************")
        print("")

        class ColumnaMonto():
            def __init__(self, col, monto):
                self.col = col
                self.monto = monto

            # def __str__(self):
            #     return '%s - %s' % (self.code, self.name)

        class WorkerAux():
            wkr = Worker()
            lista_columna_monto = []

            def __init__(self, wkr, lista):
                self.wkr = wkr
                self.lista_columna_monto = lista

            # def __str__(self):
            #     return '%s' % self.code




        # Se ordenan alfabéticamente las tareas de logs_principal
        logs_principal_ord = dict(sorted(logs_principal.items()))

        fila = 6
        letterEnd = utils.column_letter(col - 1)
        # tar es el codigo de tarea
        for tar in logs_principal_ord:

            if tar == 'D11':
                print("es D11")

            print(tar + ": " + str(logs_principal_ord[tar]))

            arreglo_de_workers = []
            arreglo_de_tuplas = logs_principal_ord[tar]
            cant = len(logs_principal_ord[tar])

            lista_workers_final = []

            i = 0
            while i<cant:

                objeto = ColumnaMonto(arreglo_de_tuplas[i][0],arreglo_de_tuplas[i][2])

                # i = 0, 1, 2 ...cant-1
                if arreglo_de_tuplas[i][1] not in arreglo_de_workers:
                    wkr_aux = WorkerAux(arreglo_de_tuplas[i][1], [])
                    wkr_aux.lista_columna_monto.append(objeto)

                    lista_workers_final.append(wkr_aux)

                    arreglo_de_workers.append(arreglo_de_tuplas[i][1])

                else:

                    for x in lista_workers_final:
                        if arreglo_de_tuplas[i][1] == x.wkr:
                            x.lista_columna_monto.append(objeto)

                i += 1


            # print("SE IMPRIME LISTA DE WORKERS FINAL DE UNA TAREA (filas de una tarea a imprimir)")
            for w in lista_workers_final:
                r.write('B%d' % fila, tar, header_center_without_bg)
                r.write('C%d' % fila, w.wkr.code, code_header_center_without_bg)
                r.write('D%d' % fila, w.wkr.full_name(), format_align_left)
                r.write('E%d' % fila, str(w.wkr.category.code), header_center_without_bg)
                r.write_formula('I%d' % fila, '=sum(U%d:%s%d)' % (fila, letterBikeekyEnd, fila), number_format)  # total hours first biweekly
                if esConsultaDosQuincenas:
                    r.write_formula('J%d' % fila, '=sum(%s%d:%s%d)' % (letterSecondBikeekyStart, fila, letterEnd, fila), number_format)  # total hours second biweekly
                r.write_formula('K%d' % fila, '=sum(I%d:J%d)' % (fila, fila), number_format)  # total hours

                for nodo in w.lista_columna_monto:
                    r.write('%s%d' % (nodo.col, fila), nodo.monto , number_format)

                fila += 1
                # print(w.wkr.full_name())
                # for celda in w.lista_columna_monto:
                #     print("col: " + celda.col + " - " + "monto: " + str(celda.monto))



            print("")
            print("")

        workbook.close()
        xlsx_data = output.getvalue()

        print("algo 3")
        return xlsx_data








    def get_dht_tasks_report_resumen_biweekly(self, initialDate, finishBiweeklyDate, finishDate):
        print("Entro al reporte tareas resumen!!!!")

        building = self

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        print("algo 1")


        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Reporte"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        title_center = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'center'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        header_center = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        format_align_left = workbook.add_format({'color': 'black', 'align': 'left', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'black'})
        background_color_number.set_num_format(2)

        print("algo 2")

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title_center)
        r.insert_image('B1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.write('A4', __('OBRA'), title)
        building_info = str(building.code) + ' - ' + building.address
        r.merge_range('B4:C4', building_info, title)
        r.write('A5', __('FECHA'), title)


        # general headers row
        r.write('A6', __('TAREAS A JORNAL'), header_center)
        r.write('A7', __('Codigo tarea'), header_center)
        r.write('B7', __('OFICIAL'), header_center)
        r.write('C7', __('PEÓN'), header_center)


        esConsultaDosQuincenas = False

        # Se chequea si se consulta por quincena o por mes
        # Si es por mes (dos quincenas)
        if finishBiweeklyDate and finishDate:
            esConsultaDosQuincenas = True
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]
            partes2 = finishDate.split("_")
            dia2 = partes2[0]
            mes2 = partes2[1]
            anio2 = partes2[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3
            fDate = dia2 + "/" + mes2 + "/" + anio2

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date = datetime.date(int(anio2), int(mes2), int(dia2))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))
            start_date_second_biweekly = end_date_biweekly + timedelta(days=1)

            diaStartSecondBiweekly = start_date_second_biweekly.day
            mesStartSecondBiweekly = start_date_second_biweekly.month
            anioStartSecondBiweekly = start_date_second_biweekly.year
            diaStartSecondBiweeklyString = str(diaStartSecondBiweekly)
            mesStartSecondBiweeklyString = str(mesStartSecondBiweekly)
            if diaStartSecondBiweeklyString.__len__() == 1:
                diaStartSecondBiweeklyString = "0" + diaStartSecondBiweeklyString
            if mesStartSecondBiweeklyString.__len__() == 1:
                mesStartSecondBiweeklyString = "0" + mesStartSecondBiweeklyString

            fBwStartSecondDate = str(diaStartSecondBiweeklyString) + "/" + str(
                mesStartSecondBiweeklyString) + "/" + str(anioStartSecondBiweekly)

            range = iDate + " al " + fBwDate + " y " + fBwStartSecondDate + " al " + fDate
            r.merge_range('B5:C5', range, title)


        else:
            # Sería el caso de finishBiweeklyDate and not finishDate (solo quincena)
            print("solo quincena")
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))

            range = iDate + " al " + fBwDate
            r.merge_range('B5:C5', range, title)

            end_date = end_date_biweekly

            # Fin de solo quincena

        tasks_de_building = building.tasks.all()
        tasks_objetos = []
        for t in tasks_de_building:
            tasks_objetos.append(t)

        print('antes del for consulta de logs')
        day_ini = start_date
        while day_ini <= end_date:
            dia = day_ini.day
            mes = day_ini.month
            anio = day_ini.year
            wdd = str(anio) + "-" + str(mes) + "-" + str(dia)
            # print("wdd:")
            # print(wdd)

            datedd = datetime.datetime.strptime(wdd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=datedd)
            except Workday.DoesNotExist:
                workday = None

            logs = LogHour.objects.filter(workday=workday)
            for log in logs:
                if log.task not in tasks_objetos:
                    tasks_objetos.append(log.task)

            day_ini = day_ini + timedelta(days=1)
        print('despues del for consulta de logs')




        # Se cargan los días del rango seleccionado
        day = start_date
        filas_principal = {}

        class HorasOficialPeon():
            def __init__(self, horas_oficial, horas_peon):
                self.horas_oficial = horas_oficial
                self.horas_peon = horas_peon

            def __str__(self):
                return '%s - %s' % (str(self.horas_oficial), str(self.horas_peon))

        while day <= end_date:
            # print("algo por ahí")
            dia = day.day
            mes = day.month
            anio = day.year
            wd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wd:")
            print(wd)

            # print("antes")
            date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=date)
            except Workday.DoesNotExist:
                workday = None
            if workday == None:
                print("No trajo fecha la consulta")

            else:
                print("workday no es vacío")

                for tarea in tasks_objetos:
                    try:
                        logs = LogHour.objects.filter(workday=workday, task=tarea)
                    except LogHour.DoesNotExist:
                        logs = None

                    # print("despues de ir a buscar los logs")

                    if logs:
                        print("Entra en if de logs")
                        arreglo = []
                        for log in logs:
                            if tarea.code in filas_principal:
                                print("if tarea")
                                worker = Worker.objects.get(code=log.worker_id)
                                horas_oficial_peon_aux = filas_principal[tarea.code]
                                if 'OFICIAL' in worker.category_id:
                                    horas_oficial_peon_aux.horas_oficial = horas_oficial_peon_aux.horas_oficial + log.amount
                                else:
                                    horas_oficial_peon_aux.horas_peon = horas_oficial_peon_aux.horas_peon + log.amount
                                filas_principal[tarea.code] = horas_oficial_peon_aux
                            else:
                                print("else tarea")
                                worker = Worker.objects.get(code=log.worker_id)
                                print("algo 15")
                                # horas_oficial_peon_aux = filas_principal[tarea.code]

                                print("algo 16")
                                if 'OFICIAL' in worker.category_id:
                                    horas_oficial_peon = HorasOficialPeon(log.amount, 0)
                                    print("algo 17")
                                else:
                                    horas_oficial_peon = HorasOficialPeon(0, log.amount)
                                    print("algo 18")
                                print("algo 19")
                                filas_principal.update({tarea.code: horas_oficial_peon})
                                print("algo 20")
            day = day + timedelta(days=1)


        # Se ordenan alfabéticamente las tareas de logs_principal
        filas_principal_ord = dict(sorted(filas_principal.items()))

        print("FILASSSSSS")
        fila = 8
        for key in filas_principal_ord:
            print(key)
            print(filas_principal_ord[key])
            print('***')

            r.write('A%s' % fila, key, header_center_without_bg)
            r.write('B%d' % fila, filas_principal_ord[key].horas_oficial, number_format)
            r.write('C%d' % fila, filas_principal_ord[key].horas_peon, number_format)
            fila+=1

        r.write_formula('B6', '=sum(B8:B%d)' % (fila-1), number_format)  # total hours oficial
        r.write_formula('C6', '=sum(C8:C%d)' % (fila-1), number_format)  # total hours peon

        r.set_column('A:C', 17)
        r.set_row(0, 25)
        # r.set_row(1, 8)
        # r.set_row(2, 8)


        workbook.close()
        xlsx_data = output.getvalue()

        print("algo 3")
        return xlsx_data










    def get_dht_prod_report_biweekly(self, initialDate, finishBiweeklyDate, finishDate):
        print("Entro al dht de produccion!!!!")

        building = self

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        print("algo 1")


        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Reporte"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        header_center = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg.set_num_format(1)
        format_align_left = workbook.add_format({'color': 'black', 'align': 'left', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'black'})
        background_color_number.set_num_format(2)

        print("algo 2")

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.merge_range('D1:L1', __('DHT Producción'), title)
        building_info = '%s: %s' % (__('Building'), str(building))
        r.merge_range('D2:L2', building_info, title)


        # general headers row
        r.merge_range('C4:E4', __('Workers'), header_center)
        r.merge_range('I4:K4', __('HORAS TRABAJADAS'), header_center)
        r.merge_range('L4:N4', __('HORAS INCENTIVOS'), header_center)
        r.merge_range('O4:Q4', __('HORAS EXTRAS'), header_center)
        r.merge_range('R4:T4', __('1/2 HORA ADICIONAL'), header_center)

        # specific headers row
        r.write('A5', __('Ordinal'), header_center)
        r.write('B5', __('Tarea'), header_center)
        r.write('C5', __('Code'), header_center)
        r.write('D5', __('Full Name'), header_center)
        r.write('E5', __('Cat'), header_center)

        r.write('F5', __('VL1'), header_center)
        r.write('G5', __('VL2'), header_center)
        r.write('H5', __('Fer.'), header_center)

        r.write('I5', __('1ªQ'), header_center)
        r.write('J5', __('2ªQ'), header_center)
        r.write('K5', __('TOTAL'), header_center)

        r.write('L5', __('1ªQ'), header_center)
        r.write('M5', __('2ªQ'), header_center)
        r.write('N5', __('TOTAL'), header_center)

        r.write('O5', __('1ªQ'), header_center)
        r.write('P5', __('2ªQ'), header_center)
        r.write('Q5', __('TOTAL'), header_center)

        r.write('R5', __('1ªQ'), header_center)
        r.write('S5', __('2ªQ'), header_center)
        r.write('T5', __('TOTAL'), header_center)


        esConsultaDosQuincenas = False

        #Se chequea si se consulta por quincena o por mes
        #Si es por mes (dos quincenas)
        if finishBiweeklyDate and finishDate:
            esConsultaDosQuincenas = True
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]
            partes2 = finishDate.split("_")
            dia2 = partes2[0]
            mes2 = partes2[1]
            anio2 = partes2[2]


            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3
            fDate = dia2 + "/" + mes2 + "/" + anio2

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date = datetime.date(int(anio2), int(mes2), int(dia2))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))
            start_date_second_biweekly = end_date_biweekly + timedelta(days=1)

            diaStartSecondBiweekly = start_date_second_biweekly.day
            mesStartSecondBiweekly = start_date_second_biweekly.month
            anioStartSecondBiweekly = start_date_second_biweekly.year
            diaStartSecondBiweeklyString = str(diaStartSecondBiweekly)
            mesStartSecondBiweeklyString = str(mesStartSecondBiweekly)
            if diaStartSecondBiweeklyString.__len__() == 1:
                diaStartSecondBiweeklyString = "0" + diaStartSecondBiweeklyString
            if mesStartSecondBiweeklyString.__len__() == 1:
                mesStartSecondBiweeklyString = "0" + mesStartSecondBiweeklyString

            fBwStartSecondDate = str(diaStartSecondBiweeklyString) + "/" + str(mesStartSecondBiweeklyString) + "/" + str(anioStartSecondBiweekly)

            range = 'Consulta: ' + iDate + " al " + fBwDate + " y " + fBwStartSecondDate + " al " + fDate
            r.merge_range('D3:L3', range, title)



        else:
            #Sería el caso de finishBiweeklyDate and not finishDate (solo quincena)
            print("solo quincena")
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))

            range = 'Consulta: ' + iDate + " al " + fBwDate
            r.merge_range('D3:J3', range, title)

            end_date = end_date_biweekly

            #Fin de solo quincena

        tasks_de_building = building.tasks.all()
        tasks_objetos = []
        for t in tasks_de_building:
            sub = t.code[:2]
            if sub.lower() == "sc":
                tasks_objetos.append(t)

        workers_de_building = building.workers.all()
        workers_objetos = []
        for w1 in workers_de_building:
            workers_objetos.append(w1)

        print('antes del for consulta de logs')
        day_ini = start_date
        while day_ini <= end_date:
            dia = day_ini.day
            mes = day_ini.month
            anio = day_ini.year
            wdd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wdd:")
            print(wdd)

            datedd = datetime.datetime.strptime(wdd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=datedd)
            except Workday.DoesNotExist:
                workday = None

            logs = LogHour.objects.filter(workday=workday)
            for log in logs:
                if log.worker not in workers_objetos:
                    workers_objetos.append(log.worker)
                if log.task not in tasks_objetos:
                    sub = log.task.code[:2]
                    if sub.lower() == "sc":
                        tasks_objetos.append(log.task)

            day_ini = day_ini + timedelta(days=1)
        print('despues del for consulta de logs')




        #Se cargan los días del rango seleccionado
        day = start_date
        col = 21
        indice = 21
        sinHoras = ""
        colFinPrimeraQuincena = 21
        diccionarioPrimeraQuincena = {}
        diccionarioSegundaQuincena = {}
        esPrimeraQuincena = True

        logs_principal = {}

        while day <= end_date:
            print("***NUEVO DÍA***")
            # print(day)

            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(day.day), header_center)

            day_aux = day + timedelta(days=1)
            if day.month < day_aux.month or day == end_date:
                print("entro en if de cambio de mes")
                letterMonthStart = utils.column_letter(indice)
                letterMonthEnd = utils.column_letter(col)
                month = utils.traducir_mes(day.month)
                r.merge_range('%s4:%s4' % (letterMonthStart, letterMonthEnd), month + " - " + str(day.year), header_center)
                indice = col + 1



            # print("algo por ahí")
            dia = day.day
            mes = day.month
            anio = day.year
            wd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wd:")
            print(wd)

            # print("antes")
            date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
            #Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=date)
            except Workday.DoesNotExist:
                workday = None
            if workday == None:
                print("No trajo fecha la consulta")

                # Se cargan logs de los trabajadores
                row = 6
                for worker in workers_objetos:
                    # print("Entro a for de los workers sin workday")
                    r.write('%s%d' % (letter, row), sinHoras)
                    row += 1
            else:
                print("workday no es vacío")

                for tarea in tasks_objetos:
                    try:
                        logs = LogHour.objects.filter(workday=workday, task=tarea)
                    except LogHour.DoesNotExist:
                        logs = None

                    # print("despues de ir a buscar los logs")

                    if logs:
                        arreglo = []
                        for log in logs:
                            # print("for de logs")
                            tupla = (letter, log.worker, log.amount)
                            arreglo.append(tupla)



                        if tarea.code in logs_principal:
                            # print("entra al if tarea code")
                            for tup in arreglo:
                                arr = logs_principal[tarea.code]
                                arr.append(tup)
                                logs_principal[tarea.code] = arr
                        else:
                            logs_principal.update({tarea.code : arreglo})

            if day == end_date_biweekly:
                colFinPrimeraQuincena = col
                # esPrimeraQuincena = False


            day = day + timedelta(days=1)
            col += 1


        # Se obtiene letra de columna de fin de primera quincena
        letterBikeekyEnd = utils.column_letter(colFinPrimeraQuincena)
        print("letterBikeekyEnd: " + letterBikeekyEnd)

        # Se obtiene letra de columna de comienzo de segunda quincena
        if esConsultaDosQuincenas:
            letterSecondBikeekyStart = utils.column_letter(colFinPrimeraQuincena + 1)
            print("letterSecondBikeekyStart: " + letterSecondBikeekyStart)

        print("LOGS PRINCIPAL******************")
        print("")

        class ColumnaMonto():
            def __init__(self, col, monto):
                self.col = col
                self.monto = monto

            # def __str__(self):
            #     return '%s - %s' % (self.code, self.name)

        class WorkerAux():
            wkr = Worker()
            lista_columna_monto = []

            def __init__(self, wkr, lista):
                self.wkr = wkr
                self.lista_columna_monto = lista

            # def __str__(self):
            #     return '%s' % self.code




        # Se ordenan alfabéticamente las tareas de logs_principal
        logs_principal_ord = dict(sorted(logs_principal.items()))

        fila = 6
        letterEnd = utils.column_letter(col - 1)
        # tar es el codigo de tarea
        for tar in logs_principal_ord:

            if tar == 'D11':
                print("es D11")

            print(tar + ": " + str(logs_principal_ord[tar]))

            arreglo_de_workers = []
            arreglo_de_tuplas = logs_principal_ord[tar]
            cant = len(logs_principal_ord[tar])

            lista_workers_final = []

            i = 0
            while i<cant:

                objeto = ColumnaMonto(arreglo_de_tuplas[i][0],arreglo_de_tuplas[i][2])

                # i = 0, 1, 2 ...cant-1
                if arreglo_de_tuplas[i][1] not in arreglo_de_workers:
                    wkr_aux = WorkerAux(arreglo_de_tuplas[i][1], [])
                    wkr_aux.lista_columna_monto.append(objeto)

                    lista_workers_final.append(wkr_aux)

                    arreglo_de_workers.append(arreglo_de_tuplas[i][1])

                else:

                    for x in lista_workers_final:
                        if arreglo_de_tuplas[i][1] == x.wkr:
                            x.lista_columna_monto.append(objeto)

                i += 1


            # print("SE IMPRIME LISTA DE WORKERS FINAL DE UNA TAREA (filas de una tarea a imprimir)")
            for w in lista_workers_final:
                r.write('B%d' % fila, tar, header_center_without_bg)
                r.write('C%d' % fila, w.wkr.code, code_header_center_without_bg)
                r.write('D%d' % fila, w.wkr.full_name(), format_align_left)
                r.write('E%d' % fila, str(w.wkr.category.code), header_center_without_bg)
                r.write_formula('I%d' % fila, '=sum(U%d:%s%d)' % (fila, letterBikeekyEnd, fila), number_format)  # total hours first biweekly
                if esConsultaDosQuincenas:
                    r.write_formula('J%d' % fila, '=sum(%s%d:%s%d)' % (letterSecondBikeekyStart, fila, letterEnd, fila), number_format)  # total hours second biweekly
                r.write_formula('K%d' % fila, '=sum(I%d:J%d)' % (fila, fila), number_format)  # total hours

                for nodo in w.lista_columna_monto:
                    r.write('%s%d' % (nodo.col, fila), nodo.monto , number_format)

                fila += 1
                # print(w.wkr.full_name())
                # for celda in w.lista_columna_monto:
                #     print("col: " + celda.col + " - " + "monto: " + str(celda.monto))



            print("")
            print("")

        workbook.close()
        xlsx_data = output.getvalue()

        print("algo 3")
        return xlsx_data






    def get_dht_lluvias_report_biweekly(self, initialDate, finishBiweeklyDate, finishDate):
        print("Entro al dht de lluvias!!!!")

        building = self

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        print("algo 1")

        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Reporte"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        header_center = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg = workbook.add_format({'color': 'black', 'align': 'center', 'border': 1})
        code_header_center_without_bg.set_num_format(1)
        format_align_left = workbook.add_format({'color': 'black', 'align': 'left', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'black'})
        background_color_number.set_num_format(2)

        print("algo 2")

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.merge_range('D1:L1', __('DHT Lluvias'), title)
        building_info = '%s: %s' % (__('Building'), str(building))
        r.merge_range('D2:L2', building_info, title)

        # general headers row
        r.merge_range('B4:D4', __('Workers'), header_center)
        r.merge_range('H4:J4', __('HORAS TRABAJADAS'), header_center)
        r.merge_range('K4:M4', __('HORAS INCENTIVOS'), header_center)
        r.merge_range('N4:P4', __('HORAS EXTRAS'), header_center)
        r.merge_range('Q4:S4', __('1/2 HORA ADICIONAL'), header_center)

        # specific headers row
        r.write('A5', __('Ordinal'), header_center)
        # r.write('B5', __('Tarea'), header_center)
        r.write('B5', __('Code'), header_center)
        r.write('C5', __('Full Name'), header_center)
        r.write('D5', __('Cat'), header_center)

        r.write('E5', __('VL1'), header_center)
        r.write('F5', __('VL2'), header_center)
        r.write('G5', __('Fer.'), header_center)

        r.write('H5', __('1ªQ'), header_center)
        r.write('I5', __('2ªQ'), header_center)
        r.write('J5', __('TOTAL'), header_center)

        r.write('K5', __('1ªQ'), header_center)
        r.write('L5', __('2ªQ'), header_center)
        r.write('M5', __('TOTAL'), header_center)

        r.write('N5', __('1ªQ'), header_center)
        r.write('O5', __('2ªQ'), header_center)
        r.write('P5', __('TOTAL'), header_center)

        r.write('Q5', __('1ªQ'), header_center)
        r.write('R5', __('2ªQ'), header_center)
        r.write('S5', __('TOTAL'), header_center)

        esConsultaDosQuincenas = False

        # Se chequea si se consulta por quincena o por mes
        # Si es por mes (dos quincenas)
        if finishBiweeklyDate and finishDate:
            esConsultaDosQuincenas = True
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]
            partes2 = finishDate.split("_")
            dia2 = partes2[0]
            mes2 = partes2[1]
            anio2 = partes2[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3
            fDate = dia2 + "/" + mes2 + "/" + anio2

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date = datetime.date(int(anio2), int(mes2), int(dia2))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))
            start_date_second_biweekly = end_date_biweekly + timedelta(days=1)

            diaStartSecondBiweekly = start_date_second_biweekly.day
            mesStartSecondBiweekly = start_date_second_biweekly.month
            anioStartSecondBiweekly = start_date_second_biweekly.year
            diaStartSecondBiweeklyString = str(diaStartSecondBiweekly)
            mesStartSecondBiweeklyString = str(mesStartSecondBiweekly)
            if diaStartSecondBiweeklyString.__len__() == 1:
                diaStartSecondBiweeklyString = "0" + diaStartSecondBiweeklyString
            if mesStartSecondBiweeklyString.__len__() == 1:
                mesStartSecondBiweeklyString = "0" + mesStartSecondBiweeklyString

            fBwStartSecondDate = str(diaStartSecondBiweeklyString) + "/" + str(
                mesStartSecondBiweeklyString) + "/" + str(anioStartSecondBiweekly)

            range = 'Consulta: ' + iDate + " al " + fBwDate + " y " + fBwStartSecondDate + " al " + fDate
            r.merge_range('D3:L3', range, title)



        else:
            # Sería el caso de finishBiweeklyDate and not finishDate (solo quincena)
            print("solo quincena")
            partes1 = initialDate.split("_")
            dia1 = partes1[0]
            mes1 = partes1[1]
            anio1 = partes1[2]
            partes3 = finishBiweeklyDate.split("_")
            dia3 = partes3[0]
            mes3 = partes3[1]
            anio3 = partes3[2]

            iDate = dia1 + "/" + mes1 + "/" + anio1
            fBwDate = dia3 + "/" + mes3 + "/" + anio3

            start_date = datetime.date(int(anio1), int(mes1), int(dia1))
            end_date_biweekly = datetime.date(int(anio3), int(mes3), int(dia3))

            range = 'Consulta: ' + iDate + " al " + fBwDate
            r.merge_range('D3:L3', range, title)

            end_date = end_date_biweekly

            # Fin de solo quincena

        tasks_de_building = building.tasks.all()
        tasks_objetos = []
        for t in tasks_de_building:
            if t.code.lower() == "ll":
                tasks_objetos.append(t)

        workers_de_building = building.workers.all()
        workers_objetos = []
        for w1 in workers_de_building:
            workers_objetos.append(w1)

        print('antes del for consulta de logs')
        day_ini = start_date
        while day_ini <= end_date:
            dia = day_ini.day
            mes = day_ini.month
            anio = day_ini.year
            wdd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wdd:")
            print(wdd)

            datedd = datetime.datetime.strptime(wdd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=datedd)
            except Workday.DoesNotExist:
                workday = None

            logs = LogHour.objects.filter(workday=workday)
            for log in logs:
                if log.worker not in workers_objetos:
                    workers_objetos.append(log.worker)
                if log.task not in tasks_objetos:
                    if log.task.code.lower() == "ll":
                        tasks_objetos.append(log.task)

            day_ini = day_ini + timedelta(days=1)
        print('despues del for consulta de logs')

        # Se cargan los días del rango seleccionado
        day = start_date
        col = 20
        indice = 20
        sinHoras = ""
        colFinPrimeraQuincena = 20
        diccionarioPrimeraQuincena = {}
        diccionarioSegundaQuincena = {}
        esPrimeraQuincena = True

        logs_principal = {}

        while day <= end_date:
            print("***NUEVO DÍA***")
            # print(day)

            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(day.day), header_center)

            day_aux = day + timedelta(days=1)
            if day.month < day_aux.month or day == end_date:
                print("entro en if de cambio de mes")
                letterMonthStart = utils.column_letter(indice)
                letterMonthEnd = utils.column_letter(col)
                month = utils.traducir_mes(day.month)
                r.merge_range('%s4:%s4' % (letterMonthStart, letterMonthEnd), month + " - " + str(day.year),
                              header_center)
                indice = col + 1

            # print("algo por ahí")
            dia = day.day
            mes = day.month
            anio = day.year
            wd = str(anio) + "-" + str(mes) + "-" + str(dia)
            print("wd:")
            print(wd)

            # print("antes")
            date = datetime.datetime.strptime(wd, "%Y-%m-%d").date()
            # Try catch por si no devuelve nada la consulta
            try:
                workday = Workday.objects.get(building=building, date=date)
            except Workday.DoesNotExist:
                workday = None
            if workday == None:
                print("No trajo fecha la consulta")

                # Se cargan logs de los trabajadores
                row = 6
                for worker in workers_objetos:
                    # print("Entro a for de los workers sin workday")
                    r.write('%s%d' % (letter, row), sinHoras)
                    row += 1
            else:
                print("workday no es vacío")

                for tarea in tasks_objetos:
                    try:
                        logs = LogHour.objects.filter(workday=workday, task=tarea)
                    except LogHour.DoesNotExist:
                        logs = None

                    # print("despues de ir a buscar los logs")

                    if logs:
                        arreglo = []
                        for log in logs:
                            # print("for de logs")
                            tupla = (letter, log.worker, log.amount)
                            arreglo.append(tupla)

                        if tarea.code in logs_principal:
                            # print("entra al if tarea code")
                            for tup in arreglo:
                                arr = logs_principal[tarea.code]
                                arr.append(tup)
                                logs_principal[tarea.code] = arr
                        else:
                            logs_principal.update({tarea.code: arreglo})

            if day == end_date_biweekly:
                colFinPrimeraQuincena = col
                # esPrimeraQuincena = False

            day = day + timedelta(days=1)
            col += 1

        # Se obtiene letra de columna de fin de primera quincena
        letterBikeekyEnd = utils.column_letter(colFinPrimeraQuincena)
        print("letterBikeekyEnd: " + letterBikeekyEnd)

        # Se obtiene letra de columna de comienzo de segunda quincena
        if esConsultaDosQuincenas:
            letterSecondBikeekyStart = utils.column_letter(colFinPrimeraQuincena + 1)
            print("letterSecondBikeekyStart: " + letterSecondBikeekyStart)

        print("LOGS PRINCIPAL******************")
        print("")

        class ColumnaMonto():
            def __init__(self, col, monto):
                self.col = col
                self.monto = monto

            # def __str__(self):
            #     return '%s - %s' % (self.code, self.name)

        class WorkerAux():
            wkr = Worker()
            lista_columna_monto = []

            def __init__(self, wkr, lista):
                self.wkr = wkr
                self.lista_columna_monto = lista

            # def __str__(self):
            #     return '%s' % self.code

        # Se ordenan alfabéticamente las tareas de logs_principal
        logs_principal_ord = dict(sorted(logs_principal.items()))

        fila = 6
        letterEnd = utils.column_letter(col - 1)
        # tar es el codigo de tarea
        for tar in logs_principal_ord:

            if tar == 'D11':
                print("es D11")

            print(tar + ": " + str(logs_principal_ord[tar]))

            arreglo_de_workers = []
            arreglo_de_tuplas = logs_principal_ord[tar]
            cant = len(logs_principal_ord[tar])

            lista_workers_final = []

            i = 0
            while i < cant:

                objeto = ColumnaMonto(arreglo_de_tuplas[i][0], arreglo_de_tuplas[i][2])

                # i = 0, 1, 2 ...cant-1
                if arreglo_de_tuplas[i][1] not in arreglo_de_workers:
                    wkr_aux = WorkerAux(arreglo_de_tuplas[i][1], [])
                    wkr_aux.lista_columna_monto.append(objeto)

                    lista_workers_final.append(wkr_aux)

                    arreglo_de_workers.append(arreglo_de_tuplas[i][1])

                else:

                    for x in lista_workers_final:
                        if arreglo_de_tuplas[i][1] == x.wkr:
                            x.lista_columna_monto.append(objeto)

                i += 1

            # print("SE IMPRIME LISTA DE WORKERS FINAL DE UNA TAREA (filas de una tarea a imprimir)")
            for w in lista_workers_final:
                # r.write('B%d' % fila, tar, header_center_without_bg)
                r.write('B%d' % fila, w.wkr.code, code_header_center_without_bg)
                r.write('C%d' % fila, w.wkr.full_name(), format_align_left)
                r.write('D%d' % fila, str(w.wkr.category.code), header_center_without_bg)
                r.write_formula('H%d' % fila, '=sum(T%d:%s%d)' % (fila, letterBikeekyEnd, fila),
                                number_format)  # total hours first biweekly
                if esConsultaDosQuincenas:
                    r.write_formula('I%d' % fila,
                                    '=sum(%s%d:%s%d)' % (letterSecondBikeekyStart, fila, letterEnd, fila),
                                    number_format)  # total hours second biweekly
                r.write_formula('J%d' % fila, '=sum(H%d:I%d)' % (fila, fila), number_format)  # total hours

                for nodo in w.lista_columna_monto:
                    r.write('%s%d' % (nodo.col, fila), nodo.monto, number_format)

                fila += 1
                # print(w.wkr.full_name())
                # for celda in w.lista_columna_monto:
                #     print("col: " + celda.col + " - " + "monto: " + str(celda.monto))

            print("")
            print("")

        workbook.close()
        xlsx_data = output.getvalue()

        print("algo 3")
        return xlsx_data







    def __str__(self):
        return str(self.code)


class Workday(models.Model):
    class Meta:
        verbose_name = _('workday')
        verbose_name_plural = _('workdays')

    building = models.ForeignKey(Building, verbose_name=_('Building'))
    date = models.DateField(_('date'), auto_now=False, default=datetime.date.today)
    finished = models.BooleanField(_('finished'), default=False)
    overseer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    comment = models.CharField(_('comment'), null=True, blank=True, max_length=400, default=None)
    force_finished = models.BooleanField(_('force finished'), default=False)
    holiday = models.BooleanField(_('holiday'), default=False)

    def save(self, *args, **kwargs):
        if self.holiday:
            self.finished = True
            self.force_finished = False
        super(Workday, self).save(*args, **kwargs)

    def expected_hours(self):
        day = self.date.weekday()
        if day == 0:
            return config.MONDAY_HOURS
        if day == 1:
            return config.TUESDAY_HOURS
        if day == 2:
            return config.WEDNESDAY_HOURS
        if day == 3:
            return config.THURSDAY_HOURS
        if day == 4:
            return config.FRIDAY_HOURS
        if day == 5:
            return config.SATURDAY_HOURS
        return config.SUNDAY_HOURS

    @staticmethod
    def additional_half_hour_threshold(day, month, year):
        index = year - constants.START_YEAR
        winter_start, winter_end = constants.WINTER_PERIOD[index]
        winter_start = datetime.datetime.strptime(winter_start, "%Y-%m-%d").date()
        winter_end = datetime.datetime.strptime(winter_end, "%Y-%m-%d").date()
        try:
            today = datetime.date(year, month, day)
            if winter_start <= today <= winter_end:
                return config.WINTER_TIME_THRESHOLD
            else:
                return config.SUMMER_TIME_THRESHOLD
        except ValueError:
            return 25  # threshold is more than hours of day if day doesn't exist.

    @staticmethod
    def calculate_incentive(day, month, year, building, worker):
        try:
            workday = Workday.objects.get(date__day=day, date__month=month, date__year=year, building=building)
            date = workday.date
            if date.isoweekday() == 5:
                monday = date - timezone.timedelta(days=4)
                week_logs = LogHour.objects.filter(workday__date__lte=date, workday__date__gte=monday, worker=worker)
                week_hours = LogHour.sum_hours(week_logs)
                if week_hours >= config.INCENTIVE_THRESHOLD:
                    return float(week_hours) * config.INCENTIVE_PERCENT / 100
            return 0
        except Workday.DoesNotExist:
            return 0

    @staticmethod
    def start(building):
        date = timezone.localdate(timezone.now())
        workdays = Workday.objects.filter(building=building).order_by('-date')
        if workdays and workdays[0].date == date:
            return False
        else:
            workday = Workday(building=building, overseer=building.overseer)
            workday.save()
            return True

    def assign_logs(self, task_id, list_hours_per_user):
        print('assign_logs - 1')
        task = self.building.tasks.get(pk=task_id)
        # if task.requires_comment and comment is None:
        #     s = 0
        #     for x in list_hours_per_user:
        #         s += float(x['amount'])
        #     if s > 0:
        #         return False
        old_task_logs = self.logs.filter(task=task)
        print('assign_logs - 2')
        old_task_logs.delete()
        print('assign_logs - 3')
        logs = LogHour.create_log_hours(self, task, self.building, list_hours_per_user)
        print('assign_logs - 4')
        self.logs.add(*logs)
        return True

    def end(self, comment):
        expected = self.expected_hours()
        if comment is None:  # if comment is None, then day needs to be ended as usual, with controls.
            workers_in_building = Worker.objects.filter(buildings__in=[self.building]).all()
            for worker in workers_in_building:
                worker_logs = self.logs.filter(worker=worker)
                if not LogHour.worker_passes_controls(self, worker_logs):
                    return False
        self.finished = True
        self.comment = comment
        self.force_finished = comment is not None
        self.save()
        return True

    def get_report(self):
        workday = self

        tasks_de_building = workday.building.tasks.all()
        tasks_objetos_sin_orden = []
        for t in tasks_de_building:
            tasks_objetos_sin_orden.append(t)

        tasks_objetos = sorted(tasks_objetos_sin_orden, key=attrgetter('code'))

        workers_de_building = workday.building.workers.all()
        workers_objetos = []
        for w1 in workers_de_building:
            workers_objetos.append(w1)

        logs = LogHour.objects.all().filter(workday=workday)
        for log in logs:
            if log.worker not in workers_objetos:
                workers_objetos.append(log.worker)
            if log.task not in tasks_objetos:
                tasks_objetos.append(log.task)

        amount_of_tasks = len(tasks_objetos)
        max_column = utils.column_letter(3 + amount_of_tasks + 1)


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
            worker.logs = list(workday.logs.filter(worker=worker))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Here we will adding the code to add data
        r = workbook.add_worksheet(__("Daily Report"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        code_header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        code_header.set_num_format(1)
        task_header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})
        number_format = workbook.add_format()
        number_format.set_num_format(2)
        background_color_number = workbook.add_format({'bg_color': '#F5A9BC', 'color': 'black'})
        background_color_number.set_num_format(2)

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'sabyltimetracker/static/images/logo.png', {'x_scale': 0.5, 'y_scale': 0.5})
        r.merge_range('D1:%s1' % max_column, __('Daily Report'), title)
        building_info = '%s: %s' % (__('Building'), str(workday.building))
        r.merge_range('D2:%s2' % max_column, building_info, title)
        date_info = '%s: %s' % (__('Date'), str(workday.date))
        r.merge_range('D3:%s3' % max_column, date_info, title)

        # general headers row
        r.merge_range('A4:D4', __('Workers'), header)

        # specific headers row
        r.write('A5', __('Code'), header)
        r.write('B5', __('Full Name'), header)
        r.write('C5', __('Cat'), header)
        r.write('D5', __('Total'), header)

        col = 5  # starting column is E
        for task in tasks_objetos:
            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(task.code), task_header)

            ancho = 5
            if len(task.code)>ancho:
                ancho = len(task.code) + 0.6

            r.set_column('%s:%s' % (letter, letter), ancho)
            task.column = letter
            col += 1

        notes = {}
        notas_generales = {}

        # cells
        row = 6
        code_width = constants.MIN_WORKER_CODE_WIDTH
        full_name_width = constants.MIN_FULL_NAME_WIDTH
        category_width = constants.MIN_WORKER_CATEGORY_WIDTH
        title_rows_height = constants.MIN_TITLE_ROW_HEIGHT

        columns_no_empty = []
        columns_empty = []
        for worker in workers_ordenados:
            r.write('A%d' % row, worker.code, code_header)
            if len(worker.code) > code_width:
                code_width = len(worker.code)
            r.write('B%d' % row, worker.full_name(), header)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name()) + 5
            r.write('C%d' % row, str(worker.category.code), header)
            if len(str(worker.category.code)) > category_width:
                category_width = len(str(worker.category.code))


            columns_no_empty_aux = []
            suma = 0
            total_tareas_que_no_suman = 0
            for log in worker.logs:
                col = None
                if log.task.whole_day:
                    #se obtienen las horas esperadas para el día workday
                    text = log.workday.expected_hours()

                    # se controla tareas que no suman
                    if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                        if (text == 8):
                            suma = 8
                        else:
                            suma = 9
                    else:
                        if (text == 8):
                            total_tareas_que_no_suman = 8
                        else:
                            total_tareas_que_no_suman = 9
                else:
                    text = log.amount
                    # se controla tareas que no suman
                    if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                        suma = suma + text
                    else:
                        total_tareas_que_no_suman = total_tareas_que_no_suman + text

                for task in tasks_objetos:
                    if task.id == log.task_id:
                        columns_no_empty_aux.append(task.column)
                        col = task.column

                r.write('%s%d' % (col, row), text, number_format)
                if log.comment:
                    comentario = log.comment
                    # if log.task.code not in notes:
                    #     notes[log.task.code] = (log.task, comentario)

                    if log.task.code in constants.TAREAS_VARIOS_TRABAJADORES:
                        if log.task.code not in notas_generales:
                            notas_generales[log.task.code] = (log.task, comentario)
                    else:
                        if worker.code not in notes:
                            notes[worker.code] = worker.code + " - " + worker.full_name() + ": " + comentario
                        else:
                            com = notes[worker.code]
                            com = com + " ** " + comentario
                            notes[worker.code] = com


            for col_no_empty_aux in columns_no_empty_aux:
                if col_no_empty_aux not in columns_no_empty:
                    columns_no_empty.append(col_no_empty_aux)


            horas_del_dia = suma + total_tareas_que_no_suman
            if (horas_del_dia != workday.expected_hours()):
                r.write('D%d' % row, suma, background_color_number)
            else:
                r.write('D%d' % row, suma, number_format)

            row += 1

        # print("********Columnas no vacias")
        # for col_no_empty in columns_no_empty:
        #     print(col_no_empty + " - ")
        #
        for tas in tasks_objetos:
            if tas.column not in columns_no_empty:
                columns_empty.append(tas.column)

        # print("****************************************")
        # print("********Columnas vacias")
        # for col_empty in columns_empty:
        #     print(col_empty + " - ")


        r.set_column('A:A', code_width)
        r.set_column('B:B', full_name_width)
        r.set_column('C:C', category_width)
        r.set_row(0, title_rows_height)
        r.set_row(1, title_rows_height)
        r.set_row(2, title_rows_height)

        r.merge_range('A%d:%s%d' % (row, max_column, row), __('Extra Information'), title)
        row += 1
        if self.force_finished:
            r.merge_range('A%d:%s%d' % (row, max_column, row), __('Day force-finished without controls.'))
            row += 1
        if not self.finished:
            r.merge_range('A%d:%s%d' % (row, max_column, row), __('Day unfinished.'))
            row += 1
        if self.holiday:
            r.merge_range('A%d:%s%d' % (row, max_column, row), __('Day is a holiday.'))
            row += 1
        if self.comment:
            r.merge_range('A%d:C%d' % (row, row), __('Workday comment'), header)
            r.merge_range('D%d:%s%d' % (row, max_column, row), workday.comment)
            row += 1


        if notes or notas_generales:
            r.merge_range('A%d:%s%d' % (row, max_column, row), __('Notes'), header)
            row += 1
            if notes:
                print('Llego a las notas')
                for code in notes:
                    print('Entra al for de notas')
                    # r.merge_range('A%d:C%d' % (row, row), task.name, header)
                    r.merge_range('A%d:%s%d' % (row, max_column, row), notes[code])
                    row += 1
            if notas_generales:
                print('Llego a las notas generales')
                for w_code, (w, comment) in notas_generales.items():
                    print('Entra al for de notas generales')
                    # r.merge_range('A%d:C%d' % (row, row), task.name, header)
                    r.merge_range('A%d:%s%d' % (row, max_column, row), comment)
                    row += 1


        if columns_empty:
            r.merge_range('E4:%s4' % max_column, __('Tasks'), header)
            for letter in columns_empty:
                r.set_column('%s:%s' % (letter, letter), None, None, {'hidden': True})


        workbook.close()
        xlsx_data = output.getvalue()
        return xlsx_data

    def is_editable_by_overseer(self):
        return True
    #    print(timezone.now() - timezone.timedelta(days=config.DAYS_ABLE_TO_EDIT) TODO make real control

    def __str__(self):
        return '%s - %s' % (str(self.date), str(self.building))


class LogHour(models.Model):
    class Meta:
        verbose_name = _('log hour')
        verbose_name_plural = _('log hours')

    workday = models.ForeignKey('Workday', on_delete=models.CASCADE, related_name='logs', verbose_name=_('workday'))
    worker = models.ForeignKey('Worker', verbose_name=_('worker'))
    task = models.ForeignKey('Task', verbose_name=_('task'))
    amount = models.DecimalField(_('amount'), max_digits=3, decimal_places=1, null=False, blank=False, default=1,
                                 validators=[MaxValueValidator(24), MinValueValidator(1)])
    comment = models.CharField(_('comment'), null=True, blank=True, max_length=255, default=None)

    @staticmethod
    def create_log_hours(workday, task, building, list_hours_per_user):
        logs = []
        for item in list_hours_per_user:
            user_id = item.get('user', None)
            user_amount_hours = item.get('amount', 0)
            comment = item.get('comment', None)
            if user_amount_hours > 0:  # no trivial logs
                try:
                    user_amount_hours = round(2*user_amount_hours) / 2
                    try:
                        worker = building.workers.get(pk=user_id)  # only valid if worker works in the correct building
                        logs.append(LogHour(worker=worker, amount=user_amount_hours, task=task, workday=workday, comment=comment))
                    except Worker.DoesNotExist:
                        print('worker no existe. user_id: ' + user_id)
                except Exception:
                    pass
        log_objs = LogHour.objects.bulk_create(logs)
        return log_objs

    # @staticmethod
    # def get_logs_by_tarea_and_building(workday, task, building):
    #     log_objs = LogHour.objects.bulk_create(logs)
    #     return log_objs

    @staticmethod
    def sum_hours(logs):
        # tareas_que_no_suman = ["AS", "CAP", "E", "FOCAP", "LS", "P", "POST", "S", "SA", "LL"];
        if logs:
            sum = 0
            for log in logs:
                if log.task.code not in constants.TAREAS_QUE_NO_SUMAN:
                    if not log.task.is_boolean:
                        sum += log.amount
                    elif log.task.whole_day:
                        sum += log.workday.expected_hours()
            return sum
        else:
            return 0

    @staticmethod
    def worker_passes_controls(workday, logs):
        leq = False
        if logs:
            sum = 0
            for log in logs:
                sum += log.amount
                if log.task.whole_day:
                    return len(logs) == 1
                if log.task.is_boolean:  # tasks that are boolean and not whole day account for some hours of the day.
                    leq = True
            if leq:
                return sum <= workday.expected_hours()
            else:
                return sum == workday.expected_hours()
        else:
            return False

    @staticmethod
    def worker_passes_controls_string(workday, logs):
        # print('Entro en passes controls string')
        if logs:
            sum = 0
            for log in logs:
                sum += log.amount
                if log.task.whole_day:
                    return "igual"

            if sum < workday.expected_hours():
                return "menor"
            elif sum == workday.expected_hours():
                return "igual"
            else:
                return "mayor"
        else:
            return "menor"

    @staticmethod
    def tiene_tarea_especial_todo_el_dia(logs):
        result = False
        if logs:
            for log in logs:
                if log.task.code in constants.TAREAS_ESPECIALES_TODO_EL_DIA:
                    result = True
        return result

    def __str__(self):
        return '%2.1f %s %s %s %s' % (self.amount, _('of'), self.worker, _('in task'), self.task)


class TaskManager(models.Manager):
    # In order to obtain the last building related to the oversee,
    # the queries are always ordered by assigned date.
    def get_queryset(self):
        return super().get_queryset()

    def get_by_building(self, building):
        return self.get_queryset().filter(buildings__in=[building]).all()


class Task(models.Model):
    class Meta:
        verbose_name = _('task')
        verbose_name_plural = _('tasks')

    code = models.CharField(_('code'), null=False, blank=False, max_length=60, unique=True)
    name = models.CharField(_('name'), null=False, blank=True, max_length=255)
    description = models.TextField(_('description'))
    category = models.ForeignKey('TaskCategory', verbose_name=_('Category'))
    requires_comment = models.BooleanField(_('requires comment'), default=False)
    is_boolean = models.BooleanField(_('is boolean'), default=False)
    whole_day = models.BooleanField(_('whole day'), default=False)
    in_monthly_report = models.BooleanField(_('in monthly report'), default=True)

    objects = TaskManager()

    def __str__(self):
        return '%s - %s' % (self.code, self.name)


class TaskCategory(models.Model):
    class Meta:
        verbose_name = _('task category')
        verbose_name_plural = _("task categories")
    name = models.CharField(_('name'), primary_key=True, max_length=60, blank=False)

    def save(self, *args, **kwargs):
        code = '%s-%s' % (self.name, constants.GENERAL_CODE_SUFFIX)
        name = _('%s/General') % self.name
        description = _('General task for the %s category') % self.name
        try:
            task, created = Task.objects.get_or_create(code=code,
                                                       name=name,
                                                       description=description,
                                                       category=self,
                                                       requires_comment=True)
            task.save()
        except IntegrityError:
            pass
        super(TaskCategory, self).save(*args, **kwargs)

    def __str__(self):
        return str(self.name)


class WorkerCategory(models.Model):
    class Meta:
        verbose_name = _('worker category')
        verbose_name_plural = _("worker categories")

    code = models.CharField(_('code'), max_length=10, unique=True)
    name = models.CharField(_('name'), primary_key=True, max_length=40, blank=False)

    def __str__(self):
        return '%s - %s' % (str(self.code), str(self.name))


class Worker(models.Model):
    class Meta:
        verbose_name = _('worker')
        verbose_name_plural = _('workers')

    code = models.CharField(_('code'), primary_key=True, max_length=10)
    first_name = models.CharField(_('first name'), max_length=100)
    last_name = models.CharField(_('last name'), max_length=100)
    category = models.ForeignKey('WorkerCategory', verbose_name=_('Category'))

    def full_name(self):
        return '%s, %s' % (self.last_name, self.first_name)

    # def __str__(self):
    #     return self.full_name()

    def __str__(self):
        return '%s - %s' % (str(self.code), self.full_name())

