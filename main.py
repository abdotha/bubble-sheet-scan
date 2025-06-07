from fastapi import FastAPI, File, UploadFile, Request, HTTPException
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

@app.get("/", response_class=HTMLResponse)
async def home(request: Request):
    """Serve the main page"""
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/upload")
async def upload_file(file: UploadFile = File(...)):
    """Upload and process a bubble sheet image"""
    try:
        # Clean up directories before processing
        FileManager.cleanup_output_folder()
        FileManager.cleanup_static_folder()
        
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        filename = f"bubble_sheet_{timestamp}.jpg"
        file_path = OUTPUT_DIR / filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the image using bubble scanner
        results = process_bubble_sheet(str(file_path))
        
        if results is None:
            raise HTTPException(status_code=500, detail="Failed to process bubble sheet")
        
        # Check for questions with insufficient bubbles
        invalid_questions = []
        rejected_areas = []
        
        for question_key, data in results.items():
            if not question_key.startswith('question_'):
                continue
                
            if data['bubbles_detected'] != REQUIRED_BUBBLES_PER_QUESTION:
                question_number = question_key.split('_')[1]
                invalid_questions.append({
                    'question_number': question_number,
                    'bubbles_detected': data['bubbles_detected']
                })
                
                # Add rejected areas information if available
                if 'rejected_areas' in data:
                    for area in data['rejected_areas']:
                        rejected_areas.append({
                            'question_number': question_number,
                            'circularity': area.get('circularity', 0),
                            'area': area.get('area', 0),
                            'reason': area.get('reason', 'Unknown')
                        })
        
        # After processing, combine all images
        combine_images(output_dir=str(TEMP_DIR))
        
        # Check if combined image exists in temp
        combined_image_path = TEMP_DIR / "combined_questions.jpg"
        if not combined_image_path.exists():
            return JSONResponse({
                "results": results,
                "error": "Failed to generate combined image"
            })
        
        # Prepare response data
        response_data = {
            "results": results,
            "combined_image": "/output/combined_questions.jpg",
            "validation": {
                "has_errors": len(invalid_questions) > 0,
                "invalid_questions": invalid_questions,
                "total_questions": len([k for k in results.keys() if k.startswith('question_')]),
                "error_message": f"Questions {', '.join([q['question_number'] for q in invalid_questions])} have less than {REQUIRED_BUBBLES_PER_QUESTION} bubbles detected. Please ensure all bubbles are clearly visible." if invalid_questions else None
            },
            "rejected_areas": rejected_areas
        }
        
        # Save JSON response to file
        json_filename = f"results_{timestamp}.json"
        json_path = OUTPUT_DIR / json_filename
        with open(json_path, "w") as f:
            json.dump(response_data, f, indent=4)
        
        return JSONResponse(response_data)
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up output directory after processing
        FileManager.cleanup_output_folder()

