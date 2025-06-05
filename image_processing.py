import cv2
import os
import numpy as np

def enhance_image(image):
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Remove salt and pepper noise using median filter
    denoised = cv2.medianBlur(gray, 3)
    
    # Apply adaptive thresholding for better contrast
    binary = cv2.adaptiveThreshold(
        denoised, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY, 11, 2
    )
    
    # Create sharpening kernel
    kernel = np.array([[-1,-1,-1],
                      [-1, 9,-1],
                      [-1,-1,-1]])
    
    # Apply sharpening
    sharpened = cv2.filter2D(binary, -1, kernel)
    
    # Convert back to BGR for saving
    enhanced = cv2.cvtColor(sharpened, cv2.COLOR_GRAY2BGR)
    return enhanced

def crop_into_thirds(image):
    # Get image dimensions
    height, width = image.shape[:2]
    
    # Calculate width of each segment
    segment_width = width // 3
    
    # Calculate new height after removing top and bottom portions
    new_height = height - 95 - 87
    
    # Crop into three equal parts and remove top/bottom portions
    left_part = image[60:height-60, 0:segment_width]
    middle_part = image[60:height-60, segment_width:segment_width*2]
    right_part = image[60:height-60, segment_width*2:width]
    
    return left_part, middle_part, right_part

def main():
    # Example usage
    image_path = input("Enter the path to your image: ")
    output_folder = input("Enter the output folder path: ")
    
    print("\nImage Cropping Tool")
    print("==================")
    
    # Check if input file exists
    if not os.path.exists(image_path):
        print(f"Error: Input file '{image_path}' does not exist!")
        return
    
    # Process the image
    success = crop_into_thirds(image_path, output_folder)
    
    if success:
        print("\nProcessing complete!")
        print(f"All cropped images have been saved in the '{output_folder}' folder")
    else:
        print("\nProcessing failed!")

if __name__ == "__main__":
    main()

