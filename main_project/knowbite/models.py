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
    title = models.CharField(max_length=512, blank=True, null=True)  # New field for YouTube title
    uploaded_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        if self.file_type == 'youtube':
            return f"YouTube: {self.title or self.youtube_link}"
        return os.path.basename(self.file.name) if self.file else "No file"

    def filename(self):
        if self.file_type == 'youtube':
            return self.title or self.youtube_link
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
class Quiz(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    file = models.ForeignKey('UploadedFile', on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.file.filename()} by {self.user.username} Quizzes"
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
        ('free', 'Free'),
        ('basic', 'Basic'),
        ('pro', 'Pro'),
    ]
    BILLING_CHOICES = [
        ('free', 'Free'),
        ('monthly', 'Monthly'),
        ('yearly', 'Yearly'),
    ]    
    name = models.CharField(max_length=20, choices=PLAN_CHOICES)
    billing_period = models.CharField(max_length=10, choices=BILLING_CHOICES, default='monthly')
    is_free = models.BooleanField(default=False)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    description = models.TextField()
    polar_plan_id = models.CharField(max_length=100, unique=True, blank=True, null=True)  # Optional for free plan
    
    @property
    def requires_payment(self):
        """Check if this plan requires payment"""
        return not self.is_free
        
    def save(self, *args, **kwargs):
        # Auto-set billing period for free plan
        if self.name == 'free':
            self.is_free = True
            self.billing_period = 'free'
            self.price = 0
            self.polar_plan_id = None  # Free plans don't require Polar plan IDs
        super().save(*args, **kwargs)

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

    def __str__(self):
        return f"{self.get_name_display()} ({self.get_billing_period_display()})"

