from PIL import Image
import os
import math
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def combine_images(output_dir='/tmp/output/temp'):
    try:
        # Directory containing the images
        image_dir = '/tmp/output/results'
        
        logger.info(f"Looking for images in: {image_dir}")
        
        # Get all question images
        image_files = [f for f in os.listdir(image_dir) if f.startswith('question_') and f.endswith('.jpg')]
        
        if not image_files:
            logger.error("No question images found to combine")
            return False
        
        logger.info(f"Found {len(image_files)} question images")
        
        # Create a dictionary to map question numbers to filenames
        question_map = {}
        for img_file in image_files:
            try:
                num = int(img_file.split('_')[1].split('.')[0])
                question_map[num] = img_file
            except (IndexError, ValueError):
                logger.warning(f"Invalid image filename format: {img_file}")
                continue
        
        if not question_map:
            logger.error("No valid question images found")
            return False
        
        # Calculate grid dimensions (3x15 grid for 45 images)
        grid_width = 3
        grid_height = 15
        
        # Get dimensions of first image to determine cell size
        first_image_path = os.path.join(image_dir, next(iter(question_map.values())))
        first_image = Image.open(first_image_path)
        cell_width, cell_height = first_image.size
        
        # Create a new blank image
        combined_image = Image.new('RGB', (cell_width * grid_width, cell_height * grid_height))
        
        # Place each image in the grid with the specified ordering
        for row in range(grid_height):
            # First column: 31-45
            if row + 31 in question_map:
                img1 = Image.open(os.path.join(image_dir, question_map[row + 31]))
                combined_image.paste(img1, (0 * cell_width, row * cell_height))
            
            # Second column: 16-30
            if row + 16 in question_map:
                img2 = Image.open(os.path.join(image_dir, question_map[row + 16]))
                combined_image.paste(img2, (1 * cell_width, row * cell_height))
            
            # Third column: 1-15
            if row + 1 in question_map:
                img3 = Image.open(os.path.join(image_dir, question_map[row + 1]))
                combined_image.paste(img3, (2 * cell_width, row * cell_height))
        
        # Ensure output directory exists
        os.makedirs(output_dir, exist_ok=True)
        
        # Save the combined image
        combined_image_path = os.path.join(output_dir, 'combined_questions.jpg')
        combined_image.save(combined_image_path)
        logger.info(f"Images combined successfully into '{combined_image_path}'")
        
        # Verify the file was created
        if not os.path.exists(combined_image_path):
            logger.error(f"Failed to save combined image at: {combined_image_path}")
            return False
            
        return True
        
    except Exception as e:
        logger.error(f"Error combining images: {str(e)}")
        return False

if __name__ == '__main__':
    combine_images() 