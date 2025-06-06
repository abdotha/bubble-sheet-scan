from PIL import Image
import os
import math

def combine_images(output_dir='static'):
    # Directory containing the images
    image_dir = 'output/results'
    
    # Get all question images
    image_files = [f for f in os.listdir(image_dir) if f.startswith('question_') and f.endswith('.jpg')]
    
    if not image_files:
        print("No question images found to combine")
        return
    
    # Create a dictionary to map question numbers to filenames
    question_map = {}
    for img_file in image_files:
        try:
            num = int(img_file.split('_')[1].split('.')[0])
            question_map[num] = img_file
        except (IndexError, ValueError):
            continue
    
    if not question_map:
        print("No valid question images found")
        return
    
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
        # First column: 31-45 (previously was 1-15)
        if row + 31 in question_map:
            img1 = Image.open(os.path.join(image_dir, question_map[row + 31]))
            combined_image.paste(img1, (0 * cell_width, row * cell_height))
        
        # Second column: 16-30 (stays the same)
        if row + 16 in question_map:
            img2 = Image.open(os.path.join(image_dir, question_map[row + 16]))
            combined_image.paste(img2, (1 * cell_width, row * cell_height))
        
        # Third column: 1-15 (previously was 31-45)
        if row + 1 in question_map:
            img3 = Image.open(os.path.join(image_dir, question_map[row + 1]))
            combined_image.paste(img3, (2 * cell_width, row * cell_height))
    
    # Save the combined image in the specified output directory
    os.makedirs(output_dir, exist_ok=True)
    combined_image_path = os.path.join(output_dir, 'combined_questions.jpg')
    combined_image.save(combined_image_path)
    print(f"Images combined successfully into '{combined_image_path}'")

if __name__ == '__main__':
    combine_images() 