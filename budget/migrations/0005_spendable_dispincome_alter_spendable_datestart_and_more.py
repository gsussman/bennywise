# Generated by Django 4.0.1 on 2022-02-25 04:03

import datetime
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('budget', '0004_alter_transaction_date_spendable_dailyresult'),
    ]

    operations = [
        migrations.AddField(
            model_name='spendable',
            name='dispincome',
            field=models.DecimalField(blank=True, decimal_places=2, max_digits=20, null=True),
        ),
        migrations.AlterField(
            model_name='spendable',
            name='datestart',
            field=models.DateTimeField(default=datetime.datetime(2022, 2, 25, 4, 3, 24, 416612)),
        ),
        migrations.AlterField(
            model_name='transaction',
            name='date',
            field=models.DateTimeField(default=datetime.datetime(2022, 2, 25, 4, 3, 24, 419540)),
        ),
    ]
