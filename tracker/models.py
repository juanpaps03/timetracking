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
    workers = models.ManyToManyField(User, related_name="buildings")
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
        try:
            workdays = Workday.objects.filter(date__year=year, date__month=month, building=building)
            logs = LogHour.objects.filter(workday__in=workdays)
            for worker in workers:
                worker.logs = logs.filter(user=worker)
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
        r.set_column('D:D', 3)
        r.merge_range('E4:E5', _('Holiday'), header)
        r.set_column('E:E', 2)
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
        r.merge_range('AQ4:AR4', _('1/2 Hour Ad'), header)
        r.write('AQ5', _(u'1ºQ'), header)
        r.write('AR5', _(u'2ºQ'), header)

        # cells
        username_width = 4
        full_name_width = 15

        # username column
        row = 5
        for worker in workers:
            r.write(row, 0, worker.username, header)
            r.write(row, 1, worker.full_name(), header)
            r.write_formula(row, 5, '=sum(L%s:Z%s)' % (row+1, row+1)) # 1ºQ hours
            r.write_formula(row, 6, '=sum(AA%s:AP%s)' % (row+1, row+1)) # 2ºQ hours
            r.write_formula(row, 7, '=sum(F%s:G%s)' % (row+1, row+1)) # total hours
            r.write_formula(row, 10, '=sum(I%s:J%s)' % (row+1, row+1)) # total incentive

            if len(worker.username) > username_width:
                username_width = len(worker.username)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name())
            for day in range(1, 32):
                hours = LogHour.sum_hours(worker.logs.filter(workday__date__day=day))
                r.write(row, 10+day, hours)
            row += 1

        r.set_column('A:A', username_width)
        r.set_column('B:B', full_name_width)

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

    @staticmethod
    def expected_hours():
        return constants.EXPECTED_HOURS[timezone.now().date().weekday()]

    def assign_logs(self, task_id, list_hours_per_user):
        task = self.building.tasks.get(pk=task_id)
        old_task_logs = self.logs.filter(task=task)
        old_task_logs.delete()
        logs = LogHour.create_log_hours(self, task, self.building, list_hours_per_user)
        self.logs.add(*logs)

    def end(self):
        expected = Workday.expected_hours()
        workers_in_building = User.objects.filter(buildings__in=[self.building]).all()
        for worker in workers_in_building:
            worker_logs = self.logs.filter(user=worker)
            if not LogHour.worker_passes_controls(self, worker_logs):
                return False
        self.finished = True
        self.save()
        return True

    def get_report(self):
        workday = self
        tasks = workday.building.tasks.all()
        amount_of_tasks = len(tasks)
        max_column = utils.column_letter(3 + amount_of_tasks)
        workers = workday.building.workers.all()
        for worker in workers:
            worker.logs = list(workday.logs.filter(user=worker))

        output = io.BytesIO()
        workbook = xlsxwriter.Workbook(output)

        # Here we will adding the code to add data
        r = workbook.add_worksheet(_("Daily Report"))
        title = workbook.add_format({ 'bold': True, 'font_size': 14, 'align': 'center' })
        header = workbook.add_format({ 'bg_color': '#F7F7F7', 'color': 'black', 'align': 'center', 'border': 1 })

        # title row

        r.merge_range('A1:C3', _('COMPANY NAME'), title)
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
        r.write(4, 0, _('Code'), header)
        r.write(4, 1, _('Full Name'), header)
        r.write(4, 2, _('Cat'), header)
        r.set_column('C:C', 3)

        col = 3  # starting column is 3
        for task in tasks:
            r.write(4, col, str(task.name), header)
            letter = chr(ord('A') + col)
            r.set_column('%s:%s' % (letter, letter), len(task.name))
            task.column = col
            col += 1

        # cells
        row = 5
        username_width = 4
        full_name_width = 15
        for worker in workers:
            r.write(row, 0, worker.username, header)
            if len(worker.username) > username_width:
                username_width = len(worker.username)
            r.write(row, 1, worker.full_name(), header)
            if len(worker.full_name()) > full_name_width:
                full_name_width = len(worker.full_name())
            for log in worker.logs:
                col = 0
                for task in tasks:
                    if task.id == log.task_id:
                        col = task.column
                r.write(row, col, log.amount)
            row += 1
        r.set_column('A:A', username_width)
        r.set_column('B:B', full_name_width)

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
    user = models.ForeignKey(User)
    task = models.ForeignKey('Task')
    amount = models.PositiveIntegerField(null=False, blank=False, default=1,
                                         validators=[MaxValueValidator(24), MinValueValidator(1)])

    @staticmethod
    def create_log_hours(workday, task, building, list_hours_per_user):
        logs = []
        for item in list_hours_per_user:
            user_id = item.get('user', None)
            user_amount_hours = item.get('amount', 0)

            if user_amount_hours > 0:  # no trivial logs
                try:
                    worker = building.workers.get(pk=user_id)  # only valid if worker works in the correct building
                    logs.append(LogHour(user=worker, amount=user_amount_hours, task=task, workday=workday))
                except Exception:
                    pass

        log_objs = LogHour.objects.bulk_create(logs)
        return log_objs

    @staticmethod
    def sum_hours(logs):
        if logs:
            sum = 0
            for log in logs:
                if log.task.code != constants.ABSENCE_CODE:
                    sum += log.amount
            return sum
        else:
            return 0

    @staticmethod
    def worker_passes_controls(workday, logs):
        if logs:
            sum = 0
            for log in logs:
                sum += log.amount
                if log.task.code == constants.ABSENCE_CODE:
                    return True
            return sum == workday.expected_hours()
        else:
            return False

    def __str__(self):
        return '%d %s %s %s %s' % (self.amount, _('of'), self.user, _('in task'), self.task)


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
    parent_task = models.ForeignKey('self', blank=True, null=True, related_name='task_relationship')

    objects = TaskManager()

    def __str__(self):
        return '%s - %s' % (self.code, self.name)
