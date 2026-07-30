import uuid
from django.db import models
from pgvector.django import VectorField

class ScrapedPage(models.Model):
    url = models.URLField(max_length=500, unique=True, primary_key=True)
    title = models.CharField(max_length=500, blank=True, null=True)
    content = models.TextField()
    scraped_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.title or self.url

class ChatSession(models.Model):
    session_id = models.CharField(max_length=100, unique=True, primary_key=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.session_id

class ChatMessage(models.Model):
    ROLE_CHOICES = [
        ('user', 'User'),
        ('assistant', 'Assistant'),
    ]
    session = models.ForeignKey(ChatSession, related_name='messages', on_delete=models.CASCADE)
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    content = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['created_at']

    def __str__(self):
        return f"{self.role}: {self.content[:50]}"

class PageChunk(models.Model):
    page = models.ForeignKey(ScrapedPage, related_name='chunks', on_delete=models.CASCADE)
    chunk_text = models.TextField()
    embedding = VectorField(dimensions=1536, null=True, blank=True)

    def __str__(self):
        return f"Chunk of {self.page.title or self.page.url}: {self.chunk_text[:30]}..."


class ChatUser(models.Model):
    user_id = models.CharField(max_length=100, primary_key=True, default=uuid.uuid4)
    name = models.CharField(max_length=255, null=True, blank=True)
    email = models.EmailField(max_length=255, null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return self.name or f"Guest ({self.user_id})"


class UserChatSession(models.Model):
    session_id = models.CharField(max_length=100, primary_key=True)
    user = models.ForeignKey(ChatUser, on_delete=models.CASCADE, db_column='user_id', null=True, blank=True, related_name='sessions')
    chat_details = models.JSONField(default=list)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self):
        return f"Session {self.session_id} - User {self.user_id if self.user else 'None'}"


