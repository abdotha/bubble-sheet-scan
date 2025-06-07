from PIL import Image
import os
import math
import time
import shutil

def combine_images(output_dir='static'):
    try:
        # Directory containing the images
        image_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'output', 'results')
        print(f"Looking for images in directory: {image_dir}")
        
        if not os.path.exists(image_dir):
            print(f"Error: Image directory {image_dir} does not exist")
            return False
            
        # Get all question images
        image_files = [f for f in os.listdir(image_dir) if f.startswith('question_') and f.endswith('.jpg')]
        print(f"Found {len(image_files)} image files")
        
        if not image_files:
            print("No question images found to combine")
            return False
        
        # Create a dictionary to map question numbers to filenames
        question_map = {}
        for img_file in image_files:
            try:
                num = int(img_file.split('_')[1].split('.')[0])
                question_map[num] = img_file
            except (IndexError, ValueError) as e:
                print(f"Error parsing filename {img_file}: {e}")
                continue
        
        if not question_map:
            print("No valid question images found")
            return False
            
        print(f"Successfully mapped {len(question_map)} questions")
        
        # Calculate grid dimensions (3x15 grid for 45 images)
        grid_width = 3
        grid_height = 15
        
        # Get dimensions of first image to determine cell size
        first_image_path = os.path.join(image_dir, next(iter(question_map.values())))
        print(f"Using first image for dimensions: {first_image_path}")
        
        first_image = Image.open(first_image_path)
        cell_width, cell_height = first_image.size
        print(f"Cell dimensions: {cell_width}x{cell_height}")
        
        # Create a new blank image
        combined_image = Image.new('RGB', (cell_width * grid_width, cell_height * grid_height))
        print(f"Created combined image with dimensions: {cell_width * grid_width}x{cell_height * grid_height}")
        
        # Place each image in the grid with the specified ordering
        for row in range(grid_height):
            # First column: 31-45 (previously was 1-15)
            if row + 31 in question_map:
                img1_path = os.path.join(image_dir, question_map[row + 31])
                print(f"Processing image for question {row + 31}: {img1_path}")
                img1 = Image.open(img1_path)
                combined_image.paste(img1, (0 * cell_width, row * cell_height))
            
            # Second column: 16-30 (stays the same)
            if row + 16 in question_map:
                img2_path = os.path.join(image_dir, question_map[row + 16])
                print(f"Processing image for question {row + 16}: {img2_path}")
                img2 = Image.open(img2_path)
                combined_image.paste(img2, (1 * cell_width, row * cell_height))
            
            # Third column: 1-15 (previously was 31-45)
            if row + 1 in question_map:
                img3_path = os.path.join(image_dir, question_map[row + 1])
                print(f"Processing image for question {row + 1}: {img3_path}")
                img3 = Image.open(img3_path)
                combined_image.paste(img3, (2 * cell_width, row * cell_height))
        
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        print(f"Ensured output directory exists: {output_dir}")
        
        # Generate a unique filename with timestamp
        timestamp = int(time.time())
        combined_image_path = os.path.join(output_dir, f'combined_questions_{timestamp}.jpg')
        print(f"Generated unique filename: {combined_image_path}")
        
        # Save the new combined image
        combined_image.save(combined_image_path)
        print(f"Saved combined image to: {combined_image_path}")
        
        # Create a symlink or copy to the standard filename
        standard_path = os.path.join(output_dir, 'combined_questions.jpg')
        if os.path.exists(standard_path):
            os.remove(standard_path)
            print(f"Removed existing standard image: {standard_path}")
        
        # Copy the file instead of symlink for better compatibility
        shutil.copy2(combined_image_path, standard_path)
        print(f"Copied to standard path: {standard_path}")
        
        # Clean up old timestamped files (keep only the last 5)
        old_files = sorted([f for f in os.listdir(output_dir) if f.startswith('combined_questions_') and f.endswith('.jpg')])
        for old_file in old_files[:-5]:  # Keep the last 5 files
            try:
                os.remove(os.path.join(output_dir, old_file))
                print(f"Cleaned up old file: {old_file}")
            except Exception as e:
                print(f"Error removing old file {old_file}: {e}")
        
        return True
        
    except Exception as e:
        print(f"Error in combine_images: {str(e)}")
        import traceback
        print(traceback.format_exc())
        return False

if __name__ == '__main__':
    combine_images()