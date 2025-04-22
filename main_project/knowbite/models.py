from django.db import models
from django.contrib.auth.models import User
import os
# Create your models here.
class UploadedFile(models.Model):
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('audio', 'Audio'),
        ('video', 'Video'),
        ('youtube', 'YouTube'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/', blank=True, null=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    youtube_link = models.URLField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.file.name if self.file else self.youtube_link

    def filename(self):
        return os.path.basename(self.file.name)

class Summary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    summary_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary for {self.uploaded_file.file.name} by {self.user.username}"
  
class ExtractedText(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    extracted_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extracted text for {self.uploaded_file.file.name} by {self.user.username}"

class ChatMessage(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.ForeignKey('UploadedFile', on_delete=models.CASCADE)
    role = models.CharField(max_length=10, choices=[('user', 'User'), ('bot', 'Bot')])
    content = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['timestamp'] # Order by timestamp by default

    def __str__(self):
        return f'{self.role.capitalize()}: {self.content[:50]}...'