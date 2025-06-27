from django.shortcuts import render, redirect, get_object_or_404
from django.http import JsonResponse
from .forms import FileUploadForm
from .models import UploadedFile
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.contrib import messages
import fitz # PyMuPDF for PDF handling
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

        # Get user's subscription
        try:
            user_subscription = request.user.usersubscription
        except:
            messages.error(request, "You need an active subscription to upload files")
            return redirect('pricing')

        # Handle YouTube links separately
        if file_type == 'youtube':
            if not youtube_link:
                messages.error(request, "YouTube URL is required")
                return redirect('dashboard')
            
            # Check YouTube upload limits
            import yt_dlp
            try:
                ydl_opts = {
                    'quiet': True,
                    'extract_flat': True,
                    'force_generic_extractor': True,
                    'no_warnings': True
                }
                with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                    info = ydl.extract_info(youtube_link, download=False)
                    duration_min = info.get('duration', 0) / 60  # Convert seconds to minutes
                    title = info.get('title', 'Unknown Title')  # Get video title or fallback to URL
                    print(duration_min)
                    can_upload, message = user_subscription.can_upload_file('youtube', duration_min=duration_min)
                    if not can_upload:
                        messages.error(request, message)
                        return redirect('dashboard')
            except Exception as e:
                messages.error(request, f"Error processing YouTube link: {str(e)}")
                return redirect('dashboard')
            
            try:
                uploaded_file = UploadedFile.objects.create(
                    user=request.user,
                    file_type='youtube',
                    youtube_link=youtube_link,
                    file=None,
                    title=title
                )
                messages.success(request, "YouTube link saved successfully")
                return redirect('summary', file_id=uploaded_file.id)
            except Exception as e:
                messages.error(request, f"Error saving YouTube link: {str(e)}")
                return redirect('dashboard')        # Handle file uploads
        form = FileUploadForm(request.POST, request.FILES)
        if form.is_valid():
            uploaded_file = form.save(commit=False)
            uploaded_file.user = request.user
            
            # Validate file type consistency
            if uploaded_file.file_type == 'youtube':
                messages.error(request, "Invalid file type selection")
                return redirect('dashboard')
                
            # Check file size and other limits
            file_size_mb = uploaded_file.file.size / (1024 * 1024)  # Convert to MB
              # For PDFs, get page count
            pages = None            
            if uploaded_file.file_type == 'pdf':
                try:
                    # Get the file content as bytes
                    file_content = uploaded_file.file.read()
                    # Open PDF from memory stream
                    with fitz.open(stream=file_content, filetype="pdf") as pdf:
                        pages = len(pdf)
                        print(f"PDF pages: {pages}")
                    # Reset file pointer for later use
                    uploaded_file.file.seek(0)
                except Exception as e:
                    print(f"Error counting PDF pages: {str(e)}")
                    pages = None
            
            # For audio, get duration
            duration_min = None
            if uploaded_file.file_type == 'audio':
                try:
                    import mutagen
                    audio = mutagen.File(uploaded_file.file)
                    if audio:
                        duration_min = audio.info.length / 60  # Convert seconds to minutes
                        print(duration_min)
                except:
                    duration_min = None
            
            # Check limits based on file type
            can_upload, message = user_subscription.can_upload_file(
                uploaded_file.file_type,
                file_size_mb=file_size_mb,
                duration_min=duration_min,
                pages=pages
            )
            
            if not can_upload:
                messages.error(request, message)
                return redirect('dashboard')
                
            uploaded_file.save()
            messages.success(request, "File uploaded successfully")
            return redirect('summary', file_id=uploaded_file.id)
        else:
            # Improved error messaging
            errors = "\n".join([f"{field}: {','.join(errors)}" for field, errors in form.errors.items()])
            messages.error(request, f"Upload failed:\n{errors}")
    
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

@login_required
def settings(request):
    user_plan = request.user.usersubscription
    context = {
        'title': 'Settings',
        'user_plan': user_plan
    }
    return render(request, 'knowbite/settings.html', context)