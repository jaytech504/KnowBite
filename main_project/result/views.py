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

from django.conf import settings
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile, Summary, ChatMessage, ExtractedText, Quiz
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
    "max_output_tokens": 8000,
}


SYSTEM_BASE = """You are a helpful teacher assisting students. Follow these rules:
1. Answer using document summary and chat history as context but also add necessary related information if needed.
2. Format math with LaTeX: $inline$ and $$display$$
3. Explain concepts in easy to understand terms and use relevant extra knowledge when helpful
4. Keep some answers under 150 words unless necessary then up to 500 words.
5. Be friendly and use occasional emojis
6. If question is unrelated, politely decline
Current Document Summary: {summary}"""


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
    


def generate_summary_with_gemini(text, plan_type):
    """Send extracted text to Gemini API and get structured summary based on plan type."""

    base_prompt = f"""
You are an expert educational blogger and content designer. Your job is to turn the following text into a beautifully formatted, engaging blog post summary that will be rendered within a <div> container on a modern website.

IMPORTANT FORMATTING RULES:
- Do NOT include a table of contents or any list of sections.
- All output must be valid HTML that renders beautifully (do NOT use <html>, <body>, or <head> tags).
- **Do not put the output in a div**
- Add style tag with css classes for the summary
- **Do not set a background color**
- Do not set a font family
- Start section headers with colored <h4> (<h1>, <h2>, or <h3>) and relevant emojis in headers.
- Use semantic HTML5 tags and CSS classes that work with standard blog styling.
- Use short paragraphs, lots of white space, and clear visual separation between sections.
- Use modern, attractive formatting and layout throughout, like top-tier blogs (Medium, Notion, Substack).
- Use css styled <table> for comparisons or data, <blockquote> and <div class='pro-tip'> for callouts, and <mark>, <b>, <i>, <u>, <code>, <span class='highlight'> for emphasis.
- All HTML elements must be properly nested and closed.
- Use $...$ for inline math and formulas (LaTeX style).
"""


    if plan_type.lower() == 'free':
        prompt = f"""{base_prompt}
- Do not exceed 750 words
- Use emojis for section headers to make it engaging 📚
- Format with clear section headers (like 📋 Introduction, 🎯 Key Points, 🎬 Conclusion) in <h4> tags
- Use bullet points for key information
- Keep it concise but informative
- When there are mathematical formulas, use LaTeX notation ($formula$)
- Use simple tables for important comparisons only
- Focus on essential information and main concepts
- Keep sections brief and to the point
Text: {text}
"""
    elif plan_type.lower() == 'basic':
        prompt = f"""{base_prompt}
- Make the summary at least 1000 - 1500 words
- Make it elaborate
- Start with a captivating introduction in a <h4> tag, using a relevant emoji
- Use stylish, modern section headers in <h4> tags with relevant emojis for each section
- Break down concepts into clear, well-structured sections with short paragraphs
- Use bullet points, numbered lists, and callout boxes for key ideas
- design diagrams for categories, process or flowchart where and if necessary
- Add at least one <table> for comparisons, frameworks, or data (make it visually appealing and easy to read)
- Highlight practical examples and real-world applications
- Include 2 example of step by step solution if it contains any mathematical or programming content.
- Include at least one 'Pro Tip' or 'Did You Know?' callout in a <blockquote> or <div class='pro-tip'> with a distinct style
- Use <b>, <i>, <u>, and <mark> for emphasis and highlights
- Add a visually distinct conclusion in a <h4> tag with an emoji
- Use $...$ for inline math and formulas
- Make the layout look like a popular, beautiful blog (think Medium, Notion, or Substack)
- Use short paragraphs and lots of white space for readability
Text: {text}
"""
    elif plan_type.lower() == 'pro':
        prompt = f"""{base_prompt}
- Make the summary at least a 1500 - 3000 words
- Make it elaborate and verbose
- Begin with a compelling hook and overview in a <h4> tag, using a carefully chosen emoji
- Use professional, modern section headers in <h4> tags with unique, relevant emojis for each section
- Break down complex concepts into digestible, visually separated sections with short paragraphs and clear subheadings
- **Always** Use <table> for data, comparisons, or frameworks (at least one, make sure it is styled for clarity and visual appeal)
- Include graphs, diagrams, flowchart or any other visual element where necessary
- Add advanced formatting: <blockquote>, <div class='pro-tip'>, <mark>, <b>, <i>, <u>, <code> for code snippets, and <span class='highlight'> for key points
- Always include at least one 'Pro Tip', 'Expert Insight', or 'Did You Know?' in a callout box with a distinct style
- Use bullet points, numbered lists, and callouts for clarity and engagement
- Add practical examples, real-world applications, and actionable advice in visually distinct boxes or highlights
- Use $...$ for inline math and highlight important equations
- Include at least **1-2 example** of step by step solution if it contains any mathematical or programming content.
- End with a strong, visually distinct conclusion in a <h4> tag with an emoji
- Make the layout look like a top-tier, beautiful blog (think Medium, Notion, Substack, or top SaaS blogs)
- Use short paragraphs, white space, and modern web style for maximum readability
Text: {text}
"""
    else:  # Fallback to free plan if unknown type
        prompt = f"""{base_prompt}
- Use emojis for section headers to make it engaging 📚
- Format with clear section headers in <h4> tags
- Use bullet points for key information
- Keep it concise but informative
- When there are mathematical formulas, use LaTeX notation ($formula$)
- Focus on essential information and main concepts
Text: {text}
"""

    try:
        print(f"Generating summary for plan type: {plan_type}")
        print(f"Input text length: {len(text)} characters")
        
        if not text or len(text.strip()) == 0:
            print("Error: Empty input text")
            return "Error: No text content available to summarize"
            
        response = model.generate_content(prompt, generation_config=generation_config)
        
        if not response:
            print("Error: No response from Gemini API")
            return "Error: Failed to generate summary - no response from AI"
            
        if not response.text:
            print("Error: Empty response text from Gemini API")
            return "Error: Failed to generate summary - empty response"
            
        print(f"Successfully generated summary of length: {len(response.text)}")
        return response.text
        
    except Exception as e:
        print(f"Error in generate_summary_with_gemini: {str(e)}")
        return f"Error: Failed to generate summary - {str(e)}"

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
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)    # Handle "regenerate" requests    
    if "regenerate" in request.GET:
        # Check regeneration limits
        print('Start regeneration check')
        try:
            user_subscription = request.user.usersubscription
            print(f"User Plan: {user_subscription.plan.name}")
            print(f"Plan regenerations allowed: {user_subscription.plan.summary_regenerations_per_file}")
            
            # Get all summaries for this file
            summaries = Summary.objects.filter(
                user=request.user,
                uploaded_file_id=file_id
            ).order_by('created_at')
            print(f"Total summaries for this file: {summaries.count()}")
            
            if summaries.exists():
                initial_summary = summaries.first()
                regenerations = summaries.filter(created_at__gt=initial_summary.created_at).count()
                print(f"Number of regenerations: {regenerations}")
            
            can_regenerate, message = user_subscription.can_regenerate_summary(file_id)
            print(f"Can regenerate: {can_regenerate}")
            print(f"Message: {message}")
            
            if not can_regenerate:
                if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                    return JsonResponse({'error': message}, status=403)
                messages.error(request, message)
                return redirect('summary', file_id=file_id)
        except Exception as e:
            messages.error(request, "Error checking subscription limits")
            return redirect('summary', file_id=file_id)

        try:     
            print('start')       
            summary = generate_or_retrieve_summary(request, uploaded_file)
            print('done')
            
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                if isinstance(summary, str) and summary.startswith('Error'):
                    # If we got an error string back
                    print(f"Error during summary generation: {summary}")
                    return JsonResponse({'error': summary}, status=500)
                    
                return JsonResponse({
                    'summary': summary,
                    'success': True,
                    'timestamp': time.time()
                })
                
            return render(request, 'result/summary.html', {
                'summary': summary,
                'file': uploaded_file,
                'chat_history': []  # Reset chat history for regenerated summary
            })
            
        except Exception as e:
            print(f"Error during summary regeneration: {str(e)}")
            if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
                return JsonResponse({
                    'error': f"Failed to regenerate summary: {str(e)}"
                }, status=500)
            messages.error(request, f"Failed to regenerate summary: {str(e)}")
            return redirect('summary', file_id=file_id)

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
            return f"Error during processing: {str(e)}"    # Summary generation step
    try:
        # Get user's plan type
        try:
            user_subscription = user.usersubscription
            plan_type = user_subscription.plan.name
            print(f"User plan type: {plan_type}")
        except Exception as e:
            print(f"Error getting plan type: {e}")          # Define chunk size based on plan type
       
        chunk_size = 3500
        if len(extracted_text) > chunk_size:
            print(f"Text length {len(extracted_text)} exceeds {chunk_size} chars, splitting into chunks")
            chunks = split_text(extracted_text, max_chars=chunk_size)
            chunk_summaries = []
            
            # Calculate word limit per chunk based on total chunks
            word_limits = {
                'free': 300,
                'basic': 700,
                'pro': 1000
            }
            total_word_limit = word_limits.get(plan_type.lower(), 300)
            chunk_word_limit = total_word_limit // len(chunks)
            
            for i, chunk in enumerate(chunks, 1):
                print(f"Processing chunk {i} of {len(chunks)}")
                summary_chunk = generate_summary_with_gemini(chunk, plan_type)
                
                if summary_chunk.startswith('Error:'):
                    print(f"Error in chunk {i}: {summary_chunk}")
                    return summary_chunk
                    
                chunk_summaries.append(summary_chunk)
                time.sleep(1)  # Delay to avoid rate limits
            
            print(f"Generated {len(chunk_summaries)} chunk summaries")
            
            chunk_summaries = ' '.join(chunk_summaries)
            combined_summary = generate_summary_with_gemini(chunk_summaries, plan_type)
                
            if combined_summary.startswith('Error:'):
                print(f"Error combining summaries: {combined_summary}")
                return combined_summary
                
            summary = combined_summary
        else:
            summary = generate_summary_with_gemini(extracted_text, plan_type)
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
    """Process chat messages with Gemini"""    # Check chat message limits
    try:
        user_subscription = request.user.usersubscription
        can_chat, message = user_subscription.can_send_chat_message(uploaded_file.id)
        if not can_chat:
            return JsonResponse({'error': message}, status=403)
    except Exception as e:
        return JsonResponse({'error': 'Error checking chat limits'}, status=500)

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


