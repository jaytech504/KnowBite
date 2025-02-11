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