from django.db import models
from django.contrib.auth.models import User


class ChatMessage(models.Model):
    room = models.CharField(max_length=100, db_index=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp']
        indexes = [
            models.Index(fields=['room', 'timestamp']),
        ]

    def __str__(self):
        return f"{self.user.username} в {self.room}: {self.content[:50]}"
