import uuid
from django.db import models
from django.contrib.postgres.fields import ArrayField
from django.contrib.auth import get_user_model


def get_user():
    return get_user_model()


class StreamType(models.TextChoices):
    VIDEO = "VIDEO", "Video"
    AUDIO = "AUDIO", "Audio"
    SCREEN_RECORD = "SCREEN_RECORD", "Screen Record"


class VisibilityChoices(models.TextChoices):
    PUBLIC = "Public", "Public"
    PRIVATE = "Private", "Private"


class UploadAudioRecord(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    userId = models.IntegerField()
    record_title = models.CharField(max_length=255)
    file = models.FileField(upload_to="uploads/audio/")
    visibility = models.CharField(
        max_length=7,
        choices=VisibilityChoices.choices,
        default=VisibilityChoices.PRIVATE
    )
    description = models.TextField(blank=True, null=True)
    theme = models.ImageField(
        upload_to="uploads/themes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.record_title


class Room(models.Model):
    room_id = models.CharField(max_length=255, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    user_id = models.CharField(max_length=200)
    total_participants = models.IntegerField(null=True, blank=True)
    status = models.CharField(max_length=50, default="active")
    start_timestamp = models.DateTimeField(auto_now_add=True)
    end_timestamp = models.DateTimeField(null=True, blank=True)
    type = models.CharField(max_length=20, choices=StreamType.choices)

class Participant(models.Model):
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="participants")
    user_id = models.CharField(max_length=255)  # External User ID
    username = models.CharField(max_length=255)

class ChatMessage(models.Model):
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="chats")
    user_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

class RecordedAudioStream(models.Model):
    id = models.AutoField(primary_key=True)
    userId = models.IntegerField()
    stream_audio_file = models.FileField(upload_to="stream/audio/")
    recorded_at = models.DateTimeField(auto_now_add=True)

class EventSchedule(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    userId = models.IntegerField()
    startTime = models.CharField(max_length=255)
    startYear = models.CharField(max_length=255)
    endTime = models.CharField(max_length=255)
    endYear = models.CharField(max_length=255)
    category = models.CharField(max_length=255)
    event_title = models.TextField(blank=True, null=True) 
    theme = models.ImageField(upload_to="uploads/themes/", blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.event_title
