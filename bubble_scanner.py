from image_croping import process_images
from image_processing import crop_into_thirds
from divide_questions import divide_image_into_questions
from bubble_detector import BubbleDetector
import cv2
import os
import json

def get_section_question_number(section, local_number):
    """Convert local question number to global question number based on section"""
    section_offsets = {
        'left': 30,    # Questions 31-45
        'middle': 15,  # Questions 16-30
        'right': 0     # Questions 1-15
    }
    return section_offsets[section] + local_number

def process_bubble_sheet(bubble_sheet_path, output_dir='output'):
    """
    Process a bubble sheet image through the complete workflow:
    1. Read and preprocess the image
    2. Detect and crop the black border
    3. Divide into thirds
    4. Process each section for questions
    5. Detect bubbles and analyze answers
    """
    # Create output directories
    temp_dir = os.path.join(output_dir, 'temp')
    results_dir = os.path.join(output_dir, 'results')
    os.makedirs(temp_dir, exist_ok=True)
    os.makedirs(results_dir, exist_ok=True)

    # Step 1: Read and preprocess the image
    print("Step 1: Reading and preprocessing image...")
    cropped_image = process_images(bubble_sheet_path)
    if cropped_image is None:
        print("Error: Failed to process image")
        return None

    # Step 2: Divide into thirds
    print("Step 2: Dividing image into thirds...")
    left_part, middle_part, right_part = crop_into_thirds(cropped_image)

    # Step 3: Process each section
    print("Step 3: Processing sections...")
    sections = {
        'right': right_part,    # Questions 1-15
        'middle': middle_part,  # Questions 16-30
        'left': left_part      # Questions 31-45
    }

    # Initialize bubble detector
    detector = BubbleDetector()
    all_answers = []  # Store all answers in a single list

    # Process each section
    for section_name, section_image in sections.items():
        print(f"\nProcessing {section_name} section...")
        
        # Create section output directory
        section_dir = os.path.join(temp_dir, f'bubble_sheet_{section_name}')
        os.makedirs(section_dir, exist_ok=True)
        
        # Divide section into questions
        divide_image_into_questions(section_image, section_dir)
        
        # Process each question in the section
        questions_dir = os.path.join(section_dir, "questions")
        
        # Check if questions directory exists
        if not os.path.exists(questions_dir):
            print(f"Error: Questions directory not found at {questions_dir}")
            continue
            
        # Get all question files (excluding _orig files)
        question_files = sorted([f for f in os.listdir(questions_dir) 
                               if f.startswith('question_') and not f.endswith('_orig.jpg')])
        
        print(f"Found {len(question_files)} questions in {section_name} section")
        
        for question_file in question_files:
            question_path = os.path.join(questions_dir, question_file)
            local_question_num = int(question_file.replace('question_', '').replace('.jpg', ''))
            global_question_num = get_section_question_number(section_name, local_question_num)
            
            print(f"\nProcessing Question {global_question_num}...")
            
            # Read and check the question image
            question_img = cv2.imread(question_path)
            if question_img is None:
                print(f"Error: Could not read question image {question_path}")
                continue
                
            print(f"Question image size: {question_img.shape}")
            
            # Process question with bubble detector
            result, bubbles, selected, rejected = detector.process(question_path)
            
            if result is None:
                print(f"Error: Failed to process question {global_question_num}")
                continue
                
            # Save processed image
            output_path = os.path.join(results_dir, f'question_{global_question_num}.jpg')
            cv2.imwrite(output_path, result)
            
            # Determine the answer (0,1,2,3)
            answer = None
            if selected and len(selected) > 0:
                # Filter out any indices >= 4
                valid_selected = [s for s in selected if s < 4]
                if valid_selected:
                    answer = valid_selected
                    print(f"Selected answers: {answer}")
                else:
                    print("No valid bubbles selected")
            else:
                print("No answer selected")
            
            # Store results
            question_result = {
                'question_number': global_question_num,
                'answer': answer,  # Will be None if no answer or invalid
                'fill_ratios': [b['fill_ratio'] for b in bubbles],
                'bubbles_detected': len(bubbles)
            }
            
            all_answers.append(question_result)
            
            print(f"Bubbles detected: {len(bubbles)}")
            print(f"Fill ratios: {[f'{r:.2f}' for r in question_result['fill_ratios']]}")

    # Sort all answers by question number
    all_answers.sort(key=lambda x: x['question_number'])

    # Create a dictionary with questions as keys
    results_dict = {}
    for q in all_answers:
        question_key = f"question_{q['question_number']}"
        results_dict[question_key] = {
            'answer': q['answer'],
            'fill_ratios': q['fill_ratios'],
            'bubbles_detected': q['bubbles_detected']
        }

    # Save detailed results as JSON
    json_path = os.path.join(results_dir, 'detailed_results.json')
    with open(json_path, 'w') as f:
        json.dump(results_dict, f, indent=2)

    # Save summary report
    summary_path = os.path.join(results_dir, 'summary.txt')
    with open(summary_path, 'w') as f:
        f.write("=== Bubble Sheet Evaluation Summary ===\n\n")
        
        # Write summary for each question
        for result in all_answers:
            question_num = result['question_number']
            answer = result['answer']
            answer_text = str(answer) if answer is not None else 'No Answer'
            
            f.write(f"Question {question_num}:\n")
            f.write(f"Answer: {answer_text}\n")
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

    print(f"\nProcessing complete. Results saved to {results_dir}")
    print(f"Detailed results: {json_path}")
    print(f"Summary report: {summary_path}")
    
    return results_dict

if __name__ == "__main__":
    bubble_sheet_path = r'input_images\sample_11.jpg'
    results = process_bubble_sheet(bubble_sheet_path)
