# Generated by Django 5.1.6 on 2025-03-19 11:26

import django.db.models.deletion
import uuid
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='RecordedAudioStream',
            fields=[
                ('id', models.AutoField(primary_key=True, serialize=False)),
                ('userId', models.IntegerField()),
                ('stream_audio_file', models.FileField(upload_to='stream/audio/')),
                ('recorded_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Room',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('room_id', models.CharField(max_length=255, unique=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('user_id', models.CharField(max_length=200)),
                ('total_participants', models.IntegerField(blank=True, null=True)),
                ('status', models.CharField(default='active', max_length=50)),
                ('start_timestamp', models.DateTimeField(auto_now_add=True)),
                ('end_timestamp', models.DateTimeField(blank=True, null=True)),
                ('type', models.CharField(choices=[('VIDEO', 'Video'), ('AUDIO', 'Audio'), ('SCREEN_RECORD', 'Screen Record')], max_length=20)),
            ],
        ),
        migrations.CreateModel(
            name='UploadAudioRecord',
            fields=[
                ('id', models.UUIDField(default=uuid.uuid4, editable=False, primary_key=True, serialize=False)),
                ('userId', models.IntegerField()),
                ('record_title', models.CharField(max_length=255)),
                ('file', models.FileField(upload_to='uploads/audio/')),
                ('visibility', models.CharField(choices=[('Public', 'Public'), ('Private', 'Private')], default='Private', max_length=7)),
                ('description', models.TextField(blank=True, null=True)),
                ('theme', models.ImageField(blank=True, null=True, upload_to='uploads/themes/')),
                ('created_at', models.DateTimeField(auto_now_add=True)),
            ],
        ),
        migrations.CreateModel(
            name='Participant',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=255)),
                ('username', models.CharField(max_length=255)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='participants', to='apps.room')),
            ],
        ),
        migrations.CreateModel(
            name='ChatMessage',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('user_id', models.CharField(max_length=255)),
                ('username', models.CharField(max_length=255)),
                ('message', models.TextField()),
                ('timestamp', models.DateTimeField(auto_now_add=True)),
                ('room', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='chats', to='apps.room')),
            ],
        ),
    ]