class UserSubscription(models.Model):
    STATUS_CHOICES = [
        ('trialing', 'In Trial'),
        ('active', 'Active'),
        ('past_due', 'Past Due'),
        ('paused', 'Paused'),
        ('canceled', 'Canceled')
    ]
    
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    plan = models.ForeignKey(Plan, on_delete=models.SET_NULL, null=True)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='trialing')
    is_active = models.BooleanField(default=True)
    current_period_start = models.DateTimeField(null=True, blank=True)
    current_period_end = models.DateTimeField(null=True, blank=True)
    trial_end = models.DateTimeField(null=True, blank=True)
    polar_subscription_id = models.CharField(max_length=100, blank=True, null=True)
    canceled_at = models.DateTimeField(null=True, blank=True)
    pause_collection = models.BooleanField(default=False)
    last_webhook_received = models.DateTimeField(null=True, blank=True)

    def __str__(self):
        return f"{self.user.username} - {self.plan.name if self.plan else 'No Plan'} ({self.status})"

    def is_in_trial(self):
        from django.utils import timezone
        return (
            self.status == 'trialing' and 
            self.trial_end is not None and 
            self.trial_end > timezone.now()
        )

    def get_subscription_status(self):
        """Returns the actual subscription status considering trial and cancellation"""
        from django.utils import timezone
        now = timezone.now()
        
        if self.status == 'canceled' or not self.is_active:
            return 'canceled'
        if self.is_in_trial():
            return 'trialing'
        if self.current_period_end and self.current_period_end < now:
            return 'past_due'
        return self.status

    def can_upload_file(self, file_type, file_size_mb=None, duration_min=None, pages=None):
        """Check if user can upload a new file based on their plan limits"""
        from django.utils import timezone

        # Get the current month's start
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Count uploads this month
        monthly_uploads = UploadedFile.objects.filter(
            user=self.user,
            uploaded_at__gte=month_start,
            file_type=file_type
        ).count()        
        remaining_uploads = 0
        if file_type == 'pdf':
            remaining_uploads = self.plan.pdf_uploads_per_month - monthly_uploads
            if remaining_uploads <= 0:
                return False, f"You've reached your monthly limit of {self.plan.pdf_uploads_per_month} PDF uploads"            
            if file_size_mb and file_size_mb > self.plan.pdf_max_size_mb:
                return False, f"File must be less than or equal to {self.plan.pdf_max_size_mb}MB (current: {round(file_size_mb, 1)}MB)"
            if pages and pages > self.plan.pdf_max_pages:
                return False, f"PDF must be {self.plan.pdf_max_pages} pages or less (current: {pages} pages)"

        elif file_type == 'audio':
            remaining_uploads = self.plan.audio_uploads_per_month - monthly_uploads
            if remaining_uploads <= 0:
                return False, f"You've reached your monthly limit of {self.plan.audio_uploads_per_month} audio uploads"
            if file_size_mb and file_size_mb > self.plan.audio_max_size_mb:
                return False, f"File must be less than or equal to {self.plan.audio_max_size_mb}MB (current: {round(file_size_mb, 1)}MB)"
            if duration_min and duration_min > self.plan.audio_max_length_min:
                return False, f"Audio must be {self.plan.audio_max_length_min} minutes or less (current: {round(duration_min, 1)} minutes)"

        elif file_type == 'youtube':
            remaining_uploads = self.plan.youtube_links_per_month - monthly_uploads
            if remaining_uploads <= 0:
                return False, f"You've reached your monthly limit of {self.plan.youtube_links_per_month} YouTube links"            
            if duration_min and duration_min > self.plan.youtube_max_length_min:
                return False, f"Video must be {self.plan.youtube_max_length_min} minutes or less (current: {round(duration_min, 1)} minutes)"
        print("OK - You have uploads remaining this month", remaining_uploads, file_type)
        # Add a more informative success message with remaining uploads
        return True, f"OK - You have {remaining_uploads} {file_type} uploads remaining this month"


    def can_generate_quiz(self, file_id):
        """Check if user can generate a new quiz"""
        from django.utils import timezone

        # Get the current month's start
        now = timezone.now()
        month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        
        # Count quizzes this month
        monthly_quizzes = Quiz.objects.filter(
            user=self.user,
            created_at__gte=month_start
        ).count()        
        remaining_quizzes = self.plan.quizzes_per_month - monthly_quizzes
        if remaining_quizzes <= 0:
            return False, f"You've reached your monthly limit of {self.plan.quizzes_per_month} quizzes"

        return True, f"OK - You have {remaining_quizzes} quizzes remaining this month"    
    def can_regenerate_summary(self, file_id):
        """Check if user can regenerate a summary"""

        # Get summaries for this file ordered by creation time
        summaries = Summary.objects.filter(
            user=self.user,
            uploaded_file_id=file_id
        ).order_by('created_at')

        if not summaries.exists():
            return False, "No summary exists for this file yet"

        # The first summary is the original, count only those after it
        initial_summary = summaries.first()
        regeneration_count = summaries.filter(
            created_at__gt=initial_summary.created_at
        ).count()

        allowed_regenerations = self.plan.summary_regenerations_per_file
        remaining = allowed_regenerations - regeneration_count

        # Debug logging
        print(f"Regeneration check for file {file_id}:")
        print(f"- Total summaries: {summaries.count()}")
        print(f"- Initial summary date: {initial_summary.created_at}")
        print(f"- Regeneration count: {regeneration_count}")
        print(f"- Allowed regenerations: {allowed_regenerations}")
        print(f"- Remaining: {remaining}")

        if remaining <= 0:
            return False, f"You've reached the limit of {allowed_regenerations} summary regenerations for this file"

        return True, f"OK - You have {remaining} summary regenerations remaining for this file"
            
    def can_send_chat_message(self, file_id):
        """Check if user can send another chat message"""

        # Count messages for this file
        message_count = ChatMessage.objects.filter(
            user=self.user,
            file_id=file_id
        ).count()        
        remaining_messages = self.plan.chatbot_messages_per_file - message_count
        print(remaining_messages)
        if remaining_messages <= 0:
            return False, f"You've reached the limit of {self.plan.chatbot_messages_per_file} messages for this file"

        return True, f"OK - You have {remaining_messages} messages remaining for this file"