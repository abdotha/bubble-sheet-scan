from fastapi import FastAPI, File, UploadFile, Request, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, JSONResponse, FileResponse
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
import os
import shutil
from combine_images import combine_images
import json
from bubble_scanner import process_bubble_sheet
import time
from typing import Dict, Any, List
import logging
from pathlib import Path
from pydantic import BaseModel
from contextlib import asynccontextmanager
import glob
import asyncio

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Constants
REQUIRED_BUBBLES_PER_QUESTION = 4

# Define base paths
BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"
OUTPUT_DIR = BASE_DIR / "output" / "results"
TEMP_DIR = BASE_DIR / "output" / "temp"
COMBINED_IMAGE_PATH = TEMP_DIR / "combined_questions.jpg"
PROCESSING_TIMEOUT = 300  # 5 minutes timeout

class FileManager:
    """Handles file operations and directory management"""
    
    @staticmethod
    def ensure_directories_exist():
        """Create necessary directories if they don't exist"""
        STATIC_DIR.mkdir(exist_ok=True)
        TEMPLATES_DIR.mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def cleanup_output_folder():
        """Clean up all files and subfolders in the output directory except .json files"""
        try:
            for item in OUTPUT_DIR.glob("**/*"):
                if item.is_file() and not item.name.endswith('.json'):
                    item.unlink()
                elif item.is_dir() and item != TEMP_DIR:
                    shutil.rmtree(item)
            logger.info("Output directory cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning output directory: {e}")
    
    @staticmethod
    def cleanup_static_folder():
        """Do not remove any files from the static directory anymore"""
        logger.info("Static directory cleanup skipped (no files removed)")

    @staticmethod
    def cleanup_temp_folder():
        """Remove all files from the output/temp directory"""
        try:
            temp_files = glob.glob(str(TEMP_DIR / '*'))
            for f in temp_files:
                if os.path.isfile(f):
                    os.remove(f)
            logger.info("Temp directory cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning temp directory: {e}")

class BubbleSheetValidator:
    """Handles validation of bubble sheet results"""
    
    @staticmethod
    def validate_results(results: Dict[str, Any]) -> bool:
        """
        Validate that all questions have exactly 4 detected bubbles
        Returns True if valid, False otherwise
        """
        if not results:
            return False
            
        # Check if results is a dictionary
        if not isinstance(results, dict):
            return False
            
        # Check each question's data
        for question_key, data in results.items():
            if not question_key.startswith('question_'):
                continue
                
            # Check if bubbles_detected exists and equals 4
            if not isinstance(data, dict) or 'bubbles_detected' not in data:
                return False
            if data['bubbles_detected'] != REQUIRED_BUBBLES_PER_QUESTION:
                logger.warning(f"Invalid bubble count for {question_key}: {data['bubbles_detected']}")
                return False
                
        return True

class ModelAnswers(BaseModel):
    number_of_questions: int
    answers: List[int]

# Define model answers file path
MODEL_ANSWERS_FILE = OUTPUT_DIR / "model_answers.json"

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for FastAPI application"""
    # Startup
    FileManager.ensure_directories_exist()
    yield
    # Shutdown
    FileManager.cleanup_output_folder()
    FileManager.cleanup_static_folder()

# Create FastAPI app
app = FastAPI(
    title="Bubble Sheet Scanner API",
    description="API for processing bubble sheet images",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files
app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

# Templates
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# Store processing status
processing_status = {}

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Upload and process a bubble sheet image"""
    try:
        # Generate unique ID for this processing job
        job_id = file_manager.generate_unique_id()
        processing_status[job_id] = {"status": "processing", "error": None, "result": None}
        
        # Save uploaded file
        file_path = file_manager.save_uploaded_file(file, job_id)
        
        # Process in background
        async def process_file():
            try:
                # Process the bubble sheet
                results = process_bubble_sheet(file_path, OUTPUT_DIR)
                
                if results is None:
                    processing_status[job_id] = {
                        "status": "error",
                        "error": "Failed to process bubble sheet",
                        "result": None
                    }
                    return
                
                # Validate results
                validator = BubbleSheetValidator()
                if not validator.validate_results(results):
                    processing_status[job_id] = {
                        "status": "error",
                        "error": "Invalid bubble sheet detected. Please ensure your image has all bubbles clearly visible and try again.",
                        "result": None
                    }
                    return
                
                # Combine images
                combined_image_path = combine_images(RESULTS_DIR)
                
                if combined_image_path:
                    # Update results with image path
                    for question_key in results:
                        results[question_key]['image'] = f"/static/{os.path.basename(combined_image_path)}"
                
                processing_status[job_id] = {
                    "status": "completed",
                    "error": None,
                    "result": results
                }
                
            except Exception as e:
                logger.error(f"Error processing file: {str(e)}")
                processing_status[job_id] = {
                    "status": "error",
                    "error": str(e),
                    "result": None
                }
            finally:
                # Cleanup after processing
                file_manager.cleanup_files(job_id)
        
        # Start background processing
        asyncio.create_task(process_file())
        
        # Return job ID immediately
        return JSONResponse({
            "job_id": job_id,
            "status": "processing",
            "message": "File upload successful. Processing started."
        })
        
    except Exception as e:
        logger.error(f"Error in upload_file: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/evaluate", response_class=HTMLResponse)
