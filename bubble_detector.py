import cv2
import numpy as np

class BubbleDetector:
    def __init__(self):
        self.min_diameter = 25   
        self.max_diameter = 100
        self.min_area = int(np.pi * (self.min_diameter/2)**2)
        self.max_area = int(np.pi * (self.max_diameter/2)**2)
        
        self.min_circularity = 0.20
        self.max_aspect_ratio = 2.5
        
        self.dark_threshold = 120
        self.fill_ratio_threshold = 0.46
        
        self.selected_color = (0, 255, 0)
        self.unselected_color = (200, 200, 200)
        self.rejected_color = (0, 255, 255)
        self.debug = True

    def preprocess(self, img):
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        
        clahe = cv2.createCLAHE(clipLimit=2.0, tileGridSize=(8, 8))
        enhanced = clahe.apply(gray)
        
        blurred = cv2.GaussianBlur(enhanced, (3, 3), 0)
        
        binary = cv2.adaptiveThreshold(blurred, 255, cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
                                     cv2.THRESH_BINARY_INV, 21, 7)
        
        return binary, enhanced

    def find_bubbles(self, img):
        binary, enhanced = self.preprocess(img)
        contours, _ = cv2.findContours(binary, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        bubbles = []
        rejected = []
        
        print("\n=== Rejected Contours Analysis ===")
        for cnt in contours:
            area = cv2.contourArea(cnt)
            perimeter = cv2.arcLength(cnt, True)
            circularity = 4 * np.pi * area / (perimeter**2) if perimeter > 0 else 0
            
            _, _, w, h = cv2.boundingRect(cnt)
            aspect_ratio = max(w, h) / min(w, h) if min(w, h) > 0 else 0
            
            diameter = 2 * np.sqrt(area / np.pi)
            
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
        
        bubbles.sort(key=lambda b: b['center'][0], reverse=True)
        bubbles = bubbles[:4]
        
        return bubbles, rejected

    def get_contour_center(self, cnt):
        M = cv2.moments(cnt)
        if M['m00'] > 0:
            return (int(M['m10']/M['m00']), int(M['m01']/M['m00']))
        return (0, 0)

    def analyze_selections(self, bubbles):
        if not bubbles:
            return []
            
        print("\n=== Fill Ratio Analysis ===")
        for i, bubble in enumerate(bubbles):
            print(f"Bubble {i+1}:")
            print(f"  Fill ratio: {bubble['fill_ratio']:.3f}")
            print(f"  Mean intensity: {bubble['mean_val']:.1f}")
            print(f"  Area: {bubble['area']:.1f}")
            print(f"  Circularity: {bubble['circularity']:.3f}")
        
        selected_idx = [i for i, b in enumerate(bubbles) 
                       if b['fill_ratio'] > self.fill_ratio_threshold]
        
        selected_idx.sort(key=lambda i: bubbles[i]['fill_ratio'], reverse=True)
        
        print(f"\nSelected bubbles (fill ratio > {self.fill_ratio_threshold}):")
        for idx in selected_idx:
            print(f"Bubble {idx+1}: {bubbles[idx]['fill_ratio']:.3f}")
        
        return selected_idx

    def visualize(self, img, bubbles, rejected, selected_indices):
        result = img.copy()
        
        for i, bubble in enumerate(bubbles):
            x, y, w, h = cv2.boundingRect(bubble['contour'])
            
            cv2.rectangle(result, (x, y), (x + w, y + h), (255, 0, 0), 2)
            
            if i in selected_indices:
                color = self.selected_color
                thickness = 3
            else:
                color = self.unselected_color
                thickness = 1
            
            cv2.drawContours(result, [bubble['contour']], -1, color, thickness)
        
        return result

    def visualize_with_answers(self, img, bubbles, rejected, selected_indices, model_answer):
        result = img.copy()
        
        for i, bubble in enumerate(bubbles):
            x, y, w, h = cv2.boundingRect(bubble['contour'])
            
            if i in selected_indices and i == model_answer:
                color = self.selected_color
                thickness = 3
            elif i in selected_indices:
                color = (0, 0, 255)
                thickness = 3
            else:
                color = self.unselected_color
                thickness = 1
            
            cv2.drawContours(result, [bubble['contour']], -1, color, thickness)
            
            if i == model_answer:
                box_color = self.selected_color
            else:
                box_color = (255, 0, 0)
            cv2.rectangle(result, (x, y), (x + w, y + h), box_color, 2)
        
        return result

    def process(self, img_path, model_answer=None):
        img = cv2.imread(img_path)
        if img is None:
            print("Error: Could not load image")
            return None, [], [], []
        
        bubbles, rejected = self.find_bubbles(img)
        selected = self.analyze_selections(bubbles)
        
        if model_answer is not None:
            result = self.visualize_with_answers(img, bubbles, rejected, selected, model_answer)
        else:
            result = self.visualize(img, bubbles, rejected, selected)
        
        print("\n=== Final Results ===")
        print(f"Found {len(bubbles)} valid bubbles (rejected {len(rejected)} contours)")
        print(f"Selected bubbles: {selected}")
        if model_answer is not None:
            print(f"Model answer: {model_answer}")
        
        return result, bubbles, rejected, selected


if __name__ == "__main__":
    detector = BubbleDetector()
    input_img = r"output\temp\bubble_sheet_left\questions\question_10.jpg"
    output_img = "processed.jpg"
    
    # Example usage with model answer
    model_answer = 4  # Replace with actual model answer
    result, bubbles, rejected, selected = detector.process(input_img, model_answer)
    if result is not None:
        cv2.imwrite(output_img, result)
        print(f"Results saved to {output_img}")