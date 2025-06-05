import os
import cv2
from bubble_detector import BubbleDetector

def get_question_number(filename):
    """Extract question number from filename"""
    return int(filename.replace('question_', '').replace('.jpg', ''))

def get_section_question_number(section, file_number):
    """Convert file number to actual question number based on section"""
    if section == 'left':
        return file_number + 30  # 31-45
    elif section == 'middle':
        return file_number + 15  # 16-30
    else:  # right
        return file_number  # 1-15

def process_question(detector, image_path, question_number):
    """Process a single question image and return results"""
    result, bubbles, selected, rejected = detector.process(image_path)
    return {
        'question_number': question_number,
        'bubbles_detected': len(bubbles),
        'selected_bubbles': [i+1 for i in selected] if selected else ['null'],
        'fill_ratios': [b['fill_ratio'] for b in bubbles],
        'result_image': result
    }

def process_section(detector, section_dir, section):
    """Process all questions in a section directory (left/center/right)"""
    results = []
    if os.path.exists(section_dir):
        for file in sorted(os.listdir(section_dir), key=get_question_number):
            if file.startswith('question_') and file.endswith('.jpg'):
                file_number = get_question_number(file)
                question_number = get_section_question_number(section, file_number)
                image_path = os.path.join(section_dir, file)
                result = process_question(detector, image_path, question_number)
                results.append(result)
    return results

def process_sample(sample_dir):
    """Process all questions in a sample directory (left, middle, and right sections)"""
    detector = BubbleDetector()
    all_results = {
        'left': [],
        'middle': [],
        'right': []
    }
    
    # Process each section
    for section in ['left', 'middle', 'right']:
        section_dir = os.path.join(sample_dir, 'questions', section)
        all_results[section] = process_section(detector, section_dir, section)
    
    return all_results

def save_results(results, output_dir):
    """Save processed images and create a summary report"""
    os.makedirs(output_dir, exist_ok=True)
    
    # Create summary report
    report_path = os.path.join(output_dir, 'summary.txt')
    with open(report_path, 'w') as f:
        f.write("=== Bubble Detection Summary ===\n\n")
        
        # Combine all results and sort by question number
        all_questions = []
        for section in ['left', 'middle', 'right']:
            all_questions.extend(results[section])
        all_questions.sort(key=lambda x: x['question_number'])
        
        # Write summary for each question
        for result in all_questions:
            f.write(f"Question {result['question_number']}:\n")
            f.write(f"Selected bubbles: {result['selected_bubbles']}\n")
            f.write(f"Fill ratios: {[f'{r:.2f}' for r in result['fill_ratios']]}\n")
            f.write("\n")
        
        # Save processed images with just question numbers
        for result in all_questions:
            image_name = f"question_{result['question_number']}.jpg"
            output_path = os.path.join(output_dir, image_name)
            cv2.imwrite(output_path, result['result_image'])

def main():
    # Base directory containing all samples
    base_dir = "cropped_images/processed"
    
    # Process each sample
    for sample_dir in os.listdir(base_dir):
        if sample_dir.startswith('cropped_sample_'):
            print(f"\nProcessing {sample_dir}...")
            sample_path = os.path.join(base_dir, sample_dir)
            
            # Process the sample
            results = process_sample(sample_path)
            
            # Save results
            output_dir = os.path.join('results', sample_dir)
            save_results(results, output_dir)
            
            # Print summary
            total_questions = sum(len(results[section]) for section in ['left', 'middle', 'right'])
            print(f"Results saved to {output_dir}")
            print(f"Processed {total_questions} questions:")
            print(f"  Right (1-15): {len(results['right'])} questions")
            print(f"  Middle (16-30): {len(results['middle'])} questions")
            print(f"  Left (31-45): {len(results['left'])} questions")

if __name__ == "__main__":
    main()
