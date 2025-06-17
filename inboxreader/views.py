import os
import imaplib
import email
import json
import pdfplumber
import docx
from email.header import decode_header
from django.http import HttpResponse
from django.conf import settings
from django.shortcuts import render
from openai import OpenAI



IMAP_HOST = os.getenv('IMAP_HOST')
EMAIL_USER = os.getenv('EMAIL_USER')
EMAIL_PASS = os.getenv('EMAIL_PASS')


BASE_SAVE_DIR = os.path.join(settings.BASE_DIR, 'attachments')
os.makedirs(BASE_SAVE_DIR, exist_ok=True)

CATEGORY_MAP = {
    'software': ['developer', 'engineer'],
    'marketing': ['marketing', 'sales'],
    'ui': ['ui', 'ux']
}

# ==== HELPERS ====
def decode_str(s):
    if not s:
        return ""
    decoded, charset = decode_header(s)[0]
    if isinstance(decoded, bytes):
        return decoded.decode(charset or 'utf-8', errors='ignore')
    return decoded

def categorize_subject(subject):
    subject_lower = subject.lower()
    for category, keywords in CATEGORY_MAP.items():
        if any(keyword in subject_lower for keyword in keywords):
            return category
    return 'others'

def save_attachment(part, filename, category):
    folder = os.path.join(BASE_SAVE_DIR, category)
    os.makedirs(folder, exist_ok=True)

    filepath = os.path.join(folder, filename)
    try:
        with open(filepath, 'wb') as f:
            f.write(part.get_payload(decode=True))
        return filepath
    except Exception as e:
        print(f"Failed to save {filename}: {e}")
        return None

# ==== MAIN VIEW ====
from datetime import datetime, timedelta
import email.utils

def fetch_attachments(request):
    saved_files = []

    try:
        mail = imaplib.IMAP4_SSL(IMAP_HOST)
        mail.login(EMAIL_USER, EMAIL_PASS)
        mail.select("inbox")

        status, messages = mail.search(None, 'ALL')
        if status != 'OK':
            return HttpResponse("Failed to retrieve emails.")

        email_ids = messages[0].split()
        if not email_ids:
            return HttpResponse("No emails found.")

        # Time window: last 10 minutes
        now = datetime.utcnow()
        ten_minutes_ago = now - timedelta(minutes=360)

        for eid in reversed(email_ids):  # reversed to get latest emails first
            status, msg_data = mail.fetch(eid, '(RFC822)')
            if status != 'OK':
                continue

            raw_email = msg_data[0][1]
            msg = email.message_from_bytes(raw_email)

            # Get email date
            msg_date_tuple = email.utils.parsedate_tz(msg.get("Date"))
            if not msg_date_tuple:
                continue
            msg_date = datetime.utcfromtimestamp(email.utils.mktime_tz(msg_date_tuple))
            if msg_date < ten_minutes_ago:
                continue  # Skip old emails

            # Extract body text
            body_found = False
            if msg.is_multipart():
                for part in msg.walk():
                    content_type = part.get_content_type()
                    if content_type == "text/plain" and "attachment" not in str(part.get("Content-Disposition")):
                        body = part.get_payload(decode=True).decode(errors='ignore')
                        if body.strip():
                            body_found = True
                            break
            else:
                body = msg.get_payload(decode=True).decode(errors='ignore')
                if body.strip():
                    body_found = True

            if not body_found:
                continue  # Skip if no email body

            subject = decode_str(msg.get('Subject'))
            category = categorize_subject(subject)

            for part in msg.walk():
                content_disposition = str(part.get("Content-Disposition"))
                if "attachment" in content_disposition:
                    filename = decode_str(part.get_filename())
                    if filename and filename.lower().endswith(('.pdf', '.doc', '.docx')):
                        filepath = save_attachment(part, filename, category)
                        if filepath:
                            saved_files.append(f"{category}/{filename}")

        mail.logout()

    except Exception as e:
        return HttpResponse(f"Error occurred: {e}")

    if saved_files:
        return HttpResponse(f"Saved files: {', '.join(saved_files)}")
    else:
        return HttpResponse("No valid attachments found in the last 10 minutes.")




# # ==== CV EVALUATION VIEW ====
client = OpenAI(
    api_key="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",
    base_url="https://api.groq.com/openai/v1"
)

