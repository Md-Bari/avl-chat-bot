from django.db import models

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
    embedding_json = models.TextField()  # Stores float array as JSON string

    def __str__(self):
        return f"Chunk of {self.page.title or self.page.url}: {self.chunk_text[:30]}..."

