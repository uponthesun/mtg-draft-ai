# Generated by Django 2.1.7 on 2019-04-07 20:56

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('drafts', '0002_drafter'),
    ]

    operations = [
        migrations.AddField(
            model_name='drafter',
            name='current_phase',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
        migrations.AddField(
            model_name='drafter',
            name='current_pick',
            field=models.IntegerField(default=0),
            preserve_default=False,
        ),
    ]