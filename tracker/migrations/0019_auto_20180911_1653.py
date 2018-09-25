# -*- coding: utf-8 -*-
# Generated by Django 1.11.9 on 2018-09-11 16:53
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tracker', '0018_auto_20180907_1455'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loghour',
            name='amount',
            field=models.PositiveIntegerField(default=1, validators=[django.core.validators.MaxValueValidator(24), django.core.validators.MinValueValidator(1)]),
        ),
    ]
