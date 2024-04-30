# Generated by Django 5.0.2 on 2024-04-30 08:15

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_denuncia_resposta'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='denuncia',
            name='evidencias',
        ),
        migrations.CreateModel(
            name='Evidencia',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('imagem', models.ImageField(upload_to='denuncia_images')),
                ('denuncias', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='evidencias_set', to='core.denuncia')),
            ],
        ),
        migrations.AddField(
            model_name='denuncia',
            name='evidencias',
            field=models.ManyToManyField(blank=True, to='core.evidencia'),
        ),
    ]
