import datetime
import io

import xlsxwriter
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext as _

from config import constants
from sabyltimetracker.users.models import User
from tracker import utils
from django.utils.dateparse import parse_datetime


class BuildingManager(models.Manager):
    # In order to obtain the last building related to the oversee,
    # the queries are always ordered by assigned date.
    def get_queryset(self):
        return super().get_queryset().order_by('-assigned')

    def get_by_overseer(self, user):
        return self.get_queryset().filter(overseer=user).first()


class Building(models.Model):
    code = models.PositiveIntegerField(null=False, blank=False)
    address = models.CharField(blank=True, max_length=255)
    overseer = models.OneToOneField(User, on_delete=models.SET_NULL, null=True, blank=True)
    workers = models.ManyToManyField('Worker', related_name="buildings")
    tasks = models.ManyToManyField('Task', related_name="buildings")
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

    def get_report(self, month, year):
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
        r = workbook.add_worksheet(_("Daily Report"))
        title = workbook.add_format({ 'bold': True, 'font_size': 14, 'align': 'center' })
        header = workbook.add_format({ 'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1 })

        # title row
        r.merge_range('A1:C3', _('COMPANY NAME'), title)
        r.insert_image('A1', 'static:images:logo.png')
        r.merge_range('D1:AR1', _('Worked Hours Detail'), title)
        building_info = '%s: %s' % (_('Building'), str(self))
        r.merge_range('D2:AR2', building_info, title)
        date_info = '%s: %s, %s: %s' % (_('Month'), str(month), _('Year'), str(year))
        r.merge_range('D3:AR3', date_info, title)

        # headers row
        r.merge_range('A4:A5', _('Code'), header)
        r.merge_range('B4:B5', _('Full Name'), header)
        r.merge_range('C4:C5', _('VL'), header)
        r.set_column('C:C', 2)
        r.merge_range('D4:D5', _('Cat'), header)
        r.merge_range('E4:E5', _('Holiday'), header)
        r.set_column('E:E', 7)
        r.merge_range('F4:H4', _('Worked Hours'), header)
        r.write('F5', _(u'1ºQ'), header)
        r.set_column('F:F', 4)
        r.write('G5', _(u'2ºQ'), header)
        r.set_column('G:G', 4)
        r.write('H5', _('Total'), header)
        r.set_column('H:H', 4)
        r.merge_range('I4:K4', _('Incentive Hours'), header)
        r.write('I5', _(u'1ºQ'), header)
        r.set_column('I:I', 4)
        r.write('J5', _(u'2ºQ'), header)
        r.set_column('J:J', 4)
        r.write('K5', _('Total'), header)
        r.set_column('K:K', 4)
        r.merge_range('L4:AP4', _('Days'), header)
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
        r.merge_range('AQ4:AR4', _('Ad 1/2 Hour'), header)
        r.write('AQ5', _(u'1ºQ'), header)
        r.set_column('AQ:AQ', 5)
        r.write('AR5', _(u'2ºQ'), header)
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
            r.write('D%d' % row, str(worker.category), header)
            r.write('E%d' % row, holiday_hours)
            r.write_formula('F%d' % row, '=sum(L%s:Z%s)' % (row, row))  # 1ºQ hours
            r.write_formula('G%d' % row, '=sum(AA%s:AP%s)' % (row, row))  # 2ºQ hours
            r.write_formula('H%d' % row, '=sum(F%s:G%s)' % (row, row))  # total hours
            r.write_formula('K%d' % row, '=sum(I%s:J%s)' % (row, row))  # total incentive

            if len(str(worker.category)) > category_width:
                category_width = len(str(worker.category))
            if len(worker.code) > code_width:
                code_width = len(worker.code)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name())
            first_additional_half_hours = 0
            second_additional_half_hours = 0
            first_incentive_hours = 0
            second_incentive_hours = 0
            for day in range(1, 32):
                hours = LogHour.sum_hours(worker.logs.filter(workday__date__day=day))
                r.write('%s%d' % (utils.column_letter(10 + day), row), hours)
                if hours >= Workday.additional_half_hour_threshold(day, month, year):
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

    def __str__(self):
        return str(self.code)


class Workday(models.Model):
    building = models.ForeignKey(Building)
    date = models.DateField(auto_now=False, default=datetime.date.today)
    finished = models.BooleanField(default=False)
    overseer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)
    comment = models.CharField(null=True, blank=True, max_length=400, default=None)
    force_finished = models.BooleanField(default=False)
    holiday = models.BooleanField(default=False)

    def save(self, *args, **kwargs):
        if self.holiday:
            self.finished = True
            self.force_finished = False
        super(Workday, self).save(*args, **kwargs)

    def expected_hours(self):
        return constants.EXPECTED_HOURS[self.date.weekday()]

    @staticmethod
    def additional_half_hour_threshold(day, month, year):
        index = year - constants.START_YEAR
        winter_start, winter_end = constants.WINTER_PERIOD[index]
        winter_start = datetime.datetime.strptime(winter_start, "%Y-%m-%d").date()
        winter_end = datetime.datetime.strptime(winter_end, "%Y-%m-%d").date()
        today = datetime.date(year, month, day)
        if winter_start <= today <= winter_end:
            return constants.WINTER_TIME_THRESHOLD
        else:
            return constants.SUMMER_TIME_THRESHOLD

    @staticmethod
    def calculate_incentive(day, month, year, building, worker):
        try:
            workday = Workday.objects.get(date__day=day, date__month=month, date__year=year, building=building)
            date = workday.date
            if date.isoweekday() == 5:
                monday = date - timezone.timedelta(days=4)
                week_logs = LogHour.objects.filter(workday__date__lte=date, workday__date__gte=monday, worker=worker)
                week_hours = LogHour.sum_hours(week_logs)
                if week_hours >= constants.INCENTIVE_THRESHOLD:
                    return float(week_hours) * constants.INCENTIVE_PERCENT / 100
            return 0
        except Workday.DoesNotExist:
            return 0

    @staticmethod
    def start(building):
        workday = Workday(building = building, overseer=building.overseer)
        workday.save()

    def assign_logs(self, task_id, list_hours_per_user, comment=None):
        task = self.building.tasks.get(pk=task_id)
        if task.requires_comment and comment is None:  # redundant check, happens in frontend.
            return False
        else:
            old_task_logs = self.logs.filter(task=task)
            old_task_logs.delete()
            logs = LogHour.create_log_hours(self, task, self.building, list_hours_per_user, comment)
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
        tasks = workday.building.tasks.all()
        amount_of_tasks = len(tasks)
        max_column = utils.column_letter(2 + amount_of_tasks)
        workers = workday.building.workers.all()
        for worker in workers:
            worker.logs = list(workday.logs.filter(worker=worker))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Here we will adding the code to add data
        r = workbook.add_worksheet(_("Daily Report"))
        title = workbook.add_format({ 'bold': True, 'font_size': 14, 'align': 'center' })
        header = workbook.add_format({ 'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1 })

        # title row

        r.merge_range('A1:C3', constants.COMPANY_NAME, title)
        r.insert_image('A1', 'static:images:logo.png')
        r.merge_range('D1:%s1' % max_column, _('Daily Report'), title)
        building_info = '%s: %s' % (_('Building'), str(workday.building))
        r.merge_range('D2:%s2' % max_column, building_info, title)
        date_info = '%s: %s' % (_('Date'), str(workday.date))
        r.merge_range('D3:%s3' % max_column, date_info, title)

        # general headers row
        r.merge_range('A4:C4', _('Workers'), header)
        r.merge_range('D4:%s4' % max_column, _('Tasks'), header)

        # specific headers row
        r.write('A5', _('Code'), header)
        r.write('B5', _('Full Name'), header)
        r.write('C5', _('Cat'), header)

        col = 3 # starting column is D
        for task in tasks:
            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(task.name), header)
            r.set_column('%s:%s' % (letter, letter), len(task.name))
            task.column = letter
            col += 1

        notes = {}

        # cells
        row = 6
        code_width = constants.MIN_WORKER_CODE_WIDTH
        full_name_width = constants.MIN_FULL_NAME_WIDTH
        category_width = constants.MIN_WORKER_CATEGORY_WIDTH
        for worker in workers:
            r.write('A%d' % row, worker.code, header)
            if len(worker.code) > code_width:
                code_width = len(worker.code)
            r.write('B%d' % row, worker.full_name(), header)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name())
            r.write('C%d' % row, str(worker.category), header)
            if len(str(worker.category)) > category_width:
                category_width = len(str(worker.category))
            for log in worker.logs:
                col = None
                text = ''
                if log.task.is_boolean:
                    text = log.task.code
                else:
                    text = log.amount
                for task in tasks:
                    if task.id == log.task_id:
                        col = task.column
                r.write('%s%d' % (col, row), text)
                if log.comment:
                    notes[log.task.code] = (log.task, log.comment)

            row += 1
        r.set_column('A:A', code_width)
        r.set_column('B:B', full_name_width)
        r.set_column('C:C', category_width)

        r.merge_range('A%d:%s%d' % (row, max_column, row), _('Extra Information'), title)
        row += 1
        if self.force_finished:
            r.merge_range('A%d:%s%d' % (row, max_column, row), _('Day force-finished without controls.'))
            row += 1
        if not self.finished:
            r.merge_range('A%d:%s%d' % (row, max_column, row), _('Day unfinished.'))
            row += 1
        if self.holiday:
            r.merge_range('A%d:%s%d' % (row, max_column, row), _('Day is a holiday.'))
            row += 1
        if self.comment:
            r.merge_range('A%d:C%d' % (row, row), _('Workday comment'), header)
            r.merge_range('D%d:%s%d' % (row, max_column, row), workday.comment)
            row += 1
        if notes:
            r.merge_range('A%d:%s%d' % (row, max_column, row), _('Notes'), header)
            row += 1
            for code, (task, comment) in notes.items():
                r.merge_range('A%d:C%d' % (row, row), task.name, header)
                r.merge_range('D%d:%s%d' % (row, max_column, row), comment)
                row += 1

        workbook.close()
        xlsx_data = output.getvalue()
        return xlsx_data

    def is_editable_by_overseer(self):
        return True
    #    print(timezone.now() - timezone.timedelta(days=constants.DAYS_ABLE_TO_EDIT) TODO make real control

    def __str__(self):
        return '%s - %s' % (str(self.date), str(self.building))


