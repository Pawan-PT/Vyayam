"""
VYAYAM STRENGTH TRAINING - DJANGO FORMS
Forms for patient registration and feedback

NOTE: These forms are not used in V1 — registration uses v1_onboarding_views.py
Kept for reference only.
"""

from django import forms
from .models import PatientProfile


class PatientRegistrationForm(forms.ModelForm):
    """Form for new patient registration"""
    
    password = forms.CharField(widget=forms.PasswordInput(), help_text="Your account password")
    
    medical_conditions = forms.MultipleChoiceField(
        choices=[
            ('high_bp', 'High Blood Pressure'),
            ('diabetes', 'Diabetes'),
            ('heart_disease', 'Heart Disease'),
            ('asthma', 'Asthma'),
            ('arthritis', 'Arthritis'),
            ('previous_injury', 'Previous Injury'),
        ],
        widget=forms.CheckboxSelectMultiple(),
        required=False,
        help_text="Select all that apply"
    )
    
    class Meta:
        model = PatientProfile
        fields = [
            'name', 'phone', 'email', 'age',
            'occupation', 'lifestyle', 'goals',
            'prescription_mode'
        ]
        widgets = {
            'name': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'John Doe'}),
            'phone': forms.TextInput(attrs={'class': 'form-control', 'placeholder': '+91-9876543210'}),
            'email': forms.EmailInput(attrs={'class': 'form-control', 'placeholder': 'john@email.com'}),
            'age': forms.NumberInput(attrs={'class': 'form-control', 'min': 10, 'max': 100}),
            'occupation': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Software Engineer'}),
            'lifestyle': forms.Select(attrs={'class': 'form-control'}),
            'goals': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 3,
                'placeholder': 'e.g., Build functional strength, lose weight, improve fitness'
            }),
            'prescription_mode': forms.Select(attrs={'class': 'form-control'}),
        }
    
    def save(self, commit=True):
        patient = super().save(commit=False)
        
        # Store medical conditions as JSON
        patient.medical_conditions_json = self.cleaned_data['medical_conditions']
        
        # Set contraindications based on medical conditions
        contraindications = []
        for condition in patient.medical_conditions_json:
            if 'bp' in condition.lower():
                contraindications.append('no_high_intensity')
            if 'diabetes' in condition.lower():
                contraindications.append('monitor_blood_sugar')
            if 'knee' in condition.lower() or 'joint' in condition.lower() or 'arthritis' in condition.lower():
                contraindications.append('limited_rom')
        
        patient.contraindications_json = contraindications
        
        if commit:
            patient.save()
        
        return patient


class DailyFeedbackForm(forms.Form):
    """Form for daily workout feedback"""
    
    comfortable = forms.BooleanField(
        required=False,
        initial=True,
        label="Were you comfortable with today's workout?",
        widget=forms.CheckboxInput(attrs={'class': 'form-check-input'})
    )
    
    difficulty_rating = forms.IntegerField(
        min_value=1,
        max_value=5,
        initial=3,
        label="How difficult was today's session? (1=Too easy, 3=Just right, 5=Too hard)",
        widget=forms.NumberInput(attrs={'class': 'form-control', 'type': 'range'})
    )
    
    notes = forms.CharField(
        required=False,
        label="Any additional notes?",
        widget=forms.Textarea(attrs={'class': 'form-control', 'rows': 3})
    )
