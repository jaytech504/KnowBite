from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .forms import FileUploadForm
from .models import UploadedFile
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages

# Create your views here.

def landing_page(request):
    return render(request, 'knowbite/landing_page.html')

@login_required
def dashboard(request):
    files = UploadedFile.objects.all()
    context = {
        'title': 'Dashboard',
        'files': files
    }
    return render(request, 'knowbite/dashboard.html', context)

@login_required
def upload_file(request):
    if request.method == 'POST':
        file_type = request.POST.get('file_type')
        youtube_link = request.POST.get('youtube_link', '').strip()

        if youtube_link:
            UploadedFile.objects.create(file_type='youtube', youtube_link=youtube_link, user=request.user)
            messages.success(request, "Youtube link uploaded successfully")
            return redirect('dashboard')

        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            uploaded_file.save()
            messages.success(request, "File uploaded successfully.")

            return redirect('summary', file_id=uploaded_file.id)
        else:
            messages.error(request, "File upload failed. Please check file type.")

    return render(request, 'knowbite/dashboard.html')


@login_required
def yournotes(request, file_id=None):
    files = UploadedFile.objects.filter(user=request.user).order_by('-uploaded_at')
    one_file = None
    if file_id:
        one_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)

    if request.method == 'POST':
        one_file.delete()
        return redirect('yournotes')

    context = {
        'title': 'Yournotes',
        'files': files,
        'one_file': one_file
    }
    return render(request, 'knowbite/yournotes.html', context)

@require_POST
@csrf_exempt
def toggle_dark_mode(request):
    dark_mode = request.COOKIES.get('dark_mode', 'false') == 'true'
    dark_mode = not dark_mode
    response = JsonResponse({'success': True})
    response.set_cookie('dark_mode', str(dark_mode).lower(), max_age=30*24*60*60)
    return response
@login_required
def settings(request):
    context = {
        'title': 'Settings'
    }
    return render(request, 'knowbite/settings.html', context)