from django import forms
from .models import UploadedFile


class FileUploadForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['file', 'file_type']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields['file_type'].choices = [
            ('pdf', 'PDF'),
            ('audio', 'Audio'),
            ('youtube', 'YouTube')  # Though YouTube is handled separately
        ]