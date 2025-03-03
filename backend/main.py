from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, FileResponse
import os
import shutil
import whisper
from dotenv import load_dotenv
from langchain_sambanova import ChatSambaNovaCloud
from starlette.background import BackgroundTask
from langchain.prompts import ChatPromptTemplate
import asyncio
import markdown

load_dotenv()
os.environ["SAMBANOVA_API_KEY"] = os.getenv("SAMBANOVA_API_KEY")

app = FastAPI()

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173"],  # Replace with your frontend URL in production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Load Whisper model for transcription
whisper_model = whisper.load_model("base")

# Initialize SambaNova LLM
llm = ChatSambaNovaCloud(
    model="Llama-3.1-Tulu-3-405B",
    temperature=0.8,
    max_tokens=2048,
)

summary_data = {}  # Global variable to store the summary

# Define the medical report prompt
medical_report_prompt = ChatPromptTemplate.from_messages([
    (
        "system",
        """You are a professional medical assistant specializing in structuring medical reports.
Given a raw transcription of a clinical consultation, analyze and extract key medical insights.

### **Patient Summary Report**
#### **1. Patient Information:**
- Name (if mentioned):
- Age (if mentioned):
- Gender (if mentioned):
- Chief Complaint:

#### **2. Present Illness:**
- Symptoms:
- Duration:
- Aggravating/Relieving Factors:
- Relevant Medical History:

#### **3. Physical Examination (if discussed):**
- Vitals:
- Physical Findings:

#### **4. Diagnosis (if discussed):**
- Possible Conditions Considered:
- Suggested Diagnostic Tests:

#### **5. Treatment Plan:**
- Medications Prescribed:
- Lifestyle Recommendations:
- Follow-up Instructions:

#### **6. Additional Notes:**
- Other Observations:

---
If any information is missing in the transcription, explicitly state "**Not mentioned**".
Ensure the report is **concise, structured, and medically relevant**.
Maintain **professional medical language** while ensuring readability.

---
Transcription:
"{transcription}"
"""
    )
])

@app.post("/upload")
async def upload_audio(file: UploadFile = File(...)):
    """Handles uploaded audio files and returns a structured medical summary in Markdown format."""
    try:
        file_path = f"temp_{file.filename}"
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        # Transcribe the audio using Whisper
        transcription = whisper_model.transcribe(file_path)["text"]

        # Use SambaNova LLM to generate structured medical notes
        prompt = medical_report_prompt.format(transcription=transcription)
        response = llm.invoke(prompt)

        # Convert AIMessage to markdown-formatted text
        summary_text = response.content
        markdown_summary = f"# Medical Report\n\n{summary_text}"

        # Store the markdown-formatted summary
        global summary_data
        summary_data = {"Medical Report": markdown_summary}

        return JSONResponse(content={"summary": markdown_summary})
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")
    finally:
        if os.path.exists(file_path):
            os.remove(file_path)

@app.post("/record")
async def process_recorded_audio(audio: UploadFile = File(...)):
    """Handles recorded audio and returns a medical summary."""
    return await upload_audio(audio)  # Reuse logic


@app.get("/download_markdown")
async def download_markdown():
    if not summary_data:
        raise HTTPException(status_code=400, detail="No summary available. Please upload an audio file first.")

    md_filename = "medical_summary.md"

    try:
        with open(md_filename, "w", encoding="utf-8") as md_file:
            md_file.write(summary_data["Medical Report"])

        if not os.path.exists(md_filename):
            raise HTTPException(status_code=500, detail="Failed to generate Markdown file.")

        # Serve the file
        response = FileResponse(
            md_filename,
            media_type="text/markdown",
            filename=md_filename,
        )

        # Schedule file deletion after a delay
        async def delete_file():
            await asyncio.sleep(10)  # Wait for 10 seconds
            if os.path.exists(md_filename):
                os.remove(md_filename)

        asyncio.create_task(delete_file())

        return response
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error generating Markdown file: {str(e)}")

@app.get("/preview_markdown")
async def preview_markdown():
    """Returns the markdown content for preview."""
    if not summary_data:
        raise HTTPException(status_code=400, detail="No summary available. Please upload an audio file first.")

    return JSONResponse(content={"markdown": summary_data["Medical Report"]})

@app.get("/")
async def status():
    """Checks API status."""
    return {"message": "API is running!"}
