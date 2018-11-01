# Generated by Django 2.1.2 on 2018-11-01 05:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0005_auto_20181031_2141'),
    ]

    operations = [
        migrations.CreateModel(
            name='PlayerName',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
            ],
        ),
        migrations.AddField(
            model_name='player',
            name='names',
            field=models.ManyToManyField(to='api.PlayerName'),
        ),
    ]
