import os
import random
import re
import time
import requests
import fitz         # PyMuPDF for PDF extraction
import pytesseract  # For OCR fallback
from PIL import Image
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile, Summary
from transformers import AutoTokenizer
from django.utils.safestring import mark_safe
import google.generativeai as genai


# Set up Gemini API client
GEMINI_API_KEY = "AIzaSyBEH5_BKeu6wQsfWQz8lnN14xdqqQMuUtY"  
genai.configure(api_key=GEMINI_API_KEY)

generation_config = {
    "temperature": 0.7,  # Adjust creativity level
    "top_p": 0.9,
    "top_k": 50,
    "max_output_tokens": 5000,
}
# -------------------------------------------------------------------
# Helper Functions: Text Extraction using PyMuPDF
# -------------------------------------------------------------------
def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using PyMuPDF (fitz)."""
    text = ""
    doc = fitz.open(pdf_path)
    for page in doc:
        page_text = page.get_text("text")
        if page_text and page_text.strip():
            text += page_text + "\n"
        else:
            # Fallback to OCR for scanned pages
            pil_image = page.get_pixmap(dpi=300).pil_image()
            ocr_text = pytesseract.image_to_string(pil_image)
            text += ocr_text + "\n"
    return text.strip() if text else None

def extract_text_from_txt(txt_path):
    """Extract text from a TXT file."""
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def generate_summary_with_gemini(text):
    """Send extracted text to Gemini API and get structured summary."""

    
    model = genai.GenerativeModel("gemini-2.0-flash-lite")

    prompt = f"""
    You are an expert summarizer. 
    Summarize the following text in a **engaging and reader-friendly** with:
    - Use bold and clear **section headers** (like Introduction, Key Points, Conclusion).
    - Use **clear headings and bullet points**.
    - Keep it **concise yet informative**.
    - Include examples and explanations where needed.
    - Use appropriate emojis before a section header.
    - Ensure the summary is **professional, easy to scan and visually appealing**.
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

def summary_result(request, file_id):
    """Extracts text from the uploaded file and generates a structured summary."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    summary_instance = Summary.objects.filter(user=request.user, uploaded_file=uploaded_file).first()
    file_path = uploaded_file.file.path

    if summary_instance and "regenerate" not in request.GET:
        summary = summary_instance.summary_text
    else:
        if file_path.lower().endswith(".pdf"):
            extracted_text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(".txt"):
            extracted_text = extract_text_from_txt(file_path)
        else:
            extracted_text = "Unsupported file type."

        if extracted_text and extracted_text != "Unsupported file type.":
            if len(extracted_text) > 3000:
                summary = generate_long_summary(extracted_text)
            else:
                summary = generate_summary_with_gemini(extracted_text)
        else:
            summary = "No text could be extracted from the file."

        if summary_instance:
            summary_instance.summary_text = summary
            summary_instance.save()
        else:
            Summary.objects.create(user=request.user, uploaded_file=uploaded_file, summary_text=summary)

        if request.headers.get('X-Requested-With') == 'XMLHttpRequest':
            return JsonResponse({
                'success': True,
                'summary': summary,
                'timestamp': time.time()
            })
        return redirect('summary', file_id=file_id)
    

    return render(request, "result/summary.html", {
        "file": uploaded_file,
        "summary": summary,
    })

def generate_mcqs_with_gemini(summary_text, num_questions, difficulty):
    """Generate multiple-choice questions dynamically based on the summary."""

    model = genai.GenerativeModel("gemini-2.0-flash-lite")
    
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

def quiz_options(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)

    return render(request, "result/quiz_options.html", {"file": uploaded_file})

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

@csrf_exempt
def chat_with_summary(request, file_id):
    """Handles chatbot conversation based on the summary."""
    if request.method == "POST":
        data = json.loads(request.body)
        user_message = data.get("message", "").strip()

        if not user_message:
            return JsonResponse({"error": "Message cannot be empty"}, status=400)

        uploaded_file = UploadedFile.objects.filter(id=file_id, user=request.user).first()
        summary_instance = Summary.objects.filter(uploaded_file=uploaded_file).first()

        if not summary_instance:
            return JsonResponse({"error": "Summary not found"}, status=404)

        summary_text = summary_instance.summary_text

        # Prepare the chatbot prompt
        prompt = f"""
        You are an AI assistant helping users understand and discuss a summary. 
        The summary content is as follows:

        {summary_text}

        User's question: {user_message}

        Provide a helpful, structured answer based only on the summary above.
        """

        model = genai.GenerativeModel("gemini-2.0-flash-lite")
        response = model.generate_content(prompt)

        bot_response = response.text if response.text else "I'm sorry, I couldn't generate a response."

        return JsonResponse({"response": bot_response})

    return JsonResponse({"error": "Invalid request method"}, status=405)