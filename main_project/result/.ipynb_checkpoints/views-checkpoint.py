# uploads/views.py

import os
import time
import re
import requests
import pdfplumber
import pytesseract
from PIL import Image
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile
from transformers import AutoTokenizer

# ----------------------------
# Hugging Face API Configuration
# ----------------------------
# For summarization, we use google/flan-t5-small.
SUMMARIZATION_MODEL_ENDPOINT = "https://api-inference.huggingface.co/models/google/flan-t5-small"
# For MCQ generation, we use valhalla/t5-small-qg-hl.
MCQ_MODEL_ENDPOINT = "https://api-inference.huggingface.co/models/valhalla/t5-small-qg-hl"

# Retrieve the API token (here hardcoded for testing; use environment variable in production)
HUGGINGFACE_API_TOKEN = os.environ.get("HUGGINGFACE_API_TOKEN", "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")
HEADERS_SUMMARIZATION = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}
HEADERS_MCQ = {"Authorization": f"Bearer {HUGGINGFACE_API_TOKEN}"}

# Load a tokenizer for truncation (we use the summarization model's tokenizer)
tokenizer = AutoTokenizer.from_pretrained("google/flan-t5-small")

# ----------------------------
# Helper Functions: Text Extraction
# ----------------------------
def extract_text_from_pdf(pdf_path):
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
            else:
                # Fallback to OCR
                pil_image = page.to_image(resolution=300).original
                ocr_text = pytesseract.image_to_string(pil_image)
                text += ocr_text + "\n"
    return text.strip() if text else None

def extract_text_from_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

# ----------------------------
# Helper Function: Truncation
# ----------------------------
def truncate_text(text, max_tokens=1024):
    tokens = tokenizer.encode(text, truncation=True, max_length=max_tokens, add_special_tokens=True)
    return tokenizer.decode(tokens, skip_special_tokens=True)

# ----------------------------
# Summarization with Hugging Face Inference API
# ----------------------------
def generate_summary(text):
    """
    Generate a detailed, structured summary using OpenAI's ChatCompletion endpoint
    (via the Hugging Face Inference API) with the Flan-T5-small model.
    """
    truncated_text = truncate_text(text, max_tokens=1024)
    prompt = (
        "You are an expert summarizer. Please read the text below and create a detailed summary. "
        "Organize the summary into at least three sections. For each section, provide a header (start with '#') "
        "and list at least two key points as bullet points (start with '-').\n\n"
        "Text:\n"
        f"{truncated_text}\n\n"
        "Summary:"
    )
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": 400,  # Increase if needed for a longer summary
            "min_length": 150,  # Increase if you want more detail
            "do_sample": False
        }
    }
    response = requests.post(SUMMARIZATION_MODEL_ENDPOINT, headers=HEADERS_SUMMARIZATION, json=payload)
    if response.status_code == 200:
        output = response.json()
        print("Raw API Output:", output)  # Debug: check what the API is returning
        if isinstance(output, list) and output:
            if "generated_text" in output[0]:
                return output[0]["generated_text"]
            elif "summary_text" in output[0]:
                return output[0]["summary_text"]
        return "No summary available."
    else:
        return f"Error: {response.status_code} - {response.text}"

def split_text(text, max_chars=3000):
    """Split long text into chunks of max_chars characters."""
    return [text[i:i+max_chars] for i in range(0, len(text), max_chars)]

def generate_long_summary(text):
    """For very long texts, split into chunks, summarize each, then combine and summarize again."""
    chunks = split_text(text, max_chars=3000)
    chunk_summaries = []
    for chunk in chunks:
        summary_chunk = generate_summary(chunk)
        chunk_summaries.append(summary_chunk)
        time.sleep(1)  # delay to avoid rate limits
    combined_text = " ".join(chunk_summaries)
    final_summary = generate_summary(combined_text)
    return final_summary

