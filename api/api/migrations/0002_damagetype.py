# Generated by Django 2.1.2 on 2018-11-01 01:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0001_initial'),
    ]

    operations = [
        migrations.CreateModel(
            name='DamageType',
            fields=[
                ('id', models.CharField(max_length=128, primary_key=True, serialize=False)),
            ],
        ),
    ]
