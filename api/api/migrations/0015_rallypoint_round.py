# Generated by Django 2.1.2 on 2018-11-20 09:54

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('api', '0014_auto_20181120_0151'),
    ]

    operations = [
        migrations.AddField(
            model_name='rallypoint',
            name='round',
            field=models.ForeignKey(default=None, on_delete=django.db.models.deletion.CASCADE, to='api.Round'),
            preserve_default=False,
        ),
    ]