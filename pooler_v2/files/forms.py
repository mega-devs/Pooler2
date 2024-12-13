from django import forms
from .models import UploadedFile, ExtractedData


class UploadedFileForm(forms.ModelForm):
    class Meta:
        model = UploadedFile
        fields = ['filename', 'country', 'is_checked']
        widgets = {
            'filename': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'is_checked': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }

class ExtractedDataForm(forms.ModelForm):
    class Meta:
        model = ExtractedData
        fields = ['email', 'password', 'provider', 'country', 'filename', 'upload_origin']
        widgets = {
            'email': forms.TextInput(attrs={'class': 'form-control'}),
            'password': forms.TextInput(attrs={'class': 'form-control'}),
            'provider': forms.TextInput(attrs={'class': 'form-control'}),
            'country': forms.TextInput(attrs={'class': 'form-control'}),
            'filename': forms.TextInput(attrs={'class': 'form-control'}),
            'upload_origin': forms.TextInput(attrs={'class': 'form-control'}),
        }