ATTACHMENTS_DIR = os.path.join(settings.BASE_DIR, 'attachments')
JOB_DESCRIPTION_FILE = os.path.join(settings.BASE_DIR, 'job_requirements.pdf')


def extract_text_from_file(file_path):
    if file_path.endswith('.pdf'):
        with pdfplumber.open(file_path) as pdf:
            return "\n".join(page.extract_text() or "" for page in pdf.pages)
    elif file_path.endswith('.docx'):
        doc = docx.Document(file_path)
        return "\n".join(p.text for p in doc.paragraphs)
    return ""


def compare_cv_to_job(cv_text, job_text):
    prompt = f"""
You are a recruitment AI. Compare the following CV with the job description.

Give a score out of 10 and a brief explanation of how well the candidate matches.

If the CV mentions that the candidate studied at a preferred university, add 1 bonus point (but keep the total score within 10).

Preferred Universities include:
- University of Dhaka (DU)
- BUET
- Rajshahi University (RU)
- Chittagong University (CU)
- Jahangirnagar University (JU)
- Shahjalal University of Science and Technology (SUST)
- Mawlana Bhashani Science and Technology University (MBSTU)
- North South University (NSU)
- American International University-Bangladesh (AIUB)

Job Description:
{job_text}

CV:
{cv_text}

Respond only in JSON format like:
{{"score": 9, "feedback": "Strong match for Python, Django, and AI with relevant experience."}}
"""
    response = client.chat.completions.create(
        model="llama3-70b-8192",
        messages=[{"role": "user", "content": prompt}]
    )
    return json.loads(response.choices[0].message.content)


def evaluate_resumes(request):
    job_text = extract_text_from_file(JOB_DESCRIPTION_FILE)
    results = []
    category_counts = {}

    for root, dirs, files in os.walk(ATTACHMENTS_DIR):
        for filename in files:
            if filename.endswith(('.pdf', '.docx')):
                file_path = os.path.join(root, filename)
                
                # Get category from folder structure
                relative_path = os.path.relpath(file_path, ATTACHMENTS_DIR)
                category = relative_path.split(os.sep)[0] if os.sep in relative_path else 'others'
                
                # Count categories
                category_counts[category] = category_counts.get(category, 0) + 1
                
                try:
                    cv_text = extract_text_from_file(file_path)
                    result = compare_cv_to_job(cv_text, job_text)
                    results.append({
                        "filename": relative_path,
                        "score": result.get("score", "N/A"),
                        "feedback": result.get("feedback", "No feedback"),
                        "category": category
                    })
                except Exception as e:
                    results.append({
                        "filename": relative_path,
                        "score": "Error",
                        "feedback": f"Failed to process: {str(e)}",
                        "category": category
                    })

    # Calculate total CVs
    total_cvs = len(results)
    
    # Create evaluation summary
    evaluation_summary = {
        'total_cvs': total_cvs
    }

    context = {
        'results': results,
        'evaluation_summary': evaluation_summary,
        'category_counts': category_counts
    }

    return render(request, 'inboxreader/cv_evaluation.html', context)



# inboxreader/views.py
from django.http import FileResponse, HttpResponseNotFound
import os

def download_cv(request):
    file_path = request.GET.get('path')
    if not file_path:
        return HttpResponseNotFound("File not specified")
    
    absolute_path = os.path.join(ATTACHMENTS_DIR, file_path)
    if os.path.exists(absolute_path):
        response = FileResponse(open(absolute_path, 'rb'))
        response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
        return response
    return HttpResponseNotFound("File not found")

def view_cv(request):
    file_path = request.GET.get('path')
    if not file_path:
        return HttpResponseNotFound("File not specified")
    
    absolute_path = os.path.join(ATTACHMENTS_DIR, file_path)
    if os.path.exists(absolute_path):
        if file_path.endswith('.pdf'):
            return FileResponse(open(absolute_path, 'rb'), content_type='application/pdf')
        elif file_path.endswith('.docx'):
            # For DOCX, we'll just offer download since browsers can't display them inline
            response = FileResponse(open(absolute_path, 'rb'))
            response['Content-Disposition'] = f'attachment; filename="{os.path.basename(file_path)}"'
            return response
    return HttpResponseNotFound("File not found")