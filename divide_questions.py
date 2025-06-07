import os
import cv2
import numpy as np
from pathlib import Path

def create_cut_visualization(img, num_questions=15, overlap=2):
    """
    Create a visualization of where the image will be cut
    Args:
        img: Input image
        num_questions: Number of questions to divide the image into
        overlap: Number of pixels to overlap between sections
    Returns:
        Image with cut lines drawn
    """
    # Create a copy of the image for visualization
    vis_img = img.copy()
    height, width = img.shape[:2]
    section_height = height // num_questions
    
    # Define colors
    line_color = (0, 255, 0)  # Green for lines
    text_color = (0, 0, 255)  # Red for text
    overlap_color = (255, 255, 0)  # Yellow for overlap regions
    
    # Draw horizontal lines
    for i in range(1, num_questions):
        y = i * section_height
        cv2.line(vis_img, (0, y), (width, y), line_color, 2)
    
    # Add text labels
    for i in range(num_questions):
        y = i * section_height + section_height // 2
        cv2.putText(vis_img, f"Q{i+1}", (10, y), cv2.FONT_HERSHEY_SIMPLEX, 0.7, text_color, 2)
    
    # Draw overlap regions
    for i in range(1, num_questions):
        y = i * section_height
        # Draw overlap region in yellow
        cv2.rectangle(vis_img, (0, y-overlap), (width, y+overlap), overlap_color, 1)
    
    return vis_img

def divide_image_into_questions(img, output_base_dir, overlap=5):
    """
    Divide the image into individual question sections
    Args:
        img: Input image
        output_base_dir: Base directory for output
        overlap: Number of pixels to overlap between sections
    """
    num_questions = 15

    # Get image dimensions
    height, width = img.shape[:2]
    
    # Calculate the height of each question section
    section_height = height // num_questions
    
    # Create visualization of cuts
    vis_img = create_cut_visualization(img, num_questions, overlap)
    
    # Create visualization directory
    vis_dir = os.path.join(output_base_dir, "visualizations")
    os.makedirs(vis_dir, exist_ok=True)
    
    # Save visualization
    vis_path = os.path.join(vis_dir, "cut_lines.jpg")
    cv2.imwrite(vis_path, vis_img)
    
    # Create questions directory
    questions_dir = os.path.join(output_base_dir, "questions")
    os.makedirs(questions_dir, exist_ok=True)
    
    # Process each question section
    for i in range(num_questions):
        # Calculate the start and end y-coordinates for this section with overlap
        start_y = max(0, i * section_height - overlap)
        end_y = min(height, (i + 1) * section_height + overlap)
        
        # Extract the section
        section = img[start_y:end_y, :]
        
        # Save the section directly without any processing
        output_path = os.path.join(questions_dir, f"question_{i+1}.jpg")
        cv2.imwrite(output_path, section)

def process_all_parts(base_dir):
    """
    Process all parts (left, middle, right) in the given directory
    Args:
        base_dir: Base directory containing the image folders
    """
    # Get all folders in the base directory
    folders = [f for f in os.listdir(base_dir) if os.path.isdir(os.path.join(base_dir, f))]
    
    for folder in folders:
        folder_path = os.path.join(base_dir, folder)
        
        # Create output directory for this image
        output_dir = os.path.join(base_dir, "processed", folder)
        os.makedirs(output_dir, exist_ok=True)
        
        # Process each part (left, middle, right)
        for part in ['left', 'middle', 'right']:
            part_path = os.path.join(folder_path, f"{part}.jpg")
            
            if os.path.exists(part_path):
                # Divide the image into questions
                divide_image_into_questions(part_path, output_dir)
                print(f"Processed {part} part of {folder}")

if __name__ == "__main__":
    # Specify the base directory containing the image folders
    base_directory = "cropped_images"  # Change this to your actual directory path
    
    # Process all parts
    process_all_parts(base_directory)
