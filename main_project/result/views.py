import os
import random
import re
import time
import requests
import pdfplumber
import fitz  # PyMuPDF
from pdf2image import convert_from_path, convert_from_bytes
import pytesseract
import io
import markdown 
import tempfile
import shutil 
import subprocess
from PIL import Image
from django.contrib import messages
from django.http import JsonResponse, StreamingHttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.contrib.auth.decorators import login_required
import json
from pytube import YouTube
from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile, Summary, ChatMessage, ExtractedText
from transformers import AutoTokenizer
from django.utils.safestring import mark_safe
import google.generativeai as genai
import assemblyai as aai

aai.settings.api_key = settings.ASSEMBLYAI_API_KEY
# Set up Gemini API client  
genai.configure(api_key=settings.GEMINI_API_KEY)

model = genai.GenerativeModel("gemini-2.0-flash-lite")

generation_config = {
    "temperature": 0.7,  # Adjust creativity level
    "top_p": 0.9,
    "top_k": 50,
    "max_output_tokens": 1500,
}

SYSTEM_BASE = """You are a helpful teacher assisting students. Follow these rules:
1. Answer based on the document summary and chat history
2. Format math with LaTeX: $inline$ and $$display$$
3. Add relevant extra knowledge when helpful
4. Keep answers under 150 words
5. Be friendly and use occasional emojis
6. If question is unrelated, politely decline
Current Document Summary: {summary}"""
# -------------------------------------------------------------------
# Helper Functions: Text Extraction using PyMuPDF
# -------------------------------------------------------------------

