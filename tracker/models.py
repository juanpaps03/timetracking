import datetime
import io

import xlsxwriter
from django.core.exceptions import ObjectDoesNotExist
from django.core.validators import MinValueValidator, MaxValueValidator
from django.db import models
from django.utils import timezone
from django.utils.translation import ugettext_lazy as _
from django.utils.translation import ugettext as __


from config import constants
from sabyltimetracker.users.models import User
from tracker import utils
from django.db import IntegrityError

from constance import config


class BuildingManager(models.Manager):
    # In order to obtain the last building related to the oversee,
    # the queries are always ordered by assigned date.
    def get_queryset(self):
        return super().get_queryset().order_by('-assigned')

    def get_by_overseer(self, user):
        return self.get_queryset().filter(overseer=user).first()


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
        task = self.building.tasks.get(pk=task_id)
        # if task.requires_comment and comment is None:
        #     s = 0
        #     for x in list_hours_per_user:
        #         s += float(x['amount'])
        #     if s > 0:
        #         return False
        old_task_logs = self.logs.filter(task=task)
        old_task_logs.delete()
        logs = LogHour.create_log_hours(self, task, self.building, list_hours_per_user)
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
        r = workbook.add_worksheet(__("Daily Report"))
        title = workbook.add_format({'bold': True, 'font_size': 14, 'align': 'left'})
        header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'left', 'border': 1})
        task_header = workbook.add_format({'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1})

        # title row
        r.merge_range('A1:C3', config.COMPANY_NAME, title)
        r.insert_image('A1', 'static:images:logo.png')
        r.merge_range('D1:%s1' % max_column, __('Daily Report'), title)
        building_info = '%s: %s' % (__('Building'), str(workday.building))
        r.merge_range('D2:%s2' % max_column, building_info, title)
        date_info = '%s: %s' % (__('Date'), str(workday.date))
        r.merge_range('D3:%s3' % max_column, date_info, title)

        # general headers row
        r.merge_range('A4:C4', __('Workers'), header)
        r.merge_range('D4:%s4' % max_column, __('Tasks'), header)

        # specific headers row
        r.write('A5', __('Code'), header)
        r.write('B5', __('Full Name'), header)
        r.write('C5', __('Cat'), header)

        col = 3  # starting column is D
        for task in tasks:
            letter = utils.column_letter(col)
            r.write('%s5' % letter, str(task.code), task_header)
            r.set_column('%s:%s' % (letter, letter), len(task.code)+0.6)
            task.column = letter
            col += 1

        notes = {}

        # cells
        row = 6
        code_width = constants.MIN_WORKER_CODE_WIDTH
        full_name_width = constants.MIN_FULL_NAME_WIDTH
        category_width = constants.MIN_WORKER_CATEGORY_WIDTH
        title_rows_height = constants.MIN_TITLE_ROW_HEIGHT
        for worker in workers:
            r.write('A%d' % row, worker.code, header)
            if len(worker.code) > code_width:
                code_width = len(worker.code)
            r.write('B%d' % row, worker.full_name(), header)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name()) + 5
            r.write('C%d' % row, str(worker.category.code), header)
            if len(str(worker.category.code)) > category_width:
                category_width = len(str(worker.category.code))
            for log in worker.logs:
                col = None
                text = ''
                if log.task.whole_day:
                    text = log.workday.expected_hours()
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
        if notes:
            r.merge_range('A%d:%s%d' % (row, max_column, row), __('Notes'), header)
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
    amount = models.DecimalField(_('amount'), max_digits=2, decimal_places=1, null=False, blank=False, default=1,
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

    def __str__(self):
        return self.full_name()
