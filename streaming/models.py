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
    room = models.ForeignKey(Room, on_delete=models.CASCADE, related_name="participants")
    user_id = models.CharField(max_length=255)  # External User ID
    username = models.CharField(max_length=255)

class ChatMessage(models.Model):
    room = models.ForeignKey(
        Room, on_delete=models.CASCADE, related_name="chats")
    user_id = models.CharField(max_length=255)
    username = models.CharField(max_length=255)
    message = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