# ----------------------------
# MCQ Generation with Hugging Face Inference API
# ----------------------------
def generate_mcqs(text, num_questions, difficulty):
    """Generate multiple-choice questions using the valhalla/t5-small-qg-hl model."""
    truncated_text = truncate_text(text, max_tokens=4000)
    prompt = (
        f"Generate {num_questions} multiple-choice questions at {difficulty} difficulty based on the following text.\n"
        "For each question, provide the question, four options labeled A), B), C), and D), "
        "and indicate the correct answer by writing 'Answer: <letter>'. Separate questions clearly.\n\n"
        f"Text:\n{truncated_text}\n\nQuestions:"
    )
    payload = {
        "inputs": prompt,
        "parameters": {
            "max_length": 1000,
            "min_length": 200,
            "do_sample": False
        }
    }
    response = requests.post(MCQ_MODEL_ENDPOINT, headers=HEADERS_MCQ, json=payload)
    if response.status_code == 200:
        output = response.json()
        if isinstance(output, list) and output:
            generated_text = output[0].get("generated_text") or output[0].get("summary_text")
            if generated_text:
                return parse_mcq_output(generated_text)
        return []
    else:
        print(f"MCQ API Error: {response.status_code} - {response.text}")
        return []

def parse_mcq_output(raw_text):
    """Parse raw MCQ output into a list of dictionaries containing questions, options, and the correct answer."""
    mcqs = []
    # Assume each question block starts with "Question:".
    blocks = re.split(r"Question:\s*", raw_text)
    for block in blocks:
        if not block.strip():
            continue
        parts = re.split(r"Options:", block)
        if len(parts) < 2:
            continue
        question_text = parts[0].strip()
        remainder = parts[1]
        opt_ans = re.split(r"Answer:", remainder)
        if len(opt_ans) < 2:
            continue
        options_text = opt_ans[0].strip()
        answer_text = opt_ans[1].strip()
        # Split options by semicolon or newline.
        options = re.split(r";|\n", options_text)
        options = [opt.strip() for opt in options if opt.strip()]
        if len(options) != 4:
            options = ["Option A", "Option B", "Option C", "Option D"]
        m = re.match(r"([A-D])", answer_text)
        correct_letter = m.group(1) if m else "A"
        mcqs.append({
            "question": question_text,
            "options": options,
            "correct_answer": correct_letter
        })
    return mcqs

# ----------------------------
# Django Views
# ----------------------------

def summary_result(request, file_id):
    """Extract text from uploaded file and generate a summary."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded_file.file.path
    if file_path.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)
        print(extracted_text)
    elif file_path.lower().endswith(".txt"):
        extracted_text = extract_text_from_txt(file_path)
    else:
        extracted_text = "Unsupported file type."
    
    if extracted_text and extracted_text != "Unsupported file type.":
        if len(extracted_text) > 3000:
            summary = generate_long_summary(extracted_text)
        else:
            summary = generate_summary(extracted_text)
    else:
        summary = "No text could be extracted from the file."
    
    return render(request, "result/summary.html", {
        "file": uploaded_file,
        "extracted_text": extracted_text,
        "summary": summary,
    })

def quiz_options(request, file_id):
    """Render quiz options form."""
    return render(request, "result/quiz_options.html", {"file_id": file_id})

def generate_quiz(request, file_id):
    """Generate MCQs from the extracted text and store quiz in session."""
    uploaded_file = get_object_or_404(UploadedFile, id=file_id)
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
        return redirect("quiz_display")
    else:
        return redirect("quiz_options", file_id=file_id)

def quiz_display(request):
    """Display generated quiz with radio buttons."""
    quiz = request.session.get("quiz")
    if not quiz:
        return redirect("upload")
    return render(request, "result/quiz.html", {"quiz": quiz})

def evaluate_quiz(request):
    """Evaluate quiz, calculate percentage score, and display results with color-coded feedback."""
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
