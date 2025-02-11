import os
import requests
import pdfplumber
import pytesseract
from PIL import Image
from django.shortcuts import render, get_object_or_404, redirect
from knowbite.models import UploadedFile

HUGGINGFACE_API_TOKEN = "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"
HUGGINGFACE_MODEL_ENDPOINT = "https://api-inference.huggingface.co/models/facebook/bart-large-cnn"
HEADERS = {"Authorization": f"Bearer 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"}

def extract_text_from_pdf(pdf_path):
    text = ""

    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text and page_text.strip():
                text += page_text + "\n"
            else:
                # use ocr if the pdf is a scanned pdf
                pil_image = page.to_image(resolution=300).original
                ocr_text = pytesseract.image_to_string(pil_image)
                text += ocr_text + "\n"

    return text.strip() if text else None

def extract_text_from_txt(txt_path):
    with open(txt_path, "r", encoding="utf-8") as f:
        return f.read().strip()

def summarize_text_hf(text):
    #using the hugging face api to summarize
    payload = {
        "inputs": text,
        "parameters": {
            "max_length": 150,
            "min_length": 40,
            "do_sample": False
        }
    }
    response = requests.post(HUGGINGFACE_MODEL_ENDPOINT, headers=HEADERS, json=payload)

    if response.status_code == 200:
        output = response.json()
        #the response is a list with a dictionary containing 'summarize_text'
        if isinstance(output, list) and output and 'summary_text' in output[0]:
            return output[0]['summary_text']
        else:
            return "No summary available."

    else:
        return f"Error: {response.status_code} - {response.text}"

def summary_result(request, file_id):
    uploaded_file = get_object_or_404(UploadedFile, id=file_id)
    file_path = uploaded_file.file.path

    #extract text based on file type
    if file_path.lower().endswith(".pdf"):
        extracted_text = extract_text_from_pdf(file_path)
    elif file_path.lower().endswith(".txt"):
        extracted_text = extract_text_from_txt(file_path)
    else:
        extracted_text = "Unsupported file type."

    #summarize the text if it is extracted
    if extracted_text and extracted_text != "Unsupported file type.":
        summary = summarize_text_hf(extracted_text)
    else:
        summary = "No text could be extracted from the file."
    
    context = {
        "file": uploaded_file,
        "extracted_text": extracted_text,
        "summary": summary
    }

    return render(request, "result/summary.html", context)