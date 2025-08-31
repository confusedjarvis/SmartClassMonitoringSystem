import os
import sys
import cv2
import numpy as np
import mediapipe as mp
import logging
from scipy.spatial.distance import cosine
from PIL import Image
from io import BytesIO
import base64
import time

# Configure logger
logger = logging.getLogger(__name__)

# Add DeepFace to sys.path
deepface_path = '/home/rohit/Downloads/deepface-master'
if deepface_path not in sys.path:
    sys.path.append(deepface_path)

# Import DeepFace and handle errors
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    logger.info("DeepFace imported successfully in advanced_face_recognition")
except ImportError as e:
    DEEPFACE_AVAILABLE = False
    logger.error(f"Error importing DeepFace in advanced_face_recognition: {str(e)}")

# Initialize MediaPipe face detection
mp_face_detection = mp.solutions.face_detection
mp_face_mesh = mp.solutions.face_mesh
mp_drawing = mp.solutions.drawing_utils

# Create face detector instances
face_detection = mp_face_detection.FaceDetection(
    model_selection=1,  # 0 for closer faces, 1 for further faces
    min_detection_confidence=0.5
)

face_mesh = mp_face_mesh.FaceMesh(
    static_image_mode=True,
    max_num_faces=10,  # Set to handle multiple faces
    min_detection_confidence=0.5
)

# Load Haar Cascade as backup
face_cascade = cv2.CascadeClassifier(
    cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
)

def base64_to_cv2_image(base64_string):
    """Convert base64 string to OpenCV image"""
    if ',' in base64_string:
        base64_string = base64_string.split(',')[1]
    
    img_data = base64.b64decode(base64_string)
    img_array = np.frombuffer(img_data, np.uint8)
    img = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return img

def detect_faces(img):
    """
    Enhanced face detection using MediaPipe first, then falling back to Haar Cascade
    Returns a list of face bounding boxes as (x, y, w, h)
    """
    if img is None:
        logger.error("Input image is None")
        return []
        
    # Convert to RGB for MediaPipe
    rgb_img = cv2.cvtColor(img, cv2.COLOR_BGR2RGB)
    
    # Try MediaPipe face detection first (more accurate)
    detection_result = face_detection.process(rgb_img)
    faces = []
    
    if detection_result.detections:
        for detection in detection_result.detections:
            # Get bounding box from detection
            bboxC = detection.location_data.relative_bounding_box
            ih, iw, _ = img.shape
            x = max(0, int(bboxC.xmin * iw))
            y = max(0, int(bboxC.ymin * ih))
            w = min(int(bboxC.width * iw), iw - x)
            h = min(int(bboxC.height * ih), ih - y)
            faces.append((x, y, w, h))
        
        if faces:
            return faces
    
    # If MediaPipe fails or doesn't find any faces, try Haar cascade
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    haar_faces = face_cascade.detectMultiScale(
        gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30)
    )
    
    if len(haar_faces) > 0:
        return [(x, y, w, h) for (x, y, w, h) in haar_faces]
    
    # As a last resort, try DeepFace's built-in detector
    if DEEPFACE_AVAILABLE:
        try:
            detected = DeepFace.extract_faces(img, enforce_detection=False, detector_backend="opencv")
            if detected:
                for face_obj in detected:
                    facial_area = face_obj.get("facial_area", {})
                    if facial_area:
                        x = facial_area.get("x", 0)
                        y = facial_area.get("y", 0)
                        w = facial_area.get("w", 0)
                        h = facial_area.get("h", 0)
                        faces.append((x, y, w, h))
        except Exception as e:
            logger.error(f"DeepFace extraction error: {str(e)}")
    
    return faces

