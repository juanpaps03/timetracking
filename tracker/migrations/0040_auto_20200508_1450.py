# -*- coding: utf-8 -*-
# Generated by Django 1.11.17 on 2020-05-08 17:50
from __future__ import unicode_literals

import django.core.validators
from django.db import migrations, models


class Migration(migrations.Migration):

    # dependencies = [
    #     ('tracker', '0039_auto_20190122_1321'),
    # ]

    dependencies = [
        ('tracker', '0038_workercategory_code'),
    ]

    operations = [
        migrations.AlterField(
            model_name='loghour',
            name='amount',
            field=models.DecimalField(decimal_places=1, default=1, max_digits=3, validators=[django.core.validators.MaxValueValidator(24), django.core.validators.MinValueValidator(1)], verbose_name='amount'),
        ),
    ]