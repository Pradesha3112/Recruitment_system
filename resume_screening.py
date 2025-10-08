import docx2txt
import pdfplumber
from io import BytesIO

def extract_text(file):
    text = ""
    filename = file.filename.lower()
    
    if filename.endswith(".pdf"):
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                if page.extract_text():
                    text += page.extract_text() + " "
    elif filename.endswith(".docx"):
        # docx2txt only works with file paths, so save temporarily in memory
        temp_path = f"temp_{file.filename}"
        file.save(temp_path)
        text = docx2txt.process(temp_path)
        import os
        os.remove(temp_path)
    return text

def calculate_score(job_desc, resume_text):
    job_keywords = set(job_desc.lower().split())
    resume_words = set(resume_text.lower().split())
    score = len(job_keywords & resume_words) / (len(job_keywords) + 1e-5) * 100
    return round(score, 2)

def screen_resumes_from_list(job_desc, resume_files):
    all_scores = []
    for f in resume_files:
        text = extract_text(f)
        score = calculate_score(job_desc, text)
        all_scores.append({"file": f.filename, "score": score})
    all_scores.sort(key=lambda x: x['score'], reverse=True)
    best_resume = all_scores[0] if all_scores else None
    return best_resume, all_scores