def align_face(img, face):
    """
    Align face for better recognition accuracy
    """
    x, y, w, h = face
    
    # Ensure coordinates are within image boundaries
    y = max(0, y)
    x = max(0, x)
    w = min(w, img.shape[1] - x)
    h = min(h, img.shape[0] - y)
    
    # Extract face region
    face_roi = img[y:y+h, x:x+w]
    
    # Check if ROI is valid
    if face_roi.size == 0 or face_roi.shape[0] == 0 or face_roi.shape[1] == 0:
        logger.warning("Invalid face ROI")
        return cv2.resize(img, (160, 160))
    
    # Convert to RGB for MediaPipe
    rgb_roi = cv2.cvtColor(face_roi, cv2.COLOR_BGR2RGB)
    
    # Get face mesh landmarks
    result = face_mesh.process(rgb_roi)
    
    if not result.multi_face_landmarks or len(result.multi_face_landmarks) == 0:
        # If no landmarks found, just resize the face ROI
        return cv2.resize(face_roi, (160, 160))
    
    landmarks = result.multi_face_landmarks[0].landmark
    
    # Get coordinates for eyes
    left_eye_indices = [33, 145, 159]  # Simplified indices
    right_eye_indices = [263, 374, 386]
    
    # Calculate eye centers
    left_eye_points = []
    right_eye_points = []
    
    h_roi, w_roi, _ = face_roi.shape
    
    for idx in left_eye_indices:
        if idx < len(landmarks):
            point = landmarks[idx]
            x_coord, y_coord = int(point.x * w_roi), int(point.y * h_roi)
            left_eye_points.append((x_coord, y_coord))
    
    for idx in right_eye_indices:
        if idx < len(landmarks):
            point = landmarks[idx]
            x_coord, y_coord = int(point.x * w_roi), int(point.y * h_roi)
            right_eye_points.append((x_coord, y_coord))
    
    # If we don't have enough points, just resize
    if len(left_eye_points) == 0 or len(right_eye_points) == 0:
        return cv2.resize(face_roi, (160, 160))
    
    left_eye_center = np.mean(left_eye_points, axis=0).astype(int)
    right_eye_center = np.mean(right_eye_points, axis=0).astype(int)
    
    # Calculate angle for alignment
    dY = right_eye_center[1] - left_eye_center[1]
    dX = right_eye_center[0] - left_eye_center[0]
    angle = np.degrees(np.arctan2(dY, dX))
    
    # Calculate scale
    dist = np.sqrt((dX**2) + (dY**2))
    desired_dist = 70  # Desired distance between eyes
    scale = desired_dist / max(1, dist)
    
    # Calculate center point
    eyes_center = (
        int((left_eye_center[0] + right_eye_center[0]) // 2),
        int((left_eye_center[1] + right_eye_center[1]) // 2)
    )
    
    # Get rotation matrix
    M = cv2.getRotationMatrix2D(eyes_center, angle, scale)
    
    # Update translation component
    tX = 160 / 2  # Center horizontally
    tY = 160 * 0.4  # Place eyes about 40% from the top
    M[0, 2] += (tX - eyes_center[0])
    M[1, 2] += (tY - eyes_center[1])
    
    # Apply the affine transformation
    aligned_face = cv2.warpAffine(face_roi, M, (160, 160), flags=cv2.INTER_CUBIC)
    
    return aligned_face

def extract_embeddings(face_img):
    """
    Extract facial embeddings using DeepFace
    Returns embeddings for a single face
    """
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace is not available")
        return None
    
    try:
        # Check if face is valid
        if face_img is None or face_img.size == 0:
            logger.error("Invalid face image")
            return None
        
        # Convert to RGB (DeepFace expects RGB)
        face_rgb = cv2.cvtColor(face_img, cv2.COLOR_BGR2RGB)
        
        # Ensure minimum size
        if face_rgb.shape[0] < 64 or face_rgb.shape[1] < 64:
            face_rgb = cv2.resize(face_rgb, (160, 160))
        
        # Use DeepFace for feature extraction
        embedding_obj = DeepFace.represent(
            face_rgb, 
            model_name="Facenet", 
            enforce_detection=False,
            detector_backend="opencv"
        )
        
        if embedding_obj and len(embedding_obj) > 0:
            return embedding_obj[0]["embedding"]
        return None
    except Exception as e:
        logger.error(f"Error extracting embeddings: {str(e)}")
        return None

def match_face_with_database(embedding, database, threshold=0.4):
    """
    Match a face embedding with a database of students
    Returns the student ID if a match is found, None otherwise
    """
    if embedding is None or not database:
        return None
    
    best_match = None
    min_distance = float('inf')
    
    for student_id, student_data in database.items():
        if not isinstance(student_data, dict) or "embeddings" not in student_data:
            continue
            
        student_embedding = student_data["embeddings"]
        distance = cosine(embedding, student_embedding)
        
        if distance < min_distance:
            min_distance = distance
            best_match = student_id
    
    # Calculate confidence score (1 - distance)
    confidence = 1 - min_distance
    
    if confidence > threshold:
        return {
            "student_id": best_match,
            "confidence": confidence
        }
    return None

def recognize_students_in_image(img, database, draw_detections=True):
    """
    Recognize multiple students in an image
    Returns list of recognized students with bounding boxes
    """
    if img is None:
        logger.error("Input image is None")
        return [], img
    
    # Make a copy of the image for drawing
    result_img = img.copy() if draw_detections else None
    
    # Detect faces
    faces = detect_faces(img)
    recognized_students = []
    
    if not faces:
        logger.info("No faces detected in the image")
        return [], result_img
    
    # Process each detected face
    for (x, y, w, h) in faces:
        # Skip very small faces
        if w < 50 or h < 50:
            continue
            
        try:
            # Align the face
            aligned_face = align_face(img, (x, y, w, h))
            
            # Extract embeddings
            embedding = extract_embeddings(aligned_face)
            
            if embedding is not None:
                # Match with database
                match_result = match_face_with_database(embedding, database)
                
                if match_result:
                    student_id = match_result["student_id"]
                    confidence = match_result["confidence"]
                    
                    recognized_students.append({
                        "student_id": student_id,
                        "confidence": confidence,
                        "bbox": (x, y, w, h)
                    })
                    
                    # Draw bounding box and label if requested
                    if draw_detections:
                        cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 255, 0), 2)
                        label = f"{student_id} ({confidence:.2f})"
                        cv2.putText(result_img, label, (x, y - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 255, 0), 2)
                else:
                    # Draw red box for unrecognized faces
                    if draw_detections:
                        cv2.rectangle(result_img, (x, y), (x + w, y + h), (0, 0, 255), 2)
                        cv2.putText(result_img, "Unknown", (x, y - 10),
                                   cv2.FONT_HERSHEY_SIMPLEX, 0.5, (0, 0, 255), 2)
        except Exception as e:
            logger.error(f"Error processing face at ({x},{y}): {str(e)}")
            continue
    
    return recognized_students, result_img

