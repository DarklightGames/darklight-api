# Generated by Django 2.1.2 on 2018-12-09 09:19

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0019_auto_20181209_0114'),
    ]

    operations = [
        migrations.AddField(
            model_name='construction',
            name='round',
            field=models.ForeignKey(default=0, on_delete=django.db.models.deletion.CASCADE, to='api.Round'),
            preserve_default=False,
        ),
    ]
