from django import forms
from django.contrib.auth.models import User
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.forms import AuthenticationForm
from crispy_forms.helper import FormHelper
from crispy_forms.layout import Submit
from django.contrib.auth.password_validation import validate_password

class UserRegisterForm(UserCreationForm):
    email = forms.EmailField(
            required=True,
            widget=forms.EmailInput(attrs={
                'class': 'form-control',
                'placeholder': 'Email Address'
            })
    )
    username =forms.CharField(
            required=True,
            widget=forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'Username'
            })
    )
    password1 = forms.CharField(
            required=True,
            label='Password',
            widget=forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Password'
            })
    )
    password2 = forms.CharField(
            required=True,
            label='Confirm Password',
            widget=forms.PasswordInput(attrs={
                'class': 'form-control',
                'placeholder': 'Confirm Password'
            })
    )

    terms = forms.BooleanField(
            required=True, 
            label="I agree to the Terms of Service and Privacy Policy")
  
    class Meta:
        model = User
        fields = ['username', 'email', 'password1', 'password2', 'terms']

    def clean_email(self):
        # Ensure email is unique
        email = self.cleaned_data.get('email')
        if User.objects.filter(email=email).exists():
            raise forms.ValidationError("This email address is already in use.")
        return email

    def clean_username(self):
        username = self.cleaned_data.get('username')
        if User.objects.filter(username=username).exists():
            raise forms.ValidationError("This username is already taken.")
        return username

    def clean(self):
        # Validate passwords match
        cleaned_data = super().clean()
        password1 = cleaned_data.get("password1")
        password2 = cleaned_data.get("password2")
        
        if password1 != password2:
            raise forms.ValidationError("Passwords must match.")
        
        return cleaned_data

    def clean_password1(self):
        password1 = self.cleaned_data.get("password1")
        validate_password(password1)  # Use Django's built-in validators
        return password1

class CustomLoginForm(AuthenticationForm):
    username = forms.CharField(
        max_length=150,
        widget=forms.TextInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Username'
        })
    )
    password = forms.CharField(
        widget=forms.PasswordInput(attrs={
            'class': 'form-control', 
            'placeholder': 'Password'
        })
    )