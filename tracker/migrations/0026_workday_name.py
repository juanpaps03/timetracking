# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-10-01 20:35
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0025_auto_20180928_1029'),
    ]

    operations = [
        migrations.AddField(
            model_name='workday',
            name='name',
            field=models.CharField(blank=True, default=None, max_length=400, null=True),
        ),
    ]
