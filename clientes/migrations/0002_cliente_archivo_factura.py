# Generated by Django 5.1.3 on 2024-12-03 14:14

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('clientes', '0001_initial'),
    ]

    operations = [
        migrations.AddField(
            model_name='cliente',
            name='archivo_factura',
            field=models.FileField(blank=True, null=True, upload_to='facturas/', verbose_name='Archivo de Factura'),
        ),
    ]