def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using PyMuPDF (fitz)."""
    text = ""
    try:
        with pdfplumber.open(pdf_path) as pdf:
            text = ""
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                text += page_text
            
            if len(text.strip()) > 100:
                return text
    except Exception:
        pass
    
    # For PyMuPDF
    try:
        doc = fitz.open(pdf_path)
        text = ""
        for page in doc:
            text += page.get_text()
            
        if len(text.strip()) > 100:
            return text
    except Exception:
        pass
    
    # For OCR
    try:
        images = convert_from_path(pdf_path)
        text = ""
        for image in images:
            text += pytesseract.image_to_string(image, config='--psm 6') + "\n"
            
        return text
    except Exception as e:
        raise Exception(f"Failed to extract text from PDF: {str(e)}")


def extract_text_from_txt(txt_path):
    """Extract text from a TXT file."""
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()
    


def generate_summary_with_gemini(text):
    """Send extracted text to Gemini API and get structured summary."""

    prompt = f"""
    You are an expert summarizer on educational content. 
    Summarize the following text in a **engaging and reader-friendly** with:
    - Use bold and clear **section headers** (like Introduction, Key Points, Conclusion) using <h4> html tags.
    - Use **clear headings and bullet points**.
    - Keep it **concise yet informative**.
    - When including mathematical formulas, please format them using LaTeX notation enclosed within dollar signs ($).
      For example, for an equation like 'y equals x squared', you should output '$y = x^2$'. 
      For subscripts, use 'a_i', for superscripts use 'b^2' and other complex ones like summation, intergrals etc.
    - Use nicely formatted html tables and diagrams **only if necessary**.
    - Include examples and explanations where needed.
    - Use appropriate emojis before a section header.
    - A **concise conclusion** summarizing the main ideas.
    
    Text: {text}
    """
    response = model.generate_content(prompt, generation_config=generation_config)

    return response.text if response.text else "No summary available."

# If needed, support long text by summarizing in chunks.
def split_text(text, max_chars=3000):
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]



def generate_long_summary(text):
    chunks = split_text(text, max_chars=3000)
    chunk_summaries = []
    for chunk in chunks:
        summary_chunk = generate_summary_with_gemini(chunk)
        chunk_summaries.append(summary_chunk)
        time.sleep(1)  # Delay to avoid rate limits
    combined_text = " ".join(chunk_summaries)
    final_summary = generate_summary_with_gemini(combined_text)
    return final_summary



def base(request, file_id):
    """Base view for the main page."""
    file = UploadedFile.objects.filter(user=request.user)

    return render(request, "result/base_result.html", {"file": file})

@login_required
def summary_result(request, file_id):
    """Handle document summary and chat interactions"""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)

    # Handle "regenerate" requests
    if "regenerate" in request.GET:
        try:
            summary = generate_or_retrieve_summary(request, uploaded_file)
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'success': True,
                    'summary': summary,
                    'timestamp': time.time()
                })
            return redirect('summary', file_id=file_id)
        except Exception as e:
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({'error': str(e)}, status=500)
            raise  # Rethrow so you see error in dev mode

    # Handle normal page load
    summary_instance = Summary.objects.filter(user=request.user, uploaded_file=uploaded_file).first()
    if summary_instance:
        summary = summary_instance.summary_text
    else:
        try:
            summary = generate_or_retrieve_summary(request, uploaded_file)
        except Exception as e:
            summary = f"Error generating summary: {str(e)}"

    formatted_summary = markdown.markdown(summary) if summary else "No summary available"

    # Handle chat message via AJAX
    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return handle_chat_request(request, uploaded_file)

    # Chat history display
    chat_history = ChatMessage.objects.filter(
        user=request.user,
        file=uploaded_file
    ).order_by('-timestamp')[:10][::-1]

    return render(request, "result/summary.html", {
        "file": uploaded_file,
        "summary": formatted_summary,
        "chat_history": [
            {
                **msg.__dict__,
                'formatted_content': markdown.markdown(msg.content)
            }
            for msg in chat_history
        ]
    })



def generate_or_retrieve_summary(request, uploaded_file):
    """Generate or retrieve document summary"""
    user = request.user  # Force evaluation of lazy object
    is_youtube = uploaded_file.file_type == 'youtube'
    summary_instance = Summary.objects.filter(user=user, uploaded_file=uploaded_file).first()
    extracted_text_instance = ExtractedText.objects.filter(user=user, uploaded_file=uploaded_file).first()
    extracted_text = ""

    if extracted_text_instance is not None:
        extracted_text = extracted_text_instance.extracted_text
    else:
        try:
            # Text extraction step
            if is_youtube:
                try:
                    extracted_text = download_and_transcribe_youtube(uploaded_file.youtube_link)
                except Exception as e:
                    print(f"YouTube extraction error: {e}")
                    return f"Error in YouTube extraction: {str(e)}"
            else:
                file_path = uploaded_file.file.path
                try:
                    if file_path.lower().endswith(".pdf"):
                        extracted_text = extract_text_from_pdf(file_path)
                    elif file_path.lower().endswith(".txt"):
                        extracted_text = extract_text_from_txt(file_path)
                    elif file_path.lower().endswith((".wav", ".mp3", ".ogg", ".m4a")):
                        extracted_text = transcribe_audio_assemblyai(file_path)
                except Exception as e:
                    print(f"Text extraction error: {e}")
                    return f"Error in text extraction: {str(e)}"
                    
            # Create extracted text record
            try:
                ExtractedText.objects.create(user=user, uploaded_file=uploaded_file, extracted_text=extracted_text)
            except Exception as e:
                print(f"ExtractedText creation error: {e}")
                return f"Error creating extracted text record: {str(e)}"
                
        except Exception as e:
            print(f"General extraction error: {e}")
            return f"Error during processing: {str(e)}"

    # Summary generation step
    try:
        if len(extracted_text) > 3000:
            summary = generate_long_summary(extracted_text)
        else:
            summary = generate_summary_with_gemini(extracted_text)
    except Exception as e:
        print(f"Summary generation error: {e}")
        return f"Error generating summary: {str(e)}"
        
    # Save summary
    try:
        if summary_instance:
            summary_instance.summary_text = summary
            summary_instance.save()
        else:
            Summary.objects.create(user=user, uploaded_file=uploaded_file, summary_text=summary)
    except Exception as e:
        print(f"Summary saving error: {e}")
        return f"Error saving summary: {str(e)}"
    
    return summary


@login_required
def handle_chat_request(request, uploaded_file):
    """Process chat messages with Gemini"""
    if request.POST.get('message') != None:
        user_message = request.POST.get('message').strip()
    else:
        user_message = request.POST.get('message-chat').strip()

    if not user_message:
        return JsonResponse({'error': 'Empty message'}, status=400)

    # Get document summary once
    summary_text = Summary.objects.filter(
        user=request.user, 
        uploaded_file=uploaded_file
    ).values_list('summary_text', flat=True).first() or "No summary available"

    # Create system instruction with summary
    system_instruction = SYSTEM_BASE.format(summary=summary_text)

    # Get last 3 exchanges (6 messages)
    history_messages = ChatMessage.objects.filter(
        user=request.user,
        file=uploaded_file
    ).order_by('-timestamp')[:6]

    # Format history for Gemini
    history = []
    for msg in reversed(history_messages):
        history.append({
            "role": "user" if msg.role == "user" else "model",
            "parts": [msg.content]
        })

    try:
        # Initialize model with system instruction
        model = genai.GenerativeModel(
            model_name="gemini-2.0-flash-lite",
            system_instruction=system_instruction
        )
        chat = model.start_chat(history=history)

        # Store user message
        ChatMessage.objects.create(
            user=request.user,
            file=uploaded_file,
            role='user',
            content=user_message
        )
        
        # Get response
        response = chat.send_message(user_message)
        bot_response = response.text

        # Store bot response
        ChatMessage.objects.create(
            user=request.user,
            file=uploaded_file,
            role='bot',
            content=bot_response
        )

        return JsonResponse({'response': bot_response})

    except Exception as e:
        print(f"Chat error: {str(e)}")
        return JsonResponse({'error': str(e)}, status=500)

@login_required
def generate_mcqs_with_gemini(summary_text, num_questions, difficulty):
    """Generate multiple-choice questions dynamically based on the summary."""
    
    prompt = f"""
    Generate {num_questions} multiple-choice questions based on the following summary. 
    The questions should be {difficulty} level.

    - Each question must have four answer choices (A, B, C, D).
    - Clearly mark the correct answer.
    - The format should be:
      
      Question: ...
      A) ...
      B) ...
      C) ...
      D) ...
      Correct Answer: X
    
    Summary: {summary_text}
    """
    response = model.generate_content(prompt, generation_config=generation_config)
    return response.text if response.text else "No MCQs generated."

@login_required
def parse_mcq_response(mcq_text):
    """Extract MCQs from AI-generated response."""
    mcqs = []
    questions = mcq_text.split("Question: ")[1:]  # Split based on "Question: "

    for q in questions:
        lines = q.strip().split("\n")
        if len(lines) >= 6:
            question = lines[0]
            option_a = lines[1][3:].strip()  # Remove "A) "
            option_b = lines[2][3:].strip()  # Remove "B) "
            option_c = lines[3][3:].strip()  # Remove "C) "
            option_d = lines[4][3:].strip()  # Remove "D) "
            correct_option = lines[5][-1].strip()  # Last character of "Correct Answer: X"

            mcqs.append({
                "question": question,
                "option_a": option_a,
                "option_b": option_b,
                "option_c": option_c,
                "option_d": option_d,
                "correct_option": correct_option,
            })
    return mcqs

@login_required
def quiz_options(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)

    return render(request, "result/quiz_options.html", {"file": uploaded_file})

@login_required
def take_quiz(request, file_id):
    """Generates and displays the quiz."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    summary_instance = get_object_or_404(Summary, uploaded_file=uploaded_file)

    num_questions = int(request.GET.get("num_questions", 10))
    difficulty = request.GET.get("difficulty", "medium").lower()

    # Generate MCQs on the fly
    mcq_text = generate_mcqs_with_gemini(summary_instance.summary_text, num_questions, difficulty)
    mcqs = parse_mcq_response(mcq_text)
    random.shuffle(mcqs)

    request.session['mcqs'] = mcqs  # Store MCQs in session for later use

    return render(request, "result/quiz.html", {"mcqs": mcqs, "file": uploaded_file})

