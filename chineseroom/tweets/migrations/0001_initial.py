# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-08 19:05
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Tweet',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('message', models.TextField(blank=True, null=True)),
                ('user', models.CharField(max_length=255)),
            ],
        ),
    ]
