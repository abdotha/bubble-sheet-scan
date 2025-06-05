import os
import cv2
import numpy as np
from pathlib import Path
import json

def detect_bubbles(image):
    """
    Detect bubbles in the question image and determine which ones are selected
    Args:
        image: Input image containing bubbles
    Returns:
        selected_positions: List of positions of selected bubbles (0-3) or empty list if none selected
        confidence: List of confidence scores for each selection
    """
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply threshold to get binary image
    _, binary = cv2.threshold(gray, 0, 255, cv2.THRESH_BINARY_INV + cv2.THRESH_OTSU)
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    # Filter contours by area and circularity
    bubbles = []
    for contour in contours:
        area = cv2.contourArea(contour)
        perimeter = cv2.arcLength(contour, True)
        circularity = 4 * np.pi * area / (perimeter * perimeter) if perimeter > 0 else 0
        
        # Filter based on area and circularity
        if 100 < area < 1000 and circularity > 0.7:
            bubbles.append(contour)
    
    # Sort bubbles from left to right
    bubbles.sort(key=lambda c: cv2.boundingRect(c)[0])
    
    # Check which bubbles are filled
    selected_positions = []
    confidences = []
    fill_threshold = 0.3  # Threshold for considering a bubble filled
    
    for i, bubble in enumerate(bubbles):
        if i >= 4:  # Only process first 4 bubbles
            break
            
        # Create mask for this bubble
        mask = np.zeros_like(binary)
        cv2.drawContours(mask, [bubble], -1, 255, -1)
        
        # Calculate fill ratio
        bubble_area = cv2.contourArea(bubble)
        filled_area = cv2.countNonZero(cv2.bitwise_and(binary, mask))
        fill_ratio = filled_area / bubble_area
        
        if fill_ratio > fill_threshold:
            selected_positions.append(i)  # Position 0-3
            confidences.append(fill_ratio)
    
    return selected_positions, confidences

def get_adjusted_question_number(part, local_question_num):
    """
    Adjust question number based on the part
    Args:
        part: Part of the image (left, middle, right)
        local_question_num: Local question number (1-15)
    Returns:
        Adjusted question number
    """
    if part == 'left':
        return local_question_num + 30  # 31-45
    elif part == 'middle':
        return local_question_num + 15  # 16-30
    else:  # right
        return local_question_num  # 1-15

def evaluate_question_image(image_path, part):
    """
    Evaluate a single question image
    Args:
        image_path: Path to the question image
        part: Part of the image (left, middle, right)
    Returns:
        Dictionary containing question number and selected positions
    """
    # Read the image
    image = cv2.imread(str(image_path))
    if image is None:
        print(f"Error: Could not read image {image_path}")
        return None
    
    # Get local question number from filename
    local_question_num = int(Path(image_path).stem.split('_')[-1])
    
    # Get adjusted question number
    question_num = get_adjusted_question_number(part, local_question_num)
    
    # Detect selected bubbles
    selected_positions, confidences = detect_bubbles(image)
    
    # Filter out low confidence selections
    filtered_positions = []
    filtered_confidences = []
    for pos, conf in zip(selected_positions, confidences):
        if conf >= 0.6:
            filtered_positions.append(pos)
            filtered_confidences.append(conf)
    
    return {
        'question_number': question_num,
        'selected_positions': filtered_positions,
        'confidences': [float(conf) for conf in filtered_confidences]
    }

def process_all_questions(base_dir):
    """
    Process all questions in the given directory
    Args:
        base_dir: Base directory containing the processed images
    """
    results = {}
    
    # Get all folders in the processed directory
    processed_dir = os.path.join(base_dir, "processed")
    if not os.path.exists(processed_dir):
        print(f"Error: Processed directory not found at {processed_dir}")
        return
    
    folders = [f for f in os.listdir(processed_dir) if os.path.isdir(os.path.join(processed_dir, f))]
    
    for folder in folders:
        folder_path = os.path.join(processed_dir, folder)
        results[folder] = {}
        
        # Initialize list for all questions (1-45)
        all_questions = [None] * 45
        
        # Process each part (left, middle, right)
        for part in ['left', 'middle', 'right']:
            questions_dir = os.path.join(folder_path, "questions", part)
            if not os.path.exists(questions_dir):
                continue
            
            # Process each question image
            for img_file in sorted(os.listdir(questions_dir)):
                if img_file.startswith('question_') and img_file.endswith('.jpg'):
                    img_path = os.path.join(questions_dir, img_file)
                    result = evaluate_question_image(img_path, part)
                    if result:
                        # Store result in the correct position (question_number - 1 for 0-based index)
                        all_questions[result['question_number'] - 1] = {
                            'question_number': result['question_number'],
                            'selected_positions': result['selected_positions'],
                            'confidences': result['confidences']
                        }
        
        # Store the complete list of questions
        results[folder] = all_questions
    
    # Save results to JSON file
    output_file = os.path.join(base_dir, "evaluation_results.json")
    with open(output_file, 'w') as f:
        json.dump(results, f, indent=2)
    
    print(f"Evaluation results saved to {output_file}")
    
    # Print summary
    print("\nEvaluation Summary:")
    for folder in results:
        print(f"\n{folder}:")
        for question in results[folder]:
            if question is not None:
                positions_str = "None" if not question['selected_positions'] else str(question['selected_positions'])
                confidences_str = "None" if not question['confidences'] else [f"{conf:.2f}" for conf in question['confidences']]
                print(f"    Question {question['question_number']}: Positions {positions_str} (Confidences: {confidences_str})")

if __name__ == "__main__":
    # Specify the base directory containing the processed images
    base_directory = "cropped_images"  # Change this to your actual directory path
    
    # Process all questions
    process_all_questions(base_directory) 