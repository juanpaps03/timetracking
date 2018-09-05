from django.utils import timezone
from config import constants

from django.db import models

from sabyltimetracker.users.models import User


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

    def __str__(self):
        return str(self.code)


class Workday(models.Model):
    building = models.ForeignKey(Building)
    date = models.DateField(auto_now=False, auto_now_add=True)
    finished = models.BooleanField(default=False)
    logs = models.ManyToManyField('LogHour', blank=True)
    overseer = models.ForeignKey(User, on_delete=models.SET_NULL, blank=True, null=True)

    @staticmethod
    def expected_hours():
        return constants.EXPECTED_HOURS[timezone.now().date().weekday()]

    def assign_logs(self, task_id, list_hours_per_user):
        task = self.building.tasks.get(pk=task_id)
        old_task_logs = self.logs.filter(task=task)
        old_task_logs.delete()
        logs = LogHour.create_log_hours(task, self.building, list_hours_per_user)
        self.logs.add(*logs)

    def end(self):
        expected = Workday.expected_hours()
        workers_in_building = User.objects.filter(buildings__in=[self.building]).all()
        for worker in workers_in_building:
            worker_logs = self.logs.filter(user=worker)
            if LogHour.sum_hours(worker_logs) < expected:
                return False
        self.finished = True
        self.save()
        return True

    def __str__(self):
        return '%s - %s' % (str(self.date), str(self.building))


class LogHour(models.Model):
    amount = models.PositiveIntegerField(null=False, blank=False, default=0)
    user = models.ForeignKey(User)
    task = models.ForeignKey('Task')

    @staticmethod
    def create_log_hours(task, building, list_hours_per_user):
        logs = []
        for item in list_hours_per_user:
            user_id = item.get('user', None)
            user_amount_hours = item.get('amount', 0)

            if user_amount_hours > 0:
                try:
                    worker = building.workers.get(pk=user_id)
                    logs.append(LogHour(user=worker, amount=user_amount_hours, task=task))
                except Exception:
                    pass

        log_objs = LogHour.objects.bulk_create(logs)
        return log_objs

    @staticmethod
    def sum_hours(logs):
        if logs:
            sum = 0
            for log in logs:
                sum += log.amount
            return sum
        else:
            return 0

    def __str__(self):
        return '%d of user %s in task %s' % (self.amount, self.user, self.task)


class TaskManager(models.Manager):
    # In order to obtain the last building related to the oversee,
    # the queries are always ordered by assigned date.
    def get_queryset(self):
        return super().get_queryset()

    def get_by_building(self, building):
        return self.get_queryset().filter(buildings__in=[building]).all()


class Task(models.Model):
    code = models.CharField(null=False, blank=False, max_length=20)
    name = models.CharField(null=False, blank=True, max_length=255)
    description = models.TextField()
    parent_task = models.ForeignKey('self', blank=True, null=True, related_name='task_relationship')

    objects = TaskManager()

    def __str__(self):
        return '%s - %s' % (self.code, self.name)
