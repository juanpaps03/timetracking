# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-11-11 19:06
from __future__ import unicode_literals

from django.db import migrations
from tracker.admin import create_defaults

def create_default_data(apps, schema_editor):
    create_defaults()

class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0032_task_in_monthly_report'),
    ]

    operations = [
            migrations.RunPython(create_default_data),
    ]
