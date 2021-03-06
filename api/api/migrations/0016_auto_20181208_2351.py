# Generated by Django 2.1.2 on 2018-12-09 07:51

from django.db import migrations, models


class Migration(migrations.Migration):
    atomic = False

    dependencies = [
        ('api', '0015_rallypoint_round'),
    ]

    operations = [
        migrations.CreateModel(
            name='Session',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('ip', models.GenericIPAddressField()),
                ('started_at', models.DateTimeField()),
                ('ended_at', models.DateTimeField()),
            ],
        ),
        migrations.RenameModel(
            old_name='DamageType',
            new_name='DamageTypeClass',
        ),
        migrations.RemoveField(
            model_name='playersession',
            name='player',
        ),
        migrations.RemoveField(
            model_name='player',
            name='ips',
        ),
        migrations.DeleteModel(
            name='PlayerIP',
        ),
        migrations.DeleteModel(
            name='PlayerSession',
        ),
        migrations.AddField(
            model_name='player',
            name='sessions',
            field=models.ManyToManyField(to='api.Session'),
        ),
    ]
