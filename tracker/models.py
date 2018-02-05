import datetime

from django.db import models

from sabyltimetracker.users.models import User


class Building(models.Model):
    code = models.PositiveIntegerField(null=False, blank=False)
    direction = models.CharField(blank=True, max_length=255)
    overseer = models.ForeignKey(User)
    workers = models.ManyToManyField(User, related_name="workers_in_building")
    tasks = models.ManyToManyField('Task', related_name="enabled_tasks")

    def __str__(self):
        return str(self.code)


class Workday(models.Model):
    date = models.DateField(auto_now=False, auto_now_add=True)
    finished = models.BooleanField(default=False)
    logs = models.ManyToManyField('Loghour')

    def __str__(self):
        return self.date


class Loghour(models.Model):
    amount = models.PositiveIntegerField(null=False, blank=False, default=0)
    user = models.ForeignKey(User)
    task = models.ForeignKey('Task')

    def __str__(self):
        return '%d of user %s in task %s' % (self.amount, self.user, self.task)


class Task(models.Model):
    code = models.CharField(null=False, blank=False, max_length=20)
    name = models.CharField(null=False, blank=True, max_length=255)
    description = models.TextField()
    parent_task = models.ForeignKey('self', blank=True, null=True, related_name='task_relationship')

    def __str__(self):
        return '%s - %s' % (self.code, self.name)
