from flask import Flask, request, jsonify, send_file, render_template
import whisper
import os
from pydub import AudioSegment
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from transformers import pipeline, AutoTokenizer, AutoModelForSeq2SeqLM, AutoModel

AudioSegment.converter = "C:\ProgramData\chocolatey\bin\ffmpeg.exe"

app = Flask(__name__)

# Initialize Whisper model
whisper_model = whisper.load_model("base")

# Initialize medical summarization model
model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn")
tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
summarizer = pipeline("summarization", model=model, tokenizer=tokenizer)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/upload', methods=['POST'])
def upload_file():
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'})
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'})
    if file:
        filename = 'uploaded_audio.wav'
        file.save(filename)
        return process_audio(filename)

@app.route('/record', methods=['POST'])
def record_audio():
    if 'audio' not in request.files:
        return jsonify({'error': 'No audio data'})
    audio = request.files['audio']
    if audio:
        filename = 'recorded_audio.wav'
        audio.save(filename)
        return process_audio(filename)

def process_audio(filename):
    # Transcribe audio
    result = whisper_model.transcribe(filename)
    transcription = result["text"]

    # Generate summary
    summary = summarizer(transcription, max_length=150, min_length=50, do_sample=False)[0]['summary_text']

    # Generate structured summary
    structured_summary = generate_structured_summary(summary)

    # Generate PDF summary
    pdf_filename = 'summary.pdf'
    generate_pdf(structured_summary, pdf_filename)

    return jsonify({'summary': structured_summary, 'pdf': pdf_filename})

def generate_structured_summary(summary):
    # This is a simple implementation. In a real-world scenario, you'd use more sophisticated NLP techniques.
    return {
        'symptoms': 'Based on the conversation, the patient reported: ' + summary,
        'advice': 'The doctor recommends: Further examination needed.',
        'medication': 'No specific medication mentioned in the summary.',
        'additional_notes': ''
    }

def generate_pdf(summary, filename):
    c = canvas.Canvas(filename, pagesize=letter)
    width, height = letter
    c.drawString(100, height - 100, "Medical Conversation Summary")
    
    y = height - 120
    c.drawString(100, y, "Patient Details:")
    y -= 20
    c.drawString(120, y, "Name: _________________")
    y -= 15
    c.drawString(120, y, "Age: ____  Gender: ____")
    y -= 15
    c.drawString(120, y, "Medical Record Number: __________")
    
    y -= 30
    c.drawString(100, y, "Symptoms:")
    y -= 15
    for line in summary['symptoms'].split('\n'):
        c.drawString(120, y, line)
        y -= 15
    
    y -= 15
    c.drawString(100, y, "Doctor's Advice:")
    y -= 15
    c.drawString(120, y, summary['advice'])
    
    y -= 30
    c.drawString(100, y, "Medication and Dosage:")
    y -= 15
    c.drawString(120, y, summary['medication'])
    
    y -= 30
    c.drawString(100, y, "Additional Notes:")
    y -= 15
    c.rect(120, y - 100, 400, 100)  # Draw a box for additional notes
    
    c.save()

@app.route('/download_pdf')
def download_pdf():
    return send_file('summary.pdf', as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True)