def process_attendance_image(base64_image, student_database):
    """
    Process an attendance image with multiple students
    Returns recognized students and annotated image
    """
    try:
        # Convert base64 to image
        img = base64_to_cv2_image(base64_image)
        
        if img is None:
            logger.error("Failed to convert base64 to image")
            return [], None
        
        # Recognize students in the image
        recognized_students, annotated_img = recognize_students_in_image(img, student_database)
        
        # Convert annotated image back to base64 for display
        if annotated_img is not None:
            _, buffer = cv2.imencode('.jpg', annotated_img)
            img_str = base64.b64encode(buffer).decode('utf-8')
            base64_img = f"data:image/jpeg;base64,{img_str}"
        else:
            base64_img = None
        
        return recognized_students, base64_img
    except Exception as e:
        logger.error(f"Error processing attendance image: {str(e)}")
        return [], None

def load_student_embeddings(face_data_dir):
    """
    Load student face embeddings from the face_data directory
    Returns a dictionary of student_id -> embeddings
    """
    database = {}
    
    if not os.path.exists(face_data_dir):
        logger.error(f"Face data directory not found: {face_data_dir}")
        return database
    
    try:
        for filename in os.listdir(face_data_dir):
            if filename.startswith("student_") and filename.endswith(".jpg"):
                # Extract student ID from filename (student_12345.jpg -> 12345)
                student_id = filename.replace("student_", "").replace(".jpg", "")
                
                # Full path to the face image
                face_path = os.path.join(face_data_dir, filename)
                
                # Extract embeddings
                if DEEPFACE_AVAILABLE:
                    try:
                        embedding = DeepFace.represent(
                            img_path=face_path, 
                            model_name="Facenet", 
                            enforce_detection=False,
                            detector_backend="opencv"
                        )
                        
                        if embedding and len(embedding) > 0:
                            database[student_id] = {
                                "embeddings": embedding[0]["embedding"],
                                "filename": filename
                            }
                    except Exception as e:
                        logger.error(f"Error extracting embeddings for {student_id}: {str(e)}")
    except Exception as e:
        logger.error(f"Error loading student database: {str(e)}")
    
    logger.info(f"Loaded {len(database)} student face embeddings")
    return database
