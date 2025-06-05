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
from typing import Dict, Any
import logging
from pathlib import Path

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

class FileManager:
    """Handles file operations and directory management"""
    
    @staticmethod
    def ensure_directories_exist():
        """Create necessary directories if they don't exist"""
        STATIC_DIR.mkdir(exist_ok=True)
        TEMPLATES_DIR.mkdir(exist_ok=True)
        OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    
    @staticmethod
    def cleanup_output_folder():
        """Clean up all files and subfolders in the output directory"""
        try:
            for item in OUTPUT_DIR.glob("**/*"):
                if item.is_file() and not item.name.endswith('.json'):
                    item.unlink()
                elif item.is_dir():
                    shutil.rmtree(item)
            logger.info("Output directory cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning output directory: {e}")
    
    @staticmethod
    def cleanup_static_folder():
        """Clean up all files in the static directory except styles.css"""
        try:
            for item in STATIC_DIR.glob("*"):
                if item.is_file() and item.name != "styles.css":
                    item.unlink()
            logger.info("Static directory cleaned successfully")
        except Exception as e:
            logger.error(f"Error cleaning static directory: {e}")

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

# Create FastAPI app
app = FastAPI(
    title="Bubble Sheet Scanner API",
    description="API for processing bubble sheet images",
    version="1.0.0"
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

@app.on_event("startup")
async def startup_event():
    """Initialize directories on startup"""
    FileManager.ensure_directories_exist()

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
        
        # Validate the results
        if not BubbleSheetValidator.validate_results(results):
            logger.error("Invalid bubble sheet detected - not all questions have 4 bubbles")
            raise HTTPException(
                status_code=400,
                detail="Invalid bubble sheet detected. Please ensure your image has all bubbles clearly visible and try again."
            )
        
        # After processing, combine all images
        combine_images()
        
        # Check if combined image exists
        combined_image_path = STATIC_DIR / "combined_questions.jpg"
        if not combined_image_path.exists():
            return JSONResponse({
                "results": results,
                "error": "Failed to generate combined image"
            })
        
        # Prepare response data
        response_data = {
            "results": results,
            "combined_image": "/static/combined_questions.jpg"
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

if __name__ == "__main__":
    import uvicorn
    port = int(os.getenv("PORT", 8000))
    host = os.getenv("HOST", "0.0.0.0")
    uvicorn.run(app, host=host, port=port)