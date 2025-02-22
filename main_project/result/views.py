import os
import time
import requests
import pdfplumber
import pytesseract
from PIL import Image
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile
from sumy.parsers.plaintext import PlaintextParser
from sumy.nlp.tokenizers import Tokenizer
from sumy.summarizers.lex_rank import LexRankSummarizer
from sumy.summarizers.text_rank import TextRankSummarizer


def extract_text_from_pdf(pdf_path):
    """Extract text from a PDF using pdfplumber; fallback to OCR if needed."""
    text = ""
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
            else:
                # Fallback to OCR for scanned pages
                pil_image = page.to_image(resolution=300).original
                ocr_text = pytesseract.image_to_string(pil_image)
                text += ocr_text + "\n"
                
    return text.strip() if text else None

def extract_text_from_txt(txt_path):
    """Extract text from a TXT file."""
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def calculate_sentence_count(text):
    #Calculate the number of sentences based on the text length.
    text_length = len(text.split())

    if text_length < 500:
        return 3
    elif text_length < 2000:
        return int(text_length / 100)
    elif text_length < 5000:
        return int(text_length / 150)
    else:
        return 30

def sumy_summarize_text(text, sentence_count):
    if not text:
        return ["No meaningful text"]

    parser = PlaintextParser.from_string(text, Tokenizer("english"))
    summarizer = TextRankSummarizer()

    summary = summarizer(parser.document, sentence_count)
    return [str(sentence) for sentence in summary]

def format_summary(summary_sentences):
    #structure summary sentences in a more readable format.
    formatted_summary = ["# Key Points\n"]
    for sentence in summary_sentences:
        formatted_summary += sentence + "\n1"
    return formatted_summary

def summary_result(request, file_id):
    """
    Extract text from the uploaded file, summarize it, and render the results.
    """
    uploaded_file = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded_file.file.path
    try:
        if file_path.lower().endswith(".pdf"):
            extracted_text = extract_text_from_pdf(file_path)
        elif file_path.lower().endswith(".txt"):
            extracted_text = extract_text_from_txt(file_path)
        else:
            extracted_text = "Unsupported file type."
    
        if extracted_text and extracted_text != "Unsupported file type.":
            # Generate summary and format it
            sentence_count = calculate_sentence_count(extracted_text)
            summary_sentences = sumy_summarize_text(extracted_text, sentence_count)
            
            
    except Exception as e:
        formatted_summary = [{'type': 'error', 'content': f"Error generating summary: {str(e)}"}]
    
    return render(request, "result/summary.html", {
        "file": uploaded_file,
        "extracted_text": extracted_text,
        "summary": summary_sentences

    })
