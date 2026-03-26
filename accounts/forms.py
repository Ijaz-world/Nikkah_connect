from django import forms
from django.contrib.auth.forms import UserCreationForm, AuthenticationForm
from .models import User
from .models import Profile
from .models import PartnerPreference


class RegisterForm(UserCreationForm):
    full_name    = forms.CharField(max_length=100, required=True)
    email        = forms.EmailField(required=True)
    phone_number = forms.CharField(max_length=15, required=False)

    class Meta:
        model  = User
        fields = ['full_name', 'email', 'phone_number', 'password1', 'password2']

    def clean_email(self):
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email is already registered.")
        return email

    def save(self, commit=True):
        user = super().save(commit=False)
        full_name = self.cleaned_data.get('full_name', '').strip()
        parts = full_name.split(' ', 1)
        user.first_name  = parts[0]
        user.last_name   = parts[1] if len(parts) > 1 else ''
        user.email       = self.cleaned_data['email']
        user.username    = self.cleaned_data['email']
        user.phone_number = self.cleaned_data.get('phone_number', '')
        user.is_email_verified = False
        if commit:
            user.save()
        return user


class LoginForm(AuthenticationForm):
    username = forms.EmailField(label='Email Address')

class ProfileStep1Form(forms.ModelForm):
    """Basic Information"""
    class Meta:
        model  = Profile
        fields = ['date_of_birth', 'gender', 'height',
                  'nationality', 'caste_sect', 'marital_status', 'has_children']
        widgets = {
            'date_of_birth': forms.DateInput(attrs={'type': 'date'}),
        }


class ProfileStep2Form(forms.ModelForm):
    """Purpose & Discovery"""
    class Meta:
        model  = Profile
        fields = ['purpose', 'heard_from']


class ProfileStep3Form(forms.ModelForm):
    """Education & Profession"""
    class Meta:
        model  = Profile
        fields = ['education', 'profession']


class ProfileStep4Form(forms.ModelForm):
    """Religious Information"""
    class Meta:
        model  = Profile
        fields = ['faith_level', 'born_muslim', 'halal_food']


class ProfileStep5Form(forms.ModelForm):
    """Lifestyle"""
    class Meta:
        model  = Profile
        fields = ['dress_style', 'smoking', 'drinking']


class ProfileStep6Form(forms.ModelForm):
    """Location & Background"""
    class Meta:
        model  = Profile
        fields = ['country', 'city', 'grew_up_in', 'open_to_abroad']


class ProfileStep7Form(forms.ModelForm):
    """Bio & Media"""
    class Meta:
        model  = Profile
        fields = ['about_me', 'profile_photo']
        widgets = {
            'about_me': forms.Textarea(attrs={'rows': 4,
                'placeholder': 'Write a short bio about yourself...'}),
        }

class PartnerPreferenceForm(forms.ModelForm):
    class Meta:
        model  = PartnerPreference
        fields = [
            'min_age', 'max_age',
            'preferred_country',
            'preferred_caste_sect',
            'preferred_ethnicity',
            'preferred_marital_status',
            'preferred_education',
            'preferred_faith_level',
            'preferred_smoking',
            'preferred_drinking',
        ]
        widgets = {
            'min_age': forms.NumberInput(attrs={'min': 18, 'max': 80}),
            'max_age': forms.NumberInput(attrs={'min': 18, 'max': 80}),
        }