@login_required
def submit_quiz(request, file_id):
    """Handles quiz submission and calculates the score."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    mcqs = request.session.get("mcqs", [])  # Retrieve MCQs from session

    user_answers = request.POST
    correct_count = 0
    results = []


    for index, mcq in enumerate(mcqs):
        user_choice = user_answers.get(str(index), "")
        option_mapping = {
            "A": mcq["option_a"],
            "B": mcq["option_b"],
            "C": mcq["option_c"],
            "D": mcq["option_d"],
        }
        user_choice_text = option_mapping.get(user_choice, "")
        correct_answer_text = option_mapping.get(mcq["correct_option"], "")
        is_correct = user_choice == mcq["correct_option"]
        if is_correct:
            correct_count += 1
        results.append({
            "question": mcq["question"],
            "user_choice": user_choice_text,
            "correct_choice": correct_answer_text,
            "is_correct": is_correct,
            "options": [mcq["option_a"], mcq["option_b"], mcq["option_c"], mcq["option_d"]],
        })

    score = (correct_count / len(mcqs)) * 100 if mcqs else 0

    return render(request, "result/quiz_result.html", {"mcqs":mcqs, "results": results, "score": score, "file": uploaded_file})

@login_required
def chatbot(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    summary_instance = Summary.objects.filter(user=request.user, uploaded_file=uploaded_file).first()

    summary = summary_instance.summary_text

    if request.method == 'POST' and request.headers.get('X-Requested-With') == 'XMLHttpRequest':
        return handle_chat_request(request, uploaded_file, summary)
    
    # Display page with history
    chat_history = ChatMessage.objects.filter(
        user=request.user, 
        file=uploaded_file
    ).order_by('-timestamp')[:10][::-1]

    for message in chat_history:
        message.formatted_content = markdown.markdown(message.content)

    context = {
        "file": uploaded_file,
        "chat_history": chat_history
    }
    return render(request, "result/chatbot.html", context)



def transcribe_audio_assemblyai(audio_file_path):
    """Transcribes audio from a file path using AssemblyAI."""
    headers = {"authorization": settings.ASSEMBLYAI_API_KEY}

    try:
        # Upload audio file
        with open(audio_file_path, "rb") as f:
            upload_response = requests.post(
                "https://api.assemblyai.com/v2/upload",
                headers=headers,
                data=f,
                timeout=300
            )
        upload_response.raise_for_status()
        audio_url = upload_response.json()["upload_url"]

        # Start transcription job
        transcript_response = requests.post(
            "https://api.assemblyai.com/v2/transcript",
            headers=headers,
            json={"audio_url": audio_url}
        )
        transcript_response.raise_for_status()
        transcript_id = transcript_response.json()["id"]

        # Poll for result
        polling_url = f"https://api.assemblyai.com/v2/transcript/{transcript_id}"
        while True:
            polling_response = requests.get(polling_url, headers=headers)
            result = polling_response.json()

            if result["status"] == "completed":
                return result["text"]
            elif result["status"] == "error":
                return f"Transcription failed: {result['error']}"

            time.sleep(5)

    except requests.exceptions.RequestException as e:
        return f"Transcription error: {e}"
def download_and_transcribe_youtube(youtube_url):
    """Transcribe a YouTube video directly using AssemblyAI"""
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            audio_path = os.path.join(temp_dir, 'audio.mp3')

            # Download and convert to MP3 using yt-dlp and ffmpeg
            subprocess.run([
                'yt-dlp',
                '-x',
                '--audio-format', 'mp3',
                '--ffmpeg-location', 'C:/ffmpeg/ffmpeg-7.1.1-essentials_build/ffmpeg-7.1.1-essentials_build/bin',  # Adjust this if you installed elsewhere
                '-o', audio_path,
                youtube_url
            ], check=True)

            # Transcribe the audio using your existing AssemblyAI function
            print("Downloading done, starting transcription...")
            return transcribe_audio_assemblyai(audio_path)

    except subprocess.CalledProcessError as e:
        return f"Download error: {str(e)}"
    except Exception as e:
        return f"Transcription error: {str(e)}"

@login_required
def transcripts(request, file_id):
    """Display the transcript of the uploaded audio file."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    transcript_instance = ExtractedText.objects.filter(user=request.user, uploaded_file=uploaded_file).first()
    
    if not transcript_instance:
        return JsonResponse({'error': 'Transcript not found'}, status=404)

    transcript_text = transcript_instance.extracted_text
    formatted_transcript = markdown.markdown(transcript_text) if transcript_text else "No transcript available"
    
    return render(request, "result/extracted_text.html", {
        "file": uploaded_file,
        "transcript": formatted_transcript
    })