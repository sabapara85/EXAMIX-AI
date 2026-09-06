"""
EXAMIX AI - Backend (FastAPI) - Deploy-ready
"""

import os
import sys
import logging
import time
from typing import List, Optional

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from pydantic import BaseModel
from dotenv import load_dotenv

import ai_provider
import ocr_service
import demo_bank
import syllabus

# ---------- Resource path for PyInstaller & Render ----------
def resource_path(relative_path):
    """Get absolute path to resource, works for dev and for PyInstaller."""
    try:
        # PyInstaller creates a temp folder and stores path in _MEIPASS
        base_path = sys._MEIPASS
    except AttributeError:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------- Logging ----------
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

load_dotenv()

app = FastAPI(title="EXAMIX AI")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

MAX_FILE_SIZE_MB = 15
ALLOWED_EXTENSIONS = (".pdf", ".jpg", ".jpeg", ".png")

class GenerateRequest(BaseModel):
    concepts: List[str]
    question_type: str
    num_questions: int
    source_text: Optional[str] = None
    demo_mode: bool = False

# ---------- Favicon ----------
@app.get("/favicon.ico")
async def favicon():
    return FileResponse(resource_path("logo.ico"))

# ---------- Health ----------
@app.get("/api/health")
def health_check():
    ocr_ready = bool(os.getenv("GOOGLE_VISION_API_KEY", "").strip()) or bool(
        os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "").strip()
    )
    provider = os.getenv("AI_PROVIDER", "deepseek").strip().lower()
    if provider == "deepseek":
        ai_ready = bool(os.getenv("DEEPSEEK_API_KEY", "").strip())
    elif provider == "openai":
        ai_ready = bool(os.getenv("OPENAI_API_KEY", "").strip())
    else:
        ai_ready = False
    return {
        "ocr_ready": ocr_ready,
        "ai_ready": ai_ready,
        "ai_provider": provider,
        "fully_ready": ocr_ready and ai_ready,
    }

# ---------- Demo sample ----------
@app.get("/api/demo-sample")
def demo_sample():
    logger.info("Serving demo sample")
    return {
        "extracted_text": demo_bank.SAMPLE_PAPER_TEXT,
        "detected_concepts": demo_bank.DEMO_CONCEPTS,
        "all_concepts": syllabus.CBSE_CLASS_9_MATHS_SYLLABUS,
        "demo_mode": True,
    }

# ---------- Upload & Analyze ----------
@app.post("/api/upload-and-analyze")
async def upload_and_analyze(file: UploadFile = File(...)):
    start_time = time.time()
    logger.info(f"Received file: {file.filename} ({file.content_type})")

    filename = file.filename or ""
    if not filename.lower().endswith(ALLOWED_EXTENSIONS):
        logger.error(f"Unsupported file type: {filename}")
        raise HTTPException(status_code=400, detail="Unsupported file type.")

    file_bytes = await file.read()
    file_size_kb = len(file_bytes) / 1024
    logger.info(f"File size: {file_size_kb:.2f} KB")
    if len(file_bytes) > MAX_FILE_SIZE_MB * 1024 * 1024:
        logger.error(f"File too large: {len(file_bytes)} bytes")
        raise HTTPException(status_code=400, detail=f"File too large (max {MAX_FILE_SIZE_MB}MB).")

    # OCR
    logger.info("Starting OCR...")
    ocr_start = time.time()
    try:
        extracted_text = ocr_service.extract_text(file_bytes, filename)
        ocr_duration = time.time() - ocr_start
        logger.info(f"OCR completed in {ocr_duration:.2f}s. Extracted {len(extracted_text)} characters.")
    except ocr_service.OCRError as e:
        logger.error(f"OCR failed: {e}")
        raise HTTPException(status_code=503, detail=f"OCR unavailable ({e}). Try demo mode.")

    # Concept identification
    logger.info("Starting concept identification...")
    concept_start = time.time()
    try:
        detected_concepts = ai_provider.identify_concepts(
            extracted_text, syllabus.CBSE_CLASS_9_MATHS_SYLLABUS
        )
        concept_duration = time.time() - concept_start
        logger.info(f"Concept identification completed in {concept_duration:.2f}s. Concepts: {detected_concepts}")
    except ai_provider.AIProviderError as e:
        logger.error(f"AI concept detection failed: {e}")
        raise HTTPException(status_code=503, detail=f"AI concept detection unavailable ({e}). Try demo mode.")

    total_duration = time.time() - start_time
    logger.info(f"Upload+analyze total time: {total_duration:.2f}s")

    return {
        "extracted_text": extracted_text,
        "detected_concepts": detected_concepts,
        "all_concepts": syllabus.CBSE_CLASS_9_MATHS_SYLLABUS,
        "demo_mode": False,
    }

