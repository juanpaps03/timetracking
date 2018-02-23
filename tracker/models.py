from django.utils import timezone

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
    direction = models.CharField(blank=True, max_length=255)
    overseer = models.ForeignKey(User)
    workers = models.ManyToManyField(User, related_name="workers_in_building")
    tasks = models.ManyToManyField('Task', related_name="enabled_tasks")
    assigned = models.DateTimeField(auto_now=False, auto_now_add=True)

    objects = BuildingManager()

    # If the oversee is modified, assigned date is update.
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

    def assign_logs(self, task_id, list_hours_per_user):
        task = self.building.tasks.get(pk=task_id)
        logs = LogHour.create_log_hours(task, self.building, list_hours_per_user)
        self.logs.add(*logs)

    def __str__(self):
        return str(self.date)


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

    def __str__(self):
        return '%d of user %s in task %s' % (self.amount, self.user, self.task)


class Task(models.Model):
    code = models.CharField(null=False, blank=False, max_length=20)
    name = models.CharField(null=False, blank=True, max_length=255)
    description = models.TextField()
    parent_task = models.ForeignKey('self', blank=True, null=True, related_name='task_relationship')

    def __str__(self):
        return '%s - %s' % (self.code, self.name)
