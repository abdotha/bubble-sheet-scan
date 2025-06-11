# Bubble Sheet Scanner

A FastAPI-based web application for scanning and processing bubble sheet answer sheets. This application can detect and process multiple-choice answer sheets, validate the responses, and provide visual feedback.

## Features

- Upload and process bubble sheet images
- Automatic bubble detection and validation
- Support for 45 questions (3 sections of 15 questions each)
- Multiple answer detection per question
- Visual feedback with combined question images
- RESTful API endpoints
- Web interface for easy interaction
- Support for multiple-choice questions (4 options per question)
- Answer key validation and grading
- Detailed analysis reports
- Docker support for easy deployment
- Google Cloud Run compatibility

## Prerequisites

- Python 3.8 or higher
- OpenCV
- Tesseract OCR
- Other dependencies listed in `requirements.txt`

## Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd bubble-sheet-scan
```

2. Create and activate a virtual environment:
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On Unix or MacOS
source venv/bin/activate
```

3. Install the required dependencies:
```bash
pip install -r requirements.txt
```

4. Install Tesseract OCR:
- Windows: Download and install from [Tesseract GitHub](https://github.com/UB-Mannheim/tesseract/wiki)
- Linux: `sudo apt-get install tesseract-ocr`
- MacOS: `brew install tesseract`

## Project Structure

```
bubble-sheet-scan/
├── main.py                 # FastAPI application entry point
├── bubble_scanner.py       # Core bubble sheet processing logic
├── bubble_detector.py      # Bubble detection algorithms
├── image_processing.py     # Image processing utilities
├── image_croping.py        # Image cropping functionality
├── combine_images.py       # Image combination utilities
├── divide_questions.py     # Question separation logic
├── evaluate_questions.py   # Question evaluation
├── evaluate_questions_bubble_detection.py  # Enhanced bubble detection evaluation
├── image_check.py         # Image validation utilities
├── static/                # Static files (CSS, images)
├── templates/             # HTML templates
├── input_images/         # Input image directory
├── output/               # Output directory for results
├── Dockerfile            # Docker configuration
├── cloudbuild.yaml       # Google Cloud Build configuration
└── requirements.txt      # Python dependencies
```

## Usage

1. Start the server:
```bash
python main.py
```

2. Open your web browser and navigate to `http://localhost:8000`

3. Upload a bubble sheet image through the web interface

4. The application will process the image and return:
   - Detected answers
   - Combined question images
   - Validation results
   - Detailed analysis report

## API Endpoints

- `GET /`: Web interface
- `POST /upload`: Upload and process bubble sheet image
- `POST /evaluate`: Evaluate bubble sheet with answer key
- `POST /grade`: Grade bubble sheet with provided answers
- `GET /evaluation`: Evaluation page
- `POST /upload_model_answers`: Upload answer key
- `GET /output/combined_questions.jpg`: Get combined question image

## Docker Deployment

1. Build the Docker image:
```bash
docker build -t bubble-sheet-scanner .
```

2. Run the container:
```bash
docker run -p 8000:8000 bubble-sheet-scanner
```

## Google Cloud Run Deployment

The application includes a `cloudbuild.yaml` configuration for easy deployment to Google Cloud Run. Follow these steps:

1. Enable required APIs in Google Cloud Console
2. Build and deploy using Cloud Build:
```bash
gcloud builds submit --config cloudbuild.yaml
```

## Dependencies

Major dependencies include:
- FastAPI: Web framework
- OpenCV: Image processing
- Tesseract: OCR capabilities
- NumPy: Numerical operations
- Pillow: Image handling
- scikit-image: Image processing utilities
- uvicorn: ASGI server
- python-multipart: File upload handling
- jinja2: Template engine

## Contributing

1. Fork the repository
2. Create a feature branch
3. Commit your changes
4. Push to the branch
5. Create a Pull Request

## License

[Add your license information here]

## Acknowledgments

- OpenCV community
- FastAPI framework
- Tesseract OCR
- Google Cloud Platform 