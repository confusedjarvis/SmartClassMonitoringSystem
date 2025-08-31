import os
import warnings
import logging
import numpy as np
import cv2
import tensorflow as tf
from tensorflow.keras.applications import VGG16
from tensorflow.keras.applications.vgg16 import preprocess_input

# Configure logging
logger = logging.getLogger(__name__)
warnings.filterwarnings("ignore")
os.environ["TF_CPP_MIN_LOG_LEVEL"] = "3"

# Initialize the face detection model
face_cascade = cv2.CascadeClassifier(cv2.data.haarcascades + 'haarcascade_frontalface_default.xml')

# Initialize VGG model (will be loaded on first use)
_vgg_model = None

def get_vgg_model():
    global _vgg_model
    if _vgg_model is None:
        _vgg_model = VGG16(weights='imagenet', include_top=False, pooling='avg')
    return _vgg_model

def represent(
    img_path,
    model_name="VGG-Face",
    enforce_detection=True,
    detector_backend="opencv",
    align=True,
    expand_percentage=0,
    normalization="base"
):
    """
    Generate face embeddings using VGG16 model
    Args:
        img_path: Path to image, numpy array, or file object
        model_name: Name of the face recognition model (only VGG-Face supported)
        enforce_detection: Enforce face detection
        detector_backend: Face detector backend (only opencv supported)
        align: Align faces (not implemented)
        expand_percentage: Expand face area percentage
        normalization: Normalization method
    Returns:
        List of dictionaries containing embeddings and face information
    """
    try:
        # Convert image to BGR numpy array if needed
        if isinstance(img_path, str):
            if not os.path.exists(img_path):
                raise ValueError(f"Image path {img_path} does not exist")
            img = cv2.imread(img_path)
        elif isinstance(img_path, np.ndarray):
            img = img_path.copy()
        else:
            raise ValueError("Invalid image input")

        if img is None:
            raise ValueError("Could not load image")
        
        # Detect faces
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
        faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5, minSize=(30, 30))
        
        if len(faces) == 0:
            if enforce_detection:
                raise ValueError("No faces detected in the image")
            else:
                # If no face detected and enforce_detection is False, use whole image
                faces = [(0, 0, img.shape[1], img.shape[0])]
        
        results = []
        for (x, y, w, h) in faces:
            # Extract and preprocess face
            face = img[y:y+h, x:x+w]
            face = cv2.resize(face, (224, 224))
            face = preprocess_input(face)
            
            # Get embedding using VGG16
            model = get_vgg_model()
            embedding = model.predict(np.expand_dims(face, axis=0), verbose=0)[0]
            
            result = {
                'embedding': embedding,
                'facial_area': {'x': x, 'y': y, 'w': w, 'h': h},
                'face_confidence': 1.0  # Placeholder confidence score
            }
            results.append(result)
        
        return results
    
    except Exception as e:
        logger.error(f"Error in represent function: {str(e)}")
        raise