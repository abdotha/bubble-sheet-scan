import cv2
import numpy as np
import json
from datetime import datetime

def has_black_border(image_path, border_thickness=1, black_threshold=10):
    # Read the image
    img = cv2.imread(image_path)
    if img is None:
        return False
    
    # Convert to grayscale
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    
    # Check all four edges
    edges = {
        'top': gray[:border_thickness, :],
        'bottom': gray[-border_thickness:, :],
        'left': gray[:, :border_thickness],
        'right': gray[:, -border_thickness:]
    }
    
    results = {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'image_path': image_path,
        'border_thickness': border_thickness,
        'black_threshold': black_threshold,
        'edges': {}
    }
    
    has_border = True
    for edge_name, edge_pixels in edges.items():
        # Count black pixels (values below threshold)
        black_pixels = np.sum(edge_pixels < black_threshold)
        total_pixels = edge_pixels.size
        black_percentage = (black_pixels / total_pixels) * 100
        
        results['edges'][edge_name] = {
            'black_pixels': int(black_pixels),
            'total_pixels': int(total_pixels),
            'black_percentage': float(black_percentage),
            'has_border': black_percentage >= 50
        }
        
        if black_percentage < 50:  # Require at least 50% black
            has_border = False
    
    results['has_border'] = has_border
    
    # Save results to JSON file
    try:
        # Create filename with timestamp
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        json_filename = f'border_check_{timestamp}.json'
        
        with open(json_filename, 'w') as f:
            json.dump(results, f, indent=4)
        print(f"Results saved to {json_filename}")
    except Exception as e:
        print(f"Error saving results: {str(e)}")
    
    return has_border

if __name__ == "__main__":
    input_path = "cropped_input_image.jpg"
    result = has_black_border(input_path)
    print(f"Has black border: {result}")