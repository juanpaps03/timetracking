# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-10-03 15:54
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0029_auto_20181002_1715'),
    ]

    operations = [
        migrations.AddField(
            model_name='task',
            name='is_boolean',
            field=models.BooleanField(default=False),
        ),
    ]
