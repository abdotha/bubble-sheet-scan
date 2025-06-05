import cv2
import numpy as np
import os

def order_points(pts):
    # Initialize a list of coordinates that will be ordered
    rect = np.zeros((4, 2), dtype=np.float32)
    
    # The top-left point will have the smallest sum
    # The bottom-right point will have the largest sum
    s = pts.sum(axis=1)
    rect[0] = pts[np.argmin(s)]
    rect[2] = pts[np.argmax(s)]
    
    # The top-right point will have the smallest difference
    # The bottom-left will have the largest difference
    diff = np.diff(pts, axis=1)
    rect[1] = pts[np.argmin(diff)]
    rect[3] = pts[np.argmax(diff)]
    
    return rect

def four_point_transform(image, pts):
    # Obtain a consistent order of the points
    rect = order_points(pts)
    (tl, tr, br, bl) = rect
    
    # Compute the width of the new image
    widthA = np.sqrt(((br[0] - bl[0]) ** 2) + ((br[1] - bl[1]) ** 2))
    widthB = np.sqrt(((tr[0] - tl[0]) ** 2) + ((tr[1] - tl[1]) ** 2))
    maxWidth = max(int(widthA), int(widthB))
    
    # Compute the height of the new image
    heightA = np.sqrt(((tr[0] - br[0]) ** 2) + ((tr[1] - br[1]) ** 2))
    heightB = np.sqrt(((tl[0] - bl[0]) ** 2) + ((tl[1] - bl[1]) ** 2))
    maxHeight = max(int(heightA), int(heightB))
    
    # Construct set of destination points
    dst = np.array([
        [0, 0],
        [maxWidth - 1, 0],
        [maxWidth - 1, maxHeight - 1],
        [0, maxHeight - 1]], dtype=np.float32)
    
    # Compute the perspective transform matrix and apply it
    M = cv2.getPerspectiveTransform(rect, dst)
    warped = cv2.warpPerspective(image, M, (maxWidth, maxHeight))
    
    return warped

def detect_and_crop_border(image_path):
    # Read the image
    image = cv2.imread(image_path)
    if image is None:
        raise ValueError(f"Could not read image at {image_path}")
    
    # Check if height is less than width and rotate if needed
    height, width = image.shape[:2]
    print(f"Height: {height}, Width: {width}")
    if height < width:
        # Rotate 90 degrees clockwise
        image = cv2.rotate(image, cv2.ROTATE_90_CLOCKWISE)
    
    # Convert to grayscale
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    
    # Apply Gaussian blur to reduce noise
    blurred = cv2.GaussianBlur(gray, (5, 5), 0)
    
    # Apply adaptive thresholding
    binary = cv2.adaptiveThreshold(
        blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C, 
        cv2.THRESH_BINARY_INV, 11, 2
    )
    
    # Find contours
    contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
    
    if not contours:
        return image
    
    # Find the largest contour (should be the black border)
    largest_contour = max(contours, key=cv2.contourArea)
    
    # Approximate the contour to get a simpler polygon
    epsilon = 0.02 * cv2.arcLength(largest_contour, True)
    approx = cv2.approxPolyDP(largest_contour, epsilon, True)
    
    # If we have 4 points, we can do perspective transform
    if len(approx) == 4:
        # Reshape the points for perspective transform
        pts = approx.reshape(4, 2)
        
        # Apply perspective transform
        warped = four_point_transform(image, pts)
        
        # Add padding
        padding = 10
        h, w = warped.shape[:2]
        warped = cv2.copyMakeBorder(
            warped, padding, padding, padding, padding,
            cv2.BORDER_CONSTANT, value=[255, 255, 255]
        )
        
        return warped
    
    # If we don't have 4 points, fall back to the original method
    rect = cv2.minAreaRect(largest_contour)
    box = cv2.boxPoints(rect)
    box = np.int32(box)
    
    # Get width and height of the rectangle
    width = int(rect[1][0])
    height = int(rect[1][1])
    
    # Get the rotation angle
    angle = rect[2]
    
    # Adjust angle if width is less than height
    if width < height:
        angle = angle + 90
    
    # Get the center of the rectangle
    center = rect[0]
    
    # Get the rotation matrix
    M = cv2.getRotationMatrix2D(center, angle, 1.0)
    
    # Rotate the image
    rotated = cv2.warpAffine(image, M, (image.shape[1], image.shape[0]), 
                            flags=cv2.INTER_CUBIC, borderMode=cv2.BORDER_REPLICATE)
    
    # Find the bounding rectangle of the rotated contour
    x, y, w, h = cv2.boundingRect(largest_contour)
    
    # Add some padding
    padding = 10
    x = max(0, x - padding)
    y = max(0, y - padding)
    w = min(rotated.shape[1] - x, w + 2*padding)
    h = min(rotated.shape[0] - y, h + 2*padding)
    
    # Crop the image
    cropped = rotated[y:y+h, x:x+w]
    
    return cropped

def process_images(input_path):
    # Define standard size for all images
    standard_width = 800
    standard_height = 600
    
    try:
        # Process the image
        cropped_image = detect_and_crop_border(input_path)
        
        # Convert to grayscale
        gray_image = cv2.cvtColor(cropped_image, cv2.COLOR_BGR2GRAY)
        
        # Remove salt and pepper noise using median blur
        denoised_image = cv2.medianBlur(gray_image, 3)
        
        # Apply bilateral filter with minimal smoothing to preserve edges
        denoised_image = cv2.bilateralFilter(denoised_image, 3, 25, 25)
        
        # Enhance contrast using CLAHE
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8,8))
        enhanced_image = clahe.apply(denoised_image)
        
        # Apply strong sharpening using unsharp masking
        gaussian = cv2.GaussianBlur(enhanced_image, (0, 0), 1.5)
        enhanced_image = cv2.addWeighted(enhanced_image, 2.0, gaussian, -1.0, 0)
        
        # Apply additional sharpening using Laplacian
        laplacian = cv2.Laplacian(enhanced_image, cv2.CV_64F)
        laplacian = np.uint8(np.absolute(laplacian))  # Convert to uint8
        enhanced_image = cv2.addWeighted(enhanced_image, 1.0, laplacian, 0.3, 0)
        
        # Ensure values are in valid range and convert to uint8
        enhanced_image = np.clip(enhanced_image, 0, 255).astype(np.uint8)
        
        # Resize image to standard size
        resized_image = cv2.resize(enhanced_image, (standard_width, standard_height), 
                                    interpolation=cv2.INTER_LINEAR)
        print(f"Image has been resized to {standard_width}x{standard_height} pixels.")
        return resized_image
    except Exception as e:
        print(f"Error processing image: {str(e)}")
        return None

if __name__ == "__main__":
    # Create necessary directories
    output_dir = "temp"
    os.makedirs(output_dir, exist_ok=True)
    
    # Specify input and output paths
    input_path = r'input_images\sample_3.jpeg'
    output_image = process_images(input_path)
    cv2.imwrite('cropped_image.jpg', output_image)
