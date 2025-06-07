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
import base64
from io import BytesIO

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
OUTPUT_DIR = Path("/tmp") / "output" / "results"
TEMP_DIR = Path("/tmp") / "output" / "temp"
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
            logger.error("Empty results received")
            return False
            
        # Check if results is a dictionary
        if not isinstance(results, dict):
            logger.error(f"Invalid results type: {type(results)}")
            return False
            
        # Track questions with incorrect bubble counts
        invalid_questions = []
        
        # Check each question's data
        for question_key, data in results.items():
            if not question_key.startswith('question_'):
                continue
                
            # Check if bubbles_detected exists and equals 4
            if not isinstance(data, dict) or 'bubbles_detected' not in data:
                logger.error(f"Invalid data structure for {question_key}: {data}")
                invalid_questions.append(f"{question_key}: Invalid data structure")
                continue
                
            if data['bubbles_detected'] != REQUIRED_BUBBLES_PER_QUESTION:
                # Only consider it invalid if there's no clear answer
                if not data.get('answer'):
                    logger.warning(f"Invalid bubble count for {question_key}: {data['bubbles_detected']}")
                    invalid_questions.append(f"{question_key}: {data['bubbles_detected']} bubbles")
                
        # If we have invalid questions, log them all
        if invalid_questions:
            logger.error(f"Questions with incorrect bubble counts: {', '.join(invalid_questions)}")
            return False
                
        return True

class ModelAnswers(BaseModel):
    number_of_questions: int
    answers: List[int]

# Define model answers file path
MODEL_ANSWERS_FILE = OUTPUT_DIR / "model_answers.json"

