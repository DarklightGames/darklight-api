# Generated by Django 2.1.2 on 2018-12-09 08:41

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0016_auto_20181208_2351'),
    ]

    operations = [
        migrations.AlterField(
            model_name='round',
            name='ended_at',
            field=models.DateTimeField(null=True),
        ),
    ]