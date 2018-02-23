# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-02-23 13:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0008_auto_20180223_1342'),
    ]

    operations = [
        migrations.AlterField(
            model_name='building',
            name='assigned',
            field=models.DateTimeField(auto_now_add=True),
        ),
        migrations.AlterField(
            model_name='workday',
            name='logs',
            field=models.ManyToManyField(to='tracker.LogHour'),
        ),
    ]