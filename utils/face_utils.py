import os
import sys
import cv2
import numpy as np
import base64
from io import BytesIO
from PIL import Image
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Add DeepFace to sys.path
deepface_path = '/home/rohit/Downloads/deepface-master'
if deepface_path not in sys.path:
    sys.path.append(deepface_path)

# Import DeepFace globally and handle errors
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    logger.info("DeepFace imported successfully in face_utils")
except ImportError as e:
    DEEPFACE_AVAILABLE = False
    logger.error(f"Error importing DeepFace in face_utils: {str(e)}")

def extract_faces_from_image(image_path):
    """
    Extract faces from an image using DeepFace
    
    Args:
        image_path: Path to the image file
        
    Returns:
        A list of extracted face objects
    """
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace is not available")
        return []
        
    try:
        faces = DeepFace.extract_faces(img_path=image_path)
        return faces
    except Exception as e:
        logger.error(f"Error extracting faces: {str(e)}")
        return []

def generate_face_embedding(image_path, model_name="VGG-Face"):
    """
    Generate face embedding using DeepFace
    
    Args:
        image_path: Path to the image file
        model_name: Model to use for embedding generation
        
    Returns:
        Embedding vector if successful, None otherwise
    """
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace is not available")
        return None
        
    try:
        embedding_objs = DeepFace.represent(img_path=image_path, model_name=model_name)
        if embedding_objs:
            return embedding_objs[0]["embedding"]
        return None
    except Exception as e:
        logger.error(f"Error generating face embedding: {str(e)}")
        return None

def verify_faces(img1_path, img2_path, model_name="VGG-Face", distance_metric="cosine", threshold=None):
    """
    Verify if two faces belong to the same person
    
    Args:
        img1_path: Path to the first image
        img2_path: Path to the second image
        model_name: Model to use for verification
        distance_metric: Distance metric to use
        threshold: Custom threshold for verification
        
    Returns:
        Dictionary with verification result
    """
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace is not available")
        return {"verified": False, "error": "DeepFace not available"}
        
    try:
        kwargs = {
            "img1_path": img1_path,
            "img2_path": img2_path,
            "model_name": model_name,
            "distance_metric": distance_metric
        }
        
        if threshold is not None:
            kwargs["threshold"] = threshold
        
        result = DeepFace.verify(**kwargs)
        return result
    except Exception as e:
        logger.error(f"Error verifying faces: {str(e)}")
        return {"verified": False, "error": str(e)}

def recognize_faces_in_image(image_path, database_path, model_name="VGG-Face", distance_metric="cosine"):
    """
    Recognize faces in an image by comparing with a database
    
    Args:
        image_path: Path to the image file
        database_path: Path to the database of face images
        model_name: Model to use for recognition
        distance_metric: Distance metric to use
        
    Returns:
        A list of recognition results
    """
    if not DEEPFACE_AVAILABLE:
        logger.error("DeepFace is not available")
        return []
        
    try:
        results = DeepFace.find(
            img_path=image_path,
            db_path=database_path,
            model_name=model_name,
            distance_metric=distance_metric
        )
        return results
    except Exception as e:
        logger.error(f"Error recognizing faces: {str(e)}")
        return []

def base64_to_image(base64_str, save_path=None):
    """
    Convert a base64 string to an image
    
    Args:
        base64_str: Base64 encoded image string
        save_path: Path to save the image (optional)
        
    Returns:
        PIL Image object
    """
    try:
        if ',' in base64_str:
            base64_str = base64_str.split(',')[1]
        
        image_data = base64.b64decode(base64_str)
        image = Image.open(BytesIO(image_data))
        
        if save_path:
            image.save(save_path)
        
        return image
    except Exception as e:
        logger.error(f"Error converting base64 to image: {str(e)}")
        return None

def image_to_base64(image_path):
    """
    Convert an image to base64 string
    
    Args:
        image_path: Path to the image file
        
    Returns:
        Base64 encoded image string
    """
    try:
        with open(image_path, "rb") as image_file:
            encoded_string = base64.b64encode(image_file.read()).decode('utf-8')
        return f"data:image/jpeg;base64,{encoded_string}"
    except Exception as e:
        logger.error(f"Error converting image to base64: {str(e)}")
        return None