class Base64Image(BaseModel):
    image: str  # base64 encoded image string

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
        logger.info(f"Received file upload: {file.filename}")
        
        # Verify file type
        if not file.content_type.startswith('image/'):
            logger.error(f"Invalid file type: {file.content_type}")
            raise HTTPException(status_code=400, detail="Only image files are allowed")
        
        # Clean up directories before processing
        try:
            FileManager.cleanup_output_folder()
            FileManager.cleanup_static_folder()
            logger.info("Directories cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning directories: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error preparing directories: {str(e)}")
        
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        filename = f"bubble_sheet_{timestamp}.jpg"
        file_path = OUTPUT_DIR / filename
        
        logger.info(f"Attempting to save file to: {file_path}")
        logger.info(f"Directory exists: {OUTPUT_DIR.exists()}")
        logger.info(f"Directory permissions: {oct(OUTPUT_DIR.stat().st_mode)[-3:]}")
        
        # Save the uploaded file
        try:
            with open(file_path, "wb") as buffer:
                content = await file.read()
                if not content:
                    raise ValueError("Empty file received")
                buffer.write(content)
            logger.info("File saved successfully")
        except Exception as e:
            logger.error(f"Error saving file: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error saving file: {str(e)}")
        
        # Process the image using bubble scanner
        logger.info("Starting bubble sheet processing")
        try:
            results = process_bubble_sheet(str(file_path))
            logger.info("Bubble sheet processing completed")
            logger.info(f"Processing results: {json.dumps(results, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing bubble sheet: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
        
        if results is None:
            logger.error("Failed to process bubble sheet - results is None")
            raise HTTPException(status_code=500, detail="Failed to process bubble sheet")
        
        # Validate the results
        if not BubbleSheetValidator.validate_results(results):
            logger.error("Invalid bubble sheet detected - not all questions have 4 bubbles")
            # Instead of raising an error, return the results with a warning
            return JSONResponse({
                "results": results,
                "warning": "Some questions may have incorrect bubble detection. Please verify the results.",
                "combined_image": "/tmp/output/temp/combined_questions.jpg"
            })
        
        # After processing, combine all images
        logger.info("Starting image combination")
        try:
            if not combine_images():
                logger.error("Failed to combine images")
                raise HTTPException(status_code=500, detail="Failed to generate combined image")
            logger.info("Image combination completed")
        except Exception as e:
            logger.error(f"Error combining images: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error combining images: {str(e)}")
        
        # Check if combined image exists
        combined_image_path = TEMP_DIR / "combined_questions.jpg"
        if not combined_image_path.exists():
            logger.error(f"Combined image not found at: {combined_image_path}")
            raise HTTPException(status_code=500, detail="Combined image not found")
        
        # Return the results and the path to the combined image
        return JSONResponse({
            "results": results,
            "combined_image": "/tmp/output/temp/combined_questions.jpg"
        })
    except Exception as e:
        logger.error(f"Error processing file: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error processing file: {str(e)}")

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
        # logger.info(f"Bubble sheet processing results: {json.dumps(results, indent=2)}")
        
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
                        student_answers = question_data.get('answer', [])
                        if student_answers is None:
                            student_answers = []
                
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
            "combined_image": "/tmp/output/temp/combined_questions.jpg"
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

@app.get("/output/combined_questions.jpg")
def get_combined_image():
    """Serve the combined image"""
    combined_image_path = TEMP_DIR / "combined_questions.jpg"
    if not combined_image_path.exists():
        raise HTTPException(status_code=404, detail="Combined image not found")
    return FileResponse(combined_image_path)

@app.post("/upload_base64")
async def upload_base64_image(image_data: Base64Image):
    """Upload and process a base64 encoded bubble sheet image"""
    try:
        logger.info("Received base64 image upload")
        
        # Clean up directories before processing
        try:
            FileManager.cleanup_output_folder()
            FileManager.cleanup_static_folder()
            logger.info("Directories cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning directories: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error preparing directories: {str(e)}")
        
        # Generate unique filename with timestamp
        timestamp = int(time.time())
        filename = f"bubble_sheet_{timestamp}.jpg"
        file_path = OUTPUT_DIR / filename
        
        logger.info(f"Attempting to save file to: {file_path}")
        logger.info(f"Directory exists: {OUTPUT_DIR.exists()}")
        logger.info(f"Directory permissions: {oct(OUTPUT_DIR.stat().st_mode)[-3:]}")
        
        # Decode and save the base64 image
        try:
            # Remove the data URL prefix if present
            if ',' in image_data.image:
                image_data.image = image_data.image.split(',')[1]
            
            # Decode base64 image
            image_bytes = base64.b64decode(image_data.image)
            
            # Save the image
            with open(file_path, "wb") as buffer:
                buffer.write(image_bytes)
            logger.info("File saved successfully")
        except Exception as e:
            logger.error(f"Error saving base64 image: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error saving image: {str(e)}")
        
        # Process the image using bubble scanner
        logger.info("Starting bubble sheet processing")
        try:
            results = process_bubble_sheet(str(file_path))
            logger.info("Bubble sheet processing completed")
            logger.info(f"Processing results: {json.dumps(results, indent=2)}")
        except Exception as e:
            logger.error(f"Error processing bubble sheet: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error processing image: {str(e)}")
        
        if results is None:
            logger.error("Failed to process bubble sheet - results is None")
            raise HTTPException(status_code=500, detail="Failed to process bubble sheet")
        
        # Validate the results
        validation_result = BubbleSheetValidator.validate_results(results)
        
        # After processing, combine all images
        logger.info("Starting image combination")
        try:
            combine_images()
            logger.info("Image combination completed")
        except Exception as e:
            logger.error(f"Error combining images: {str(e)}")
            raise HTTPException(status_code=500, detail=f"Error combining images: {str(e)}")
        
        # Check if combined image exists
        combined_image_path = TEMP_DIR / "combined_questions.jpg"
        if not combined_image_path.exists():
            logger.error(f"Combined image not found at: {combined_image_path}")
            return JSONResponse({
                "results": results,
                "error": "Failed to generate combined image"
            })
        
        logger.info("Processing completed successfully")
        
        # Prepare response data with timestamp to prevent caching
        response_data = {
            "results": results,
            "combined_image": f"/tmp/output/temp/combined_questions.jpg?t={timestamp}",
            "timestamp": timestamp
        }
        
        # Only add warning if validation failed
        if not validation_result:
            response_data["warning"] = "Some questions may have incorrect bubble detection. Please verify the results."
        
        return JSONResponse(response_data)
        
    except HTTPException as he:
        logger.error(f"HTTP Exception: {str(he)}")
        raise he
    except Exception as e:
        logger.error(f"Unexpected error in upload_base64_image: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)