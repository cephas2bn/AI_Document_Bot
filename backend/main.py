from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import os
import shutil
import pdfplumber
import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
from PIL import Image
from docx import Document
import pandas as pd

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Helper function to extract text from PDF
def extract_text_from_pdf(file_path):
    text = ""
    with pdfplumber.open(file_path) as pdf:
        for page in pdf.pages:
            text += page.extract_text() or ""
    return text

# Helper function to extract text from DOCX
def extract_text_from_docx(file_path):
    text = ""
    doc = Document(file_path)
    for para in doc.paragraphs:
        text += para.text + "\n"
    return text

# Helper function to extract text from CSV
def extract_text_from_csv(file_path):
    df = pd.read_csv(file_path)
    return df.to_string()

# Helper function to extract text from TXT
def extract_text_from_txt(file_path):
    with open(file_path, 'r') as f:
        text = f.read()
    return text

# Helper function to perform OCR on images
def extract_text_from_image(file_path):
    image = Image.open(file_path)
    text = pytesseract.image_to_string(image)
    return text

# Main function to handle document parsing based on file type
def parse_document(file_path, file_type):
    if file_type == "pdf":
        return extract_text_from_pdf(file_path)
    elif file_type == "docx":
        return extract_text_from_docx(file_path)
    elif file_type == "csv":
        return extract_text_from_csv(file_path)
    elif file_type == "txt":
        return extract_text_from_txt(file_path)
    elif file_type in ["jpg", "jpeg", "png"]:  # Image formats for OCR
        return extract_text_from_image(file_path)
    else:
        raise ValueError("Unsupported file type")

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    # Save the uploaded file to a temporary location
    file_location = f"uploaded_files/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())

    # Determine file type
    file_extension = file.filename.split(".")[-1].lower()
    try:
        extracted_text = parse_document(file_location, file_extension)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    # Clean up temporary file after parsing (optional)
    os.remove(file_location)

    # Return extracted text as a JSON response (for testing purposes)
    return {"extracted_text": extracted_text}

# Add existing endpoints like /question below if you have them

class QuestionRequest(BaseModel):
    question: str

@app.post("/question")
async def answer_question(request: QuestionRequest):
    # Placeholder for actual answer logic; for now, it returns a simulated answer
    return {"answer": f"Simulated answer to: {request.question}"}



from transformers import pipeline
from pydantic import BaseModel
from typing import Optional

# Initialize the question-answering model
qa_pipeline = pipeline("question-answering", model="distilbert-base-uncased-distilled-squad")

# Placeholder variable to store extracted text
stored_text = ""

# Update the /upload endpoint to store extracted text globally
@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    global stored_text  # Make it accessible to the /question endpoint
    file_location = f"uploaded_files/{file.filename}"
    with open(file_location, "wb") as f:
        f.write(await file.read())

    file_extension = file.filename.split(".")[-1].lower()
    try:
        extracted_text = parse_document(file_location, file_extension)
        stored_text = extracted_text  # Store extracted text for answering questions
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))

    os.remove(file_location)
    return {"extracted_text": extracted_text}

# Modify the /question endpoint to use the stored text
class QuestionRequest(BaseModel):
    question: str

@app.post("/question")
async def answer_question(request: QuestionRequest):
    if not stored_text:
        return {"answer": "No document uploaded or extracted text available."}

    # Use the QA pipeline to find an answer within the stored text
    try:
        result = qa_pipeline({
            "question": request.question,
            "context": stored_text
        })
        answer = result["answer"]
    except Exception as e:
        return {"answer": f"An error occurred while processing the question: {str(e)}"}

    return {"answer": answer}
