# Generated by Django 2.1.2 on 2018-11-01 02:21

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0003_frag'),
    ]

    operations = [
        migrations.CreateModel(
            name='Map',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=128)),
            ],
        ),
        migrations.CreateModel(
            name='Round',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('version', models.CharField(max_length=16)),
                ('frags', models.ManyToManyField(to='api.Frag')),
                ('map', models.ManyToManyField(to='api.Map')),
                ('players', models.ManyToManyField(to='api.Player')),
            ],
        ),
    ]