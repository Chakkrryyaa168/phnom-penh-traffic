import os
from django import forms


class TrafficUploadForm(forms.Form):
    csv_file = forms.FileField(
        label="Traffic CSV File",
        help_text="Required columns: 'intersection', 'timestamp', 'volume'",
        widget=forms.FileInput(attrs={
            'class': 'form-control form-control-lg',
            'accept': '.csv,text/csv',
            'id': 'csv_file_input'
        })
    )
    clear_existing = forms.BooleanField(
        required=False,
        initial=False,
        label="Replace existing data",
        help_text="Check to remove all previous intersections and records before importing.",
        widget=forms.CheckboxInput(attrs={
            'class': 'form-check-input',
            'id': 'clear_existing'
        })
    )

    def clean_csv_file(self):
        uploaded_file = self.cleaned_data.get('csv_file')
        if not uploaded_file:
            raise forms.ValidationError("No file was uploaded.")

        filename = uploaded_file.name
        ext = os.path.splitext(filename)[1].lower()
        if ext != '.csv':
            raise forms.ValidationError("Invalid file extension. Please upload a standard .csv file.")

        # Limit maximum file size (e.g. 25MB)
        if uploaded_file.size > 25 * 1024 * 1024:
            raise forms.ValidationError("File size exceeds 25MB limit.")

        return uploaded_file

