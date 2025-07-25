from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.models import User
from django.contrib.auth import login
import firebase_admin
from firebase_admin import credentials, auth
import json
import os

# Initialize Firebase Admin SDK
cred = credentials.Certificate({
    "type": "service_account",
    "project_id": "knowbite-dc17e",
    "private_key_id": os.environ.get('FIREBASE_PRIVATE_KEY_ID'),
    "private_key": os.environ.get('FIREBASE_PRIVATE_KEY').replace('\\n', '\n'),
    "client_email": os.environ.get('FIREBASE_CLIENT_EMAIL'),
    "client_id": os.environ.get('FIREBASE_CLIENT_ID'),
    "auth_uri": "https://accounts.google.com/o/oauth2/auth",
    "token_uri": "https://oauth2.googleapis.com/token",
    "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
    "client_x509_cert_url": os.environ.get('FIREBASE_CLIENT_CERT_URL')
})

firebase_admin.initialize_app(cred)

@csrf_exempt
def firebase_auth_view(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        token = data.get('token')
        
        try:
            # Verify the Firebase token
            decoded_token = auth.verify_id_token(token)
            uid = decoded_token['uid']
            email = decoded_token['email']
            display_name = data.get('display_name', '')

            # Get or create user
            try:
                user = User.objects.get(email=email)
            except User.DoesNotExist:
                # Create new user
                username = email.split('@')[0]
                # Make sure username is unique
                base_username = username
                counter = 1
                while User.objects.filter(username=username).exists():
                    username = f"{base_username}{counter}"
                    counter += 1
                
                user = User.objects.create_user(
                    username=username,
                    email=email,
                    first_name=display_name
                )

            # Log the user in
            login(request, user)
            
            return JsonResponse({
                'success': True,
                'redirect_url': '/dashboard/'
            })
            
        except Exception as e:
            return JsonResponse({
                'success': False,
                'error': str(e)
            }, status=400)
            
    return JsonResponse({'error': 'Invalid request method'}, status=405)
