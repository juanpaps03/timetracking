# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-09-26 18:42
from __future__ import unicode_literals

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0023_auto_20180926_1502'),
    ]

    operations = [
        migrations.AlterField(
            model_name='task',
            name='category',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='tracker.TaskCategory'),
            preserve_default=False,
        ),
        migrations.AlterField(
            model_name='worker',
            name='category',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='tracker.WorkerCategory'),
            preserve_default=False,
        ),
    ]