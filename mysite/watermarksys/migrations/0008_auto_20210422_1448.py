# Generated by Django 3.2 on 2021-04-22 06:48

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('watermarksys', '0007_auto_20210419_1132'),
    ]

    operations = [
        migrations.AlterField(
            model_name='cost',
            name='phone',
            field=models.CharField(max_length=11),
        ),
        migrations.AlterField(
            model_name='userinformation',
            name='phone',
            field=models.CharField(max_length=11, unique=True),
        ),
        migrations.AlterField(
            model_name='users',
            name='phone',
            field=models.CharField(max_length=11, unique=True),
        ),
        migrations.AlterField(
            model_name='watermark',
            name='phone',
            field=models.CharField(max_length=11),
        ),
    ]
