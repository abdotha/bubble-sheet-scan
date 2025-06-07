from image_croping import process_images
from image_processing import crop_into_thirds
from divide_questions import divide_image_into_questions
from bubble_detector import BubbleDetector
import cv2
import os
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def get_section_question_number(section, local_number):
    """Convert local question number to global question number based on section"""
    section_offsets = {
        'left': 30,    # Questions 31-45
        'middle': 15,  # Questions 16-30
        'right': 0     # Questions 1-15
    }
    return section_offsets[section] + local_number

def process_bubble_sheet(bubble_sheet_path, output_dir='/tmp/output', model_answers=None):
    """
    Process a bubble sheet image through the complete workflow:
    1. Read and preprocess the image
    2. Detect and crop the black border
    3. Divide into thirds
    4. Process each section for questions
    5. Detect bubbles and analyze answers
    
    Args:
        bubble_sheet_path: Path to the bubble sheet image
        output_dir: Directory to save output files
        model_answers: Optional list of model answers (1-based indices)
    """
    # Create output directories
    temp_dir = os.path.join(output_dir, 'temp')
    results_dir = os.path.join(output_dir, 'results')
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)
    
    logger.info(f"Created directories: {temp_dir} and {results_dir}")

    # Step 1: Read and preprocess the image
    logger.info("Step 1: Reading and preprocessing image...")
    cropped_image = process_images(bubble_sheet_path)
    if cropped_image is None:
        logger.error("Error: Failed to process image")
        return None

    # Step 2: Divide into thirds
    logger.info("Step 2: Dividing image into thirds...")
    left_part, middle_part, right_part = crop_into_thirds(cropped_image)

    # Step 3: Process each section
    logger.info("Step 3: Processing sections...")
    sections = {
        'right': right_part,    # Questions 1-15
        'middle': middle_part,  # Questions 16-30
        'left': left_part      # Questions 31-45
    }

    # Initialize bubble detector
    detector = BubbleDetector()
    all_answers = []

    # Process each section
    for section_name, section_image in sections.items():
        logger.info(f"\nProcessing {section_name} section...")
        
        # Create section output directory
        section_dir = os.path.join(temp_dir, f'bubble_sheet_{section_name}')
        os.makedirs(section_dir, exist_ok=True)
        
        # Divide section into questions
        divide_image_into_questions(section_image, section_dir)
        
        # Process each question in the section
        questions_dir = os.path.join(section_dir, "questions")
        
        # Check if questions directory exists
        if not os.path.exists(questions_dir):
            logger.error(f"Error: Questions directory not found at {questions_dir}")
            continue
            
        # Get all question files (excluding _orig files)
        question_files = sorted([f for f in os.listdir(questions_dir) 
                               if f.startswith('question_') and not f.endswith('_orig.jpg')])
        
        logger.info(f"Found {len(question_files)} questions in {section_name} section")
        
        for question_file in question_files:
            question_path = os.path.join(questions_dir, question_file)
            local_question_num = int(question_file.replace('question_', '').replace('.jpg', ''))
            global_question_num = get_section_question_number(section_name, local_question_num)
            
            # Read and check the question image
            question_img = cv2.imread(question_path)
            if question_img is None:
                logger.error(f"Error: Could not read question image {question_path}")
                continue
                
            # Get model answer for this question if available
            model_answer = None
            if model_answers is not None and 0 <= global_question_num - 1 < len(model_answers):
                model_answer = model_answers[global_question_num - 1]
            
            # Process question with bubble detector
            result, bubbles, selected, rejected = detector.process(question_path, model_answer)
            
            if result is None:
                logger.error(f"Error: Failed to process question {global_question_num}")
                continue
                
            # Save processed image
            output_path = os.path.join(results_dir, f'question_{global_question_num}.jpg')
            cv2.imwrite(output_path, result)
            logger.debug(f"Saved processed image to: {output_path}")
            
            # Determine the answer (0,1,2,3)
            answer = None
            if selected and len(selected) > 0:
                # Filter out any indices >= 4
                valid_selected = [s for s in selected if s < 4]
                if valid_selected:
                    answer = valid_selected
                else:
                    logger.warning(f"No valid bubbles selected for question {global_question_num}")
            else:
                logger.debug(f"No answer selected for question {global_question_num}")
            
            # Store results
            question_result = {
                'question_number': global_question_num,
                'answer': answer,  # Will be None if no answer or invalid
                'fill_ratios': [b['fill_ratio'] for b in bubbles],
                'bubbles_detected': len(bubbles),
                'model_answer': model_answer
            }
            
            all_answers.append(question_result)

    # Sort all answers by question number
    all_answers.sort(key=lambda x: x['question_number'])

    # Create a dictionary with questions as keys
    results_dict = {}
    for q in all_answers:
        question_key = f"question_{q['question_number']}"
        results_dict[question_key] = {
            'answer': q['answer'],
            'fill_ratios': q['fill_ratios'],
            'bubbles_detected': q['bubbles_detected'],
            'model_answer': q['model_answer']
        }

    # Save detailed results as JSON
    json_path = os.path.join(results_dir, 'detailed_results.json')
    with open(json_path, 'w') as f:
        json.dump(results_dict, f, indent=2)
    logger.info(f"Saved detailed results to: {json_path}")

    # Save summary report
    summary_path = os.path.join(results_dir, 'summary.txt')
    with open(summary_path, 'w') as f:
        f.write("=== Bubble Sheet Evaluation Summary ===\n\n")
        
        # Write summary for each question
        for result in all_answers:
            question_num = result['question_number']
            answer = result['answer']
            answer_text = str(answer) if answer is not None else 'No Answer'
            model_answer = result['model_answer']
            model_answer_text = f" (Model: {model_answer})" if model_answer is not None else ""
            
            f.write(f"Question {question_num}:\n")
            f.write(f"Answer: {answer_text}{model_answer_text}\n")
            f.write(f"Fill ratios: {[f'{r:.2f}' for r in result['fill_ratios']]}\n")
            f.write("\n")
        
        # Add section summaries
        f.write("\n=== Section Summaries ===\n")
        for section in ['right', 'middle', 'left']:
            section_answers = [r for r in all_answers 
                             if get_section_question_number(section, 1) <= r['question_number'] <= 
                                get_section_question_number(section, 15)]
            answered = sum(1 for r in section_answers if r['answer'] is not None)
            f.write(f"\n{section.upper()} Section (Questions {get_section_question_number(section, 1)}-{get_section_question_number(section, 15)}):\n")
            f.write(f"Questions answered: {answered}/15\n")
            f.write("Answers: " + ", ".join(str(r['answer']) if r['answer'] is not None else 'X' 
                                          for r in section_answers) + "\n")
    
    logger.info(f"Saved summary report to: {summary_path}")
    logger.info(f"Processing complete. Results saved to {results_dir}")
    
    return results_dict

if __name__ == "__main__":
    bubble_sheet_path = r'input_images\sample_11.jpg'
    results = process_bubble_sheet(bubble_sheet_path)
