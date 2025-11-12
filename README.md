# CV Selector Pro

An AI-powered CV screening application built with Django that automates resume evaluation from email attachments using advanced language models.

## Features
- Fetches and categorizes CV attachments from unread emails
- Evaluates CVs against job requirements using Llama 3.7B LLM
- Provides 10-point scoring with detailed feedback
- Supports PDF and DOCX file formats
- Exports evaluation results with category breakdowns
- Web interface for viewing and downloading processed CVs

## Tech Stack
- Django
- llama3-70b-8192 (via Groq API)
- Python libraries: pdfplumber, python-docx, imaplib

## Prerequisites
- Python 3.8+
- Virtual environment
- Email account with IMAP access

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd CV-Selector
   ```

2. Activate virtual environment:
   ```bash
   # Windows
   .\venv\Scripts\activate
   ```

3. Install dependencies:
   ```bash
   pip install django openai pdfplumber python-docx python-dotenv
   ```

4. Run migrations:
   ```bash
   python manage.py migrate
   ```

5. Configure environment variables in `.env`:
   ```
   IMAP_HOST=your-imap-host
   EMAIL_USER=your-email@example.com
   EMAIL_PASS=your-password
   ```

## Usage

1. Start the server:
   ```bash
   python manage.py runserver
   ```

2. Access the application at `http://127.0.0.1:8000/`

3. Navigate to endpoints:
   - `/fetch-attachments/` - Fetch CVs from emails
   - `/cv-evaluation/` - View evaluation results

## License
MIT License