def generate_mcqs_with_gemini(summary_text, num_questions, difficulty):
    """Generate multiple-choice questions dynamically based on the summary."""
    
    prompt = f"""
    Generate {num_questions} multiple-choice questions based on the following summary. 
    The questions should be {difficulty} level.
    Use Latex formulas **where necessary**.
    Use diagrams such as graphs, circuit diagrams etc **if necessary**.
    You can ask questions using related images using the html image tag.

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
    
    # Check quiz generation limits
    try:
        user_subscription = request.user.usersubscription
        can_generate, message = user_subscription.can_generate_quiz(file_id)
        if not can_generate:
            print('Cannot generate quiz')
            messages.error(request, message)
            return redirect('quiz_options', file_id=file_id)
    except Exception as e:
        print('Got error')
        messages.error(request, "Error checking quiz limits")
        return redirect('quiz_options', file_id=file_id)
    
    summary_instance = get_object_or_404(Summary, uploaded_file=uploaded_file)

    num_questions = int(request.GET.get("num_questions", 10))
    print(num_questions)
    if request.GET.get("difficulty") == '1':
        difficulty = "easy"
    elif request.GET.get("difficulty") == '3':
        difficulty = "hard"
    else:
        difficulty = "medium"

    print(difficulty)

    # Generate MCQs on the fly
    mcq_text = generate_mcqs_with_gemini(summary_instance.summary_text, num_questions, difficulty)
    mcqs = parse_mcq_response(mcq_text)
    random.shuffle(mcqs)

    Quiz.objects.create(user=request.user, file=uploaded_file)

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
    incorrect_count = len(mcqs) - correct_count

    return render(request, "result/quiz_result.html", {"mcqs":mcqs, 
                                                        "results": results, 
                                                        "score": score, 
                                                        "file": uploaded_file,
                                                        "correct_count": correct_count,
                                                        "incorrect_count": incorrect_count,})

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

            # Transcribe the audio using existing AssemblyAI function
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