@app.get("/evaluation", response_class=HTMLResponse)
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
async def evaluate_bubble_sheet(file: UploadFile = File(...)):
    """Evaluate a bubble sheet against stored model answers"""
    try:
        # Check if model answers file exists
        if not MODEL_ANSWERS_FILE.exists():
            raise HTTPException(
                status_code=400,
                detail="No model answers found. Please upload model answers first using /upload_model_answers endpoint."
            )
        
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
        
        # Clean up directories before processing
        FileManager.cleanup_output_folder()
        FileManager.cleanup_static_folder()
        
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        filename = f"bubble_sheet_{timestamp}.jpg"
        file_path = OUTPUT_DIR / filename
        
        # Save the uploaded file
        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Process the image using bubble scanner
        results = process_bubble_sheet(str(file_path), model_answers=model_answers.answers)
        
        if results is None:
            raise HTTPException(status_code=500, detail="Failed to process bubble sheet")
        
        # Log the results for debugging
        logger.info(f"Bubble sheet processing results: {json.dumps(results, indent=2)}")
        
        # Validate the results
        if not BubbleSheetValidator.validate_results(results):
            logger.error("Invalid bubble sheet detected - not all questions have 4 bubbles")
            raise HTTPException(
                status_code=400,
                detail="Invalid bubble sheet detected. Please ensure your image has all bubbles clearly visible and try again."
            )
        
        # After processing, combine all images
        combine_images(output_dir='output/temp')
        
        # Check if combined image exists
        combined_image_path = COMBINED_IMAGE_PATH
        if not combined_image_path.exists():
            return JSONResponse({
                "error": "Failed to generate combined image"
            })
        
        # Evaluate answers
        evaluation_results = []
        correct_count = 0
        
        # Log model answers for debugging
        logger.info(f"Model answers: {model_answers.model_dump()}")
        
        for i in range(model_answers.number_of_questions):
            question_key = f"question_{i+1}"
            try:
                if question_key not in results:
                    logger.warning(f"Question {i+1} not found in results")
                    student_answers = []
                else:
                    question_data = results[question_key]
                    if not isinstance(question_data, dict):
                        logger.warning(f"Invalid data format for question {i+1}: {question_data}")
                        student_answers = []
                    else:
                        # Use detected_answer for evaluation
                        detected = question_data.get('detected_answer')
                        student_answers = [detected] if detected is not None else []
                
                correct_answer = model_answers.answers[i]
                
                # Get the student's answer (first answer if multiple)
                student_answer = student_answers[0] if student_answers else None
                
                # Check if student selected multiple answers
                has_multiple_answers = len(student_answers) > 1
                
                # Mark as correct if:
                # 1. Student selected exactly one answer
                # 2. That answer matches the correct answer (both in 4-0 format)
                is_correct = not has_multiple_answers and student_answer == correct_answer
                
                if is_correct:
                    correct_count += 1
                
                # Format student answer for display
                if not student_answers:
                    student_answer_display = "No Answer"
                elif has_multiple_answers:
                    student_answer_display = f"Multiple: {student_answers}"  # Already in 4-0 format
                else:
                    student_answer_display = str(student_answer)  # Already in 4-0 format
                
                # Get fill ratios for debugging
                fill_ratios = question_data.get('fill_ratios', []) if isinstance(question_data, dict) else []
                
                evaluation_results.append({
                    "question": i + 1,
                    "student_answers": student_answers,
                    "student_answer_display": student_answer_display,
                    "correct_answer": correct_answer,
                    "is_correct": is_correct,
                    "has_multiple_answers": has_multiple_answers,
                    "fill_ratios": fill_ratios  # Add fill ratios for debugging
                })
                
                # Log each question evaluation for debugging
                logger.info(f"Question {i+1} evaluation: student={student_answers}, display={student_answer_display}, correct={correct_answer}, is_correct={is_correct}, multiple_answers={has_multiple_answers}, fill_ratios={fill_ratios}")
                
            except Exception as e:
                logger.error(f"Error evaluating question {i+1}: {e}")
                evaluation_results.append({
                    "question": i + 1,
                    "error": str(e),
                    "student_answers": [],
                    "student_answer_display": "Error",
                    "correct_answer": model_answers.answers[i],
                    "is_correct": False,
                    "has_multiple_answers": False,
                    "fill_ratios": []
                })
        
        # Calculate score
        score = (correct_count / model_answers.number_of_questions) * 100
        
        # Prepare response data
        response_data = {
            "evaluation_results": evaluation_results,
            "summary": {
                "total_questions": model_answers.number_of_questions,
                "correct_answers": correct_count,
                "score": score,
                "questions_with_multiple_answers": sum(1 for r in evaluation_results if r.get('has_multiple_answers', False))
            },
            "combined_image": "/output/combined_questions.jpg"
        }
        
        # Save JSON response to file
        json_filename = f"evaluation_{timestamp}.json"
        json_path = OUTPUT_DIR / json_filename
        with open(json_path, "w") as f:
            json.dump(response_data, f, indent=4)

        return JSONResponse(response_data)
        
    except HTTPException as he:
        # Re-raise HTTP exceptions
        raise he
    except Exception as e:
        logger.error(f"Error processing file: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    finally:
        # Clean up output directory after processing
        FileManager.cleanup_output_folder()

@app.post("/grade")
async def grade_bubble_sheet(file: UploadFile = File(...)):
    """
    Endpoint to grade a bubble sheet and return:
    - Processed/graded image (base64, with green/red circles)
    - JSON with student answers (0-3 or null)
    - Student score
    """
    import cv2
    import base64
    from io import BytesIO
    from PIL import Image

    # Check if model answers file exists
    if not MODEL_ANSWERS_FILE.exists():
        raise HTTPException(
            status_code=400,
            detail="No model answers found. Please upload model answers first using /upload_model_answers endpoint."
        )
    # Load model answers
    with open(MODEL_ANSWERS_FILE, "r") as f:
        model_answers = ModelAnswers(**json.load(f))

    # Save uploaded file to temp
    FileManager.cleanup_output_folder()
    FileManager.cleanup_static_folder()
    timestamp = int(time.time())
    filename = f"bubble_sheet_{timestamp}.jpg"
    file_path = OUTPUT_DIR / filename
    with open(file_path, "wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # Process the image using bubble scanner
    results = process_bubble_sheet(str(file_path), model_answers=model_answers.answers)
    if results is None:
        raise HTTPException(status_code=500, detail="Failed to process bubble sheet")

    # Prepare student answers and grading
    student_answers = []
    correct_count = 0
    multi_answers = []
    for i in range(model_answers.number_of_questions):
        question_key = f"question_{i+1}"
        qdata = results.get(question_key, {})
        detected_answers = qdata.get('detected_answers', [])
        # If more than one answer, mark as wrong
        if isinstance(detected_answers, list) and len(detected_answers) > 1:
            student_answers.append(detected_answers)
            multi_answers.append(i+1)
        elif isinstance(detected_answers, list) and len(detected_answers) == 1:
            ans = detected_answers[0]
            student_answers.append(ans)
            if ans == model_answers.answers[i]:
                correct_count += 1
        else:
            student_answers.append(None)

    # Draw on the combined image (from temp)
    combined_img_path = TEMP_DIR / "combined_questions.jpg"
    if not combined_img_path.exists():
        combine_images(output_dir=str(TEMP_DIR))
    pil_img = Image.open(str(combined_img_path)).convert("RGB")
    buffered = BytesIO()
    pil_img.save(buffered, format="JPEG")
    img_base64 = base64.b64encode(buffered.getvalue()).decode()

    return {
        "image_base64": img_base64,
        "student_answers": student_answers,
        "correct_answers": correct_count,
        "total_questions": model_answers.number_of_questions,
        "multi_answer_questions": multi_answers
    }

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