class LogHour(models.Model):
    workday = models.ForeignKey('Workday', on_delete=models.CASCADE, related_name='logs')
    worker = models.ForeignKey('Worker')
    task = models.ForeignKey('Task')
    amount = models.DecimalField(max_digits=2, decimal_places=1, null=False, blank=False, default=1,
                                 validators=[MaxValueValidator(24), MinValueValidator(1)])
    comment = models.CharField(null=True, blank=True, max_length=255, default=None)

    @staticmethod
    def create_log_hours(workday, task, building, list_hours_per_user, comment=None):
        logs = []
        for item in list_hours_per_user:
            user_id = item.get('user', None)
            user_amount_hours = item.get('amount', 0)

            if user_amount_hours > 0:  # no trivial logs
                try:
                    user_amount_hours = round(2*user_amount_hours) / 2
                    worker = building.workers.get(pk=user_id)  # only valid if worker works in the correct building
                    logs.append(LogHour(worker=worker, amount=user_amount_hours, task=task, workday=workday, comment=comment))
                except Exception:
                    pass

        log_objs = LogHour.objects.bulk_create(logs)
        return log_objs

    @staticmethod
    def sum_hours(logs):
        if logs:
            sum = 0
            for log in logs:
                if not log.task.is_boolean:
                    sum += log.amount
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
    code = models.CharField(null=False, blank=False, max_length=20, unique=True)
    name = models.CharField(null=False, blank=True, max_length=255, unique=True)
    description = models.TextField()
    category = models.ForeignKey('TaskCategory')
    requires_comment = models.BooleanField(default=False)
    is_boolean = models.BooleanField(default=False)
    whole_day = models.BooleanField(default=False)

    objects = TaskManager()

    def __str__(self):
        return '%s - %s' % (self.code, self.name)


class TaskCategory(models.Model):
    class Meta:
        verbose_name_plural = "task categories"
    name = models.CharField(primary_key=True, max_length=40, blank=False)

    def __str__(self):
        return str(self.name)


class WorkerCategory(models.Model):
    class Meta:
        verbose_name_plural = "worker categories"

    name = models.CharField(primary_key=True, max_length=40, blank=False)

    def __str__(self):
        return str(self.name)


class Worker(models.Model):
    code = models.CharField(primary_key=True, max_length=10)
    first_name = models.CharField(max_length=100)
    last_name = models.CharField(max_length=100)
    category = models.ForeignKey('WorkerCategory')

    def full_name(self):
        return '%s, %s' % (self.last_name, self.first_name)

    def __str__(self):
        return self.full_name()
