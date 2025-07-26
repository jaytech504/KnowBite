from django.shortcuts import render, redirect, get_object_or_404
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.contrib.auth import login
from django.conf import settings
from django.http import JsonResponse, HttpResponse
from .forms import UserRegisterForm, CustomLoginForm
from django.contrib.auth.views import LoginView
from django.contrib.auth.decorators import login_required
from django.contrib.auth import login, authenticate, logout
from django.contrib import messages
# Create your views here.

def register(request):
    if request.method == 'POST':
        form = UserRegisterForm(request.POST)
        if form.is_valid():
            user = form.save()
            messages.success(request, "Your account has been created successfully!")
            return redirect('login')
        else:
            messages.error(request, "Please correct the errors below.")
    else:
        form = UserRegisterForm()
    
    return render(request, 'users/register.html', {'form': form})

class CustomLoginView(LoginView):
    template_name = 'users/login.html'
    authentication_form = CustomLoginForm

def logout_view(request):
    logout(request)
    return redirect("landing_page")

def terms_of_service(request):

    return render(request, 'users/terms_of_service.html')

def privacy_policy(request):

    return render(request, 'users/privacy_policy.html')

    