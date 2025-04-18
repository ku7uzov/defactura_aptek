from django import forms

class FileUploadForm(forms.Form):
    pharmacies_file = forms.FileField(label='Файл с аптеками (Excel)')
