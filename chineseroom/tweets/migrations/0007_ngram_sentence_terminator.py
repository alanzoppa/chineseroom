# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-11 21:16
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('tweets', '0006_ngram_sentence_starter'),
    ]

    operations = [
        migrations.AddField(
            model_name='ngram',
            name='sentence_terminator',
            field=models.BooleanField(default=False),
        ),
    ]
