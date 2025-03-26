import os
import re
import time
import requests
import fitz         # PyMuPDF for PDF extraction
import pytesseract  # For OCR fallback
from PIL import Image
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile
from transformers import AutoTokenizer
import google.generativeai as genai


# Set up Gemini API client
GEMINI_API_KEY = "AIzaSyBEH5_BKeu6wQsfWQz8lnN14xdqqQMuUtY"  
genai.configure(api_key=GEMINI_API_KEY)

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
    response = model.generate_content(prompt)

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
    file_path = uploaded_file.file.path
    if file_path.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)
        print(extracted_text)
    elif file_path.lower().endswith(".txt"):
        extracted_text = extract_text_from_txt(file_path)
        print(extracted_text)
    else:
        extracted_text = "Unsupported file type."

    if extracted_text and extracted_text != "Unsupported file type.":
        if len(extracted_text) > 3000:
            summary = generate_long_summary(extracted_text)
        else:
            summary = generate_summary_with_gemini(extracted_text)
    else:
        summary = "No text could be extracted from the file."
    
    
    return render(request, "result/summary.html", {
        "file": uploaded_file,
        "extracted_text": extracted_text,
        "summary": summary,
    })

def quiz_options(request, file_id):
    """Display a form for selecting quiz options (number of questions and difficulty)."""
    file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    
    return render(request, "result/quiz_options.html", {"file": file})

def generate_quiz(request, file_id):
    """Generate MCQs from the extracted text based on user-selected options and store quiz in session."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    file_path = uploaded_file.file.path
    if file_path.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)
    elif file_path.lower().endswith(".txt"):
        extracted_text = extract_text_from_txt(file_path)
    else:
        extracted_text = "Unsupported file type."
    
    if not extracted_text or extracted_text == "Unsupported file type.":
        return render(request, "result/quiz_error.html", {"error": "No text could be extracted."})
    
    if request.method == "POST":
        num_questions = int(request.POST.get("num_questions", 10))
        difficulty = request.POST.get("difficulty", "easy")
        mcqs = generate_mcqs(extracted_text, num_questions, difficulty)
        request.session["quiz"] = mcqs
        return redirect("quiz_display", file_id=uploaded_file.id)
    else:
        return redirect("quiz_options", {'file': uploaded_file})

def quiz_display(request, file_id):
    """Display the generated quiz with radio buttons for answer selection."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id, user=request.user)
    quiz = request.session.get("quiz")
    if not quiz:
        return redirect("summary", file_id=uploaded_file.id)
    return render(request, "result/quiz.html", {"quiz": quiz})

def evaluate_quiz(request):
    """Evaluate the submitted quiz, calculate score percentage, and render results with color-coded feedback."""
    quiz = request.session.get("quiz")
    if not quiz:
        return redirect("upload")
    total = len(quiz)
    correct_count = 0
    results = []
    for idx, question in enumerate(quiz):
        user_answer = request.POST.get(f"question_{idx}")
        is_correct = (user_answer == question.get("correct_answer"))
        if is_correct:
            correct_count += 1
        results.append({
            "question": question.get("question"),
            "options": question.get("options"),
            "correct_answer": question.get("correct_answer"),
            "user_answer": user_answer,
            "is_correct": is_correct,
        })
    score_percentage = (correct_count / total) * 100 if total > 0 else 0
    return render(request, "result/quiz_result.html", {
        "results": results,
        "score": score_percentage,
        "total": total,
        "correct": correct_count,
    })
