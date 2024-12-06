from django import forms
from .models import UploadedFile

class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['filename', 'country', 'is_checked']
        widgets = {
            'filename': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'is_checked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }