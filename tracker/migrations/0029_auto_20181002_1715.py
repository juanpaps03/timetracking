# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-10-02 20:15
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0028_workday_holiday'),
    ]

    operations = [
        migrations.AddField(
            model_name='loghour',
            name='comment',
            field=models.CharField(blank=True, default=None, max_length=255, null=True),
        ),
        migrations.AddField(
            model_name='task',
            name='requires_comment',
            field=models.BooleanField(default=False),
        ),
    ]