# ---------- Generate ----------
@app.post("/api/generate")
def generate_paper(req: GenerateRequest):
    start_time = time.time()
    logger.info(f"Generate request: concepts={req.concepts}, type={req.question_type}, num={req.num_questions}, demo={req.demo_mode}")

    if len(req.concepts) < 2:
        raise HTTPException(status_code=400, detail="Select at least 2 concepts.")
    if req.num_questions not in (5, 10, 15, 20):
        raise HTTPException(status_code=400, detail="Number must be 5, 10, 15, or 20.")
    if req.question_type not in ("MCQ", "Short Answer", "Long Answer", "Mixed"):
        raise HTTPException(status_code=400, detail="Invalid question type.")

    if req.demo_mode:
        logger.info("Using demo bank (explicit demo mode)")
        questions = demo_bank.generate_demo_paper(req.concepts, req.question_type, req.num_questions)
        logger.info(f"Demo generated {len(questions)} questions")
        return {"questions": questions, "demo_mode": True}

    # AI generation
    try:
        logger.info("Attempting batch AI generation...")
        ai_start = time.time()
        questions = ai_provider.generate_questions(req.concepts, req.question_type, req.num_questions)
        ai_duration = time.time() - ai_start
        logger.info(f"AI batch generated {len(questions)} questions in {ai_duration:.2f}s")
        return {"questions": questions, "demo_mode": False}
    except ai_provider.AIProviderError as e:
        logger.warning(f"Batch AI generation failed: {e}. Trying one-by-one...")
        try:
            single_questions = []
            single_start = time.time()
            for i in range(req.num_questions):
                logger.info(f"Generating question {i+1} of {req.num_questions} individually...")
                one = ai_provider.generate_questions(req.concepts, req.question_type, 1)
                single_questions.extend(one)
            single_duration = time.time() - single_start
            logger.info(f"One-by-one generated {len(single_questions)} questions in {single_duration:.2f}s")
            return {
                "questions": single_questions,
                "demo_mode": False,
                "notice": "Generated one question at a time due to batch failure."
            }
        except ai_provider.AIProviderError as e2:
            logger.warning(f"One-by-one also failed: {e2}. Trying demo bank fallback...")
            bank_concepts = set(demo_bank.QUESTION_BANK.keys())
            missing = [c for c in req.concepts if c not in bank_concepts]
            if missing:
                logger.error(f"Demo bank missing concepts: {missing}")
                raise HTTPException(
                    status_code=503,
                    detail=f"AI unavailable and demo bank lacks: {', '.join(missing)}. Please try again."
                )
            else:
                fallback_questions = demo_bank.generate_demo_paper(req.concepts, req.question_type, req.num_questions)
                if fallback_questions:
                    logger.info(f"Demo fallback generated {len(fallback_questions)} questions")
                    return {
                        "questions": fallback_questions,
                        "demo_mode": True,
                        "notice": "AI unavailable. Showing EXPO DEMO MODE paper."
                    }
                else:
                    raise HTTPException(status_code=503, detail="Demo bank could not generate questions.")

# ---------- Serve frontend ----------
FRONTEND_DIR = resource_path("frontend")

if os.path.isdir(FRONTEND_DIR):
    app.mount("/static", StaticFiles(directory=FRONTEND_DIR), name="static")
    @app.get("/")
    def serve_index():
        return FileResponse(os.path.join(FRONTEND_DIR, "index.html"))
else:
    logger.error(f"Frontend directory not found at {FRONTEND_DIR}")