async def evaluation_page(request: Request):
    """Serve the evaluation page"""
    return templates.TemplateResponse("evaluation.html", {"request": request})

@app.post("/upload_model_answers")
async def upload_model_answers(model_answers: ModelAnswers):
    """Store model answers in a JSON file"""
    try:
        # Validate the model answers
        if len(model_answers.answers) != model_answers.number_of_questions:
            raise HTTPException(
                status_code=400,
                detail="Number of answers must match the number of questions"
            )
        
        # Save model answers to JSON file
        with open(MODEL_ANSWERS_FILE, "w") as f:
            json.dump(model_answers.model_dump(), f, indent=4)
        
        return JSONResponse({
            "message": "Model answers saved successfully",
            "number_of_questions": model_answers.number_of_questions,
            "file_path": str(MODEL_ANSWERS_FILE)
        })
    except Exception as e:
        logger.error(f"Error saving model answers: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/evaluate")
async def evaluate_bubble_sheet(file: UploadFile = File(...), background_tasks: BackgroundTasks = None):
    """Evaluate a bubble sheet against stored model answers"""
    try:
        # Generate unique ID for this processing job
        job_id = file_manager.generate_unique_id()
        processing_status[job_id] = {"status": "processing", "error": None, "result": None}
        
        # Load model answers from JSON file
        try:
            with open(MODEL_ANSWERS_FILE, "r") as f:
                model_answers = ModelAnswers(**json.load(f))
        except Exception as e:
            logger.error(f"Error loading model answers: {e}")
            raise HTTPException(
                status_code=500,
                detail="Error loading model answers. Please try uploading them again."
            )
        
        # Save uploaded file
        file_path = file_manager.save_uploaded_file(file, job_id)
        
        # Process in background
        async def process_evaluation():
            try:
                # Process the bubble sheet with model answers
                results = process_bubble_sheet(file_path, OUTPUT_DIR, model_answers.answers)
                
                if results is None:
                    processing_status[job_id] = {
                        "status": "error",
                        "error": "Failed to process bubble sheet",
                        "result": None
                    }
                    return
                
                # Validate results
                validator = BubbleSheetValidator()
                if not validator.validate_results(results):
                    processing_status[job_id] = {
                        "status": "error",
                        "error": "Invalid bubble sheet detected. Please ensure your image has all bubbles clearly visible and try again.",
                        "result": None
                    }
                    return
                
                # Calculate score
                total_questions = len(results)
                correct_answers = sum(1 for q in results.values() 
                                   if q.get('answer') is not None and 
                                   q.get('model_answer') is not None and 
                                   q['answer'] == q['model_answer'])
                
                score = correct_answers
                percentage = (correct_answers / total_questions) * 100 if total_questions > 0 else 0
                
                # Combine images
                combined_image_path = combine_images(RESULTS_DIR)
                
                if combined_image_path:
                    # Update results with image path
                    for question_key in results:
                        results[question_key]['image'] = f"/static/{os.path.basename(combined_image_path)}"
                
                processing_status[job_id] = {
                    "status": "completed",
                    "error": None,
                    "result": {
                        "results": results,
                        "score": score,
                        "total_questions": total_questions,
                        "percentage": percentage,
                        "combined_image": f"/static/{os.path.basename(combined_image_path)}" if combined_image_path else None
                    }
                }
                
            except Exception as e:
                logger.error(f"Error processing evaluation: {str(e)}")
                processing_status[job_id] = {
                    "status": "error",
                    "error": str(e),
                    "result": None
                }
            finally:
                # Cleanup after processing
                file_manager.cleanup_files(job_id)
        
        # Start background processing
        asyncio.create_task(process_evaluation())
        
        # Return job ID immediately
        return JSONResponse({
            "job_id": job_id,
            "status": "processing",
            "message": "File upload successful. Processing started."
        })
        
    except Exception as e:
        logger.error(f"Error in evaluate: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/status/{job_id}")
async def get_status(job_id: str):
    if job_id not in processing_status:
        raise HTTPException(status_code=404, detail="Job not found")
    
    status = processing_status[job_id]
    
    # If processing is complete or error, clean up the status after returning
    if status["status"] in ["completed", "error"]:
        result = status.copy()
        del processing_status[job_id]
        return result
    
    return status

@app.get("/output/combined_questions.jpg")
def get_combined_image():
    """Serve the combined questions image from the temp directory"""
    if not COMBINED_IMAGE_PATH.exists():
        raise HTTPException(status_code=404, detail="Combined image not found")
    return FileResponse(str(COMBINED_IMAGE_PATH), media_type="image/jpeg")

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)