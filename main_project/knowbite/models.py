from django.db import models
from django.contrib.auth.models import User
import os
# Create your models here.
from django.db import models
import os

class UploadedFile(models.Model):
    FILE_TYPES = [
        ('pdf', 'PDF'),
        ('audio', 'Audio'),
        ('youtube', 'YouTube'),
    ]
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.FileField(upload_to='uploads/', blank=True, null=True)
    file_type = models.CharField(max_length=10, choices=FILE_TYPES)
    youtube_link = models.URLField(blank=True, null=True)
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.file_type == 'youtube':
            return f"YouTube: {self.youtube_link}"
        return os.path.basename(self.file.name) if self.file else "No file"

    def filename(self):
        if self.file_type == 'youtube':
            return self.youtube_link
        return os.path.basename(self.file.name) if self.file else None

    def save(self, *args, **kwargs):
        # Validate file type consistency
        if self.file_type == 'youtube' and not self.youtube_link:
            raise ValueError("YouTube links require a youtube_link")
        if self.file_type != 'youtube' and not self.file:
            raise ValueError("Non-YouTube uploads require a file")
        super().save(*args, **kwargs)

class Summary(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    summary_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Summary for {self.uploaded_file.filename()} by {self.user.username}"

class ExtractedText(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    uploaded_file = models.OneToOneField(UploadedFile, on_delete=models.CASCADE)
    extracted_text = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"Extracted text for {self.uploaded_file.filename()} by {self.user.username}"

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


class Plan(models.Model):
    PLAN_CHOICES = [
        ('basic', 'Basic'),
        ('pro', 'Pro'),
    ]
    BILLING_CHOICES = [
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]
    name = models.CharField(max_length=20, choices=PLAN_CHOICES)
    billing_period = models.CharField(max_length=10, choices=BILLING_CHOICES, default='monthly')
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    paddle_plan_id = models.CharField(max_length=100, unique=True)  # Paddle plan/product ID

    # Limits
    pdf_uploads_per_month = models.IntegerField()
    pdf_max_size_mb = models.IntegerField()
    pdf_max_pages = models.IntegerField()
    audio_uploads_per_month = models.IntegerField()
    audio_max_size_mb = models.IntegerField()
    audio_max_length_min = models.IntegerField()
    youtube_links_per_month = models.IntegerField()
    youtube_max_length_min = models.IntegerField()
    quizzes_per_month = models.IntegerField()
    summary_regenerations_per_file = models.IntegerField()
    chatbot_messages_per_file = models.IntegerField()

    class Meta:
        unique_together = (('name', 'billing_period'),)

    def __str__(self):
        return self.get_name_display()

class UserSubscription(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    is_active = models.BooleanField(default=False)
    current_period_end = models.DateTimeField(null=True, blank=True)
    paddle_subscription_id = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'No Plan'}"