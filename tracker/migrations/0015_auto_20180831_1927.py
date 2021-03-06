# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-08-31 19:27
from __future__ import unicode_literals

from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0014_auto_20180831_1926'),
    ]

    operations = [
        migrations.AlterField(
            model_name='building',
            name='overseer',
            field=models.OneToOneField(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, to=settings.AUTH_USER_MODEL),
        ),
        migrations.AlterField(
            model_name='workday',
            name='logs',
            field=models.ManyToManyField(blank=True, to='tracker.LogHour'),
        ),
    ]
