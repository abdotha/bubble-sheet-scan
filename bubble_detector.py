import cv2
import numpy as np

class BubbleDetector:
    def __init__(self):
        # More flexible size parameters
        self.min_diameter = 25   
        self.max_diameter = 100  # Maximum size
        self.min_area = int(np.pi * (self.min_diameter/2)**2)  # Calculate area from diameter
        self.max_area = int(np.pi * (self.max_diameter/2)**2)
        
        # Relaxed shape parameters
        self.min_circularity = 0.20  # Reduced from 0.5 to allow less circular shapes
        self.max_aspect_ratio = 2.5  # Increased from 1.5
        
        # Adjusted selection parameters
        self.dark_threshold = 120
        self.fill_ratio_threshold = 0.46  # Slightly reduced
        
        # Visualization
        self.selected_color = (0, 255, 0)  # Green
        self.unselected_color = (200, 200, 200)  # Gray
        self.rejected_color = (0, 255, 255)  # Yellow for rejected contours
        self.debug = True  # Set to False to disable debug output

    def preprocess(self, img):
        """Simple preprocessing with mean filter and salt-and-pepper noise reduction"""
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        # Remove salt and pepper noise using median filter
        denoised = cv2.medianBlur(gray, 3)
        
        # Apply mean filter (box filter)
        mean_filtered = cv2.boxFilter(denoised, -1, (5, 5), normalize=True)
        
        # Gentle contrast enhancement
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(mean_filtered)
        
        # Mild smoothing
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        # Adaptive thresholding
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 21, 7)
        
        return binary, enhanced

    def find_bubbles(self, img):
        """More flexible bubble detection"""
        binary, enhanced = self.preprocess(img)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        bubbles = []
        rejected = []
        
        print("\n=== Rejected Contours Analysis ===")
        for cnt in contours:
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter**2) if perimeter > 0 else 0
            
            # Get bounding rectangle and aspect ratio
            _, _, w, h = cv2.boundingRect(cnt)
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            
            # Calculate equivalent diameter
            diameter = 2 * np.sqrt(area / np.pi)
            
            # Size and shape validation
            size_ok = self.min_area < area < self.max_area
            shape_ok = (circularity > self.min_circularity and 
                       aspect_ratio < self.max_aspect_ratio)
            
            if size_ok and shape_ok:
                mask = np.zeros_like(enhanced)
                cv2.drawContours(mask, [cnt], -1, 255, -1)
                
                mean_val = cv2.mean(enhanced, mask=mask)[0]
                dark_px = np.sum(enhanced[mask > 0] < self.dark_threshold)
                fill_ratio = dark_px / np.sum(mask > 0) if np.sum(mask > 0) > 0 else 0
                
                bubbles.append({
                    'contour': cnt,
                    'center': self.get_contour_center(cnt),
                    'area': area,
                    'diameter': diameter,
                    'circularity': circularity,
                    'aspect_ratio': aspect_ratio,
                    'fill_ratio': fill_ratio,
                    'mean_val': mean_val
                })
                
                if self.debug:
                    print(f"Valid bubble - Fill ratio: {fill_ratio:.2f}, Mean intensity: {mean_val:.1f}")
            else:
                # Determine rejection reason
                rejection_reason = []
                if not size_ok:
                    if area <= self.min_area:
                        rejection_reason.append("Too small")
                    else:
                        rejection_reason.append("Too large")
                if not shape_ok:
                    if circularity <= self.min_circularity:
                        rejection_reason.append("Low circularity")
                    if aspect_ratio >= self.max_aspect_ratio:
                        rejection_reason.append("High aspect ratio")
                
                rejected.append({
                    'contour': cnt,
                    'area': area,
                    'circularity': circularity,
                    'aspect_ratio': aspect_ratio,
                    'rejection_reason': " & ".join(rejection_reason)
                })
                
                print(f"\nRejected Contour:")
                print(f"  Area: {area:.1f} (min: {self.min_area}, max: {self.max_area})")
                print(f"  Diameter: {diameter:.1f}px (min: {self.min_diameter}, max: {self.max_diameter})")
                print(f"  Circularity: {circularity:.3f} (min: {self.min_circularity})")
                print(f"  Aspect Ratio: {aspect_ratio:.2f} (max: {self.max_aspect_ratio})")
                print(f"  Size OK: {size_ok}")
                print(f"  Shape OK: {shape_ok}")
                print(f"  Rejection Reason: {rejection_reason}")
        
        # Sort bubbles right-to-left (0 is rightmost, 3 is leftmost)
        bubbles.sort(key=lambda b: b['center'][0], reverse=True)
        
        # Ensure we only keep the first 4 bubbles (0-3)
        bubbles = bubbles[:4]
        
        return bubbles, rejected

    def get_contour_center(self, cnt):
        M = cv2.moments(cnt)
        if M['m00'] > 0:
            return (int(M['m10']/M['m00']), int(M['m01']/M['m00']))
        return (0, 0)

    def analyze_selections(self, bubbles):
        """Select bubbles based on fill ratio analysis"""
        if not bubbles:
            return []
            
        # Print detailed fill ratio analysis
        print("\n=== Fill Ratio Analysis ===")
        for i, bubble in enumerate(bubbles):
            print(f"Bubble {i+1}:")
            print(f"  Fill ratio: {bubble['fill_ratio']:.3f}")
            print(f"  Mean intensity: {bubble['mean_val']:.1f}")
            print(f"  Area: {bubble['area']:.1f}")
            print(f"  Circularity: {bubble['circularity']:.3f}")
        
        # Find bubbles with fill ratio above threshold
        selected_idx = [i for i, b in enumerate(bubbles) 
                       if b['fill_ratio'] > self.fill_ratio_threshold]
        
        # Sort selected bubbles by fill ratio (highest first)
        selected_idx.sort(key=lambda i: bubbles[i]['fill_ratio'], reverse=True)
        
        print(f"\nSelected bubbles (fill ratio > {self.fill_ratio_threshold}):")
        for idx in selected_idx:
            print(f"Bubble {idx+1}: {bubbles[idx]['fill_ratio']:.3f}")
        
        return selected_idx

    def visualize(self, img, bubbles, rejected, selected_indices):
        """Visualize results with fill ratio information"""
        result = img.copy()
        
        # Draw all bubbles
        for i, bubble in enumerate(bubbles):
            # Set color based on selection status
            if i in selected_indices:
                color = self.selected_color
                thickness = 3
            else:
                color = self.unselected_color
                thickness = 1
            
            # Draw bubble contour
            cv2.drawContours(result, [bubble['contour']], -1, color, thickness)
        
        return result

    def visualize_with_answers(self, img, bubbles, rejected, selected_indices, model_answer):
        """Visualize results with color coding based on model answer"""
        result = img.copy()
        
        # Use selected_indices and model_answer directly (0 = leftmost)
        for i, bubble in enumerate(bubbles):
            # Get bounding rectangle
            x, y, w, h = cv2.boundingRect(bubble['contour'])
            
            # Set color based on selection and answer status
            if i in selected_indices and i == model_answer:
                color = self.selected_color  # Green for correct answer (selected and model answer)
                thickness = 3
            elif i in selected_indices:
                color = (0, 0, 255)  # Red for incorrect answer (selected but not model answer)
                thickness = 3
            else:
                color = self.unselected_color
                thickness = 1
            
            # Draw bubble contour (fill)
            cv2.drawContours(result, [bubble['contour']], -1, color, thickness)
            
            # Draw green box only for model answer
            if i == model_answer:
                cv2.rectangle(result, (x, y), (x + w, y + h), self.selected_color, 2)
        
        return result

    def process(self, img_path, model_answer=None):
        img = cv2.imread(img_path)
        if img is None:
            print("Error: Could not load image")
            return None, [], [], []
        
        bubbles, rejected = self.find_bubbles(img)
        selected = self.analyze_selections(bubbles)
        
        # Use appropriate visualization based on whether model_answer is provided
        if model_answer is not None:
            result = self.visualize_with_answers(img, bubbles, rejected, selected, model_answer)
        else:
            result = self.visualize(img, bubbles, rejected, selected)
        
        # Console reporting
        print("\n=== Final Results ===")
        print(f"Found {len(bubbles)} valid bubbles (rejected {len(rejected)} contours)")
        print(f"Selected bubbles: {selected}")
        if model_answer is not None:
            print(f"Model answer: {model_answer}")
            print(f"Correct answer: {model_answer in selected}")
        
        print("\nBubble Statistics:")
        for i, bubble in enumerate(bubbles):
            status = "SELECTED" if i in selected else "unselected"
            print(f"Bubble {i}: {status}")
            print(f"  Diameter: {bubble['diameter']:.1f}px")
            print(f"  Fill ratio: {bubble['fill_ratio']:.2f}")
            print(f"  Circularity: {bubble['circularity']:.2f}\n")
        
        return result, bubbles, selected, rejected


if __name__ == "__main__":
    detector = BubbleDetector()
    input_img = r"output\temp\bubble_sheet_left\questions\question_10.jpg"
    output_img = "processed.jpg"
    
    # Example usage with model answer
    model_answer = 4  # Replace with actual model answer
    result, bubbles, selected, rejected = detector.process(input_img, model_answer)
    if result is not None:
        cv2.imwrite(output_img, result)
        print(f"Results saved to {output_img}")