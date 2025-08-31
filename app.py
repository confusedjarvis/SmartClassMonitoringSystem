import os
from flask import Flask, render_template, redirect, url_for, flash, request, jsonify
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, UserMixin, login_user, current_user, logout_user, login_required
from flask_bcrypt import Bcrypt
from flask_mail import Mail, Message
from datetime import datetime, date
from dotenv import load_dotenv
import sys
import json
import base64
import cv2
import numpy as np
from PIL import Image
from io import BytesIO
import pandas as pd
import logging

# Add DeepFace to sys.path
deepface_path = '/home/rohit/Downloads/deepface-master'
if deepface_path not in sys.path:
    sys.path.append(deepface_path)

# Set up logging
logging.basicConfig(level=logging.INFO, 
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    handlers=[logging.FileHandler("app.log"),
                              logging.StreamHandler()])
logger = logging.getLogger(__name__)

# Load environment variables
load_dotenv()

# Initialize Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'default_secret_key')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('SQLALCHEMY_DATABASE_URI', 'sqlite:///site.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

@app.context_processor
def inject_now():
    return {'now': datetime.now}

# Initialize extensions
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message_category = 'info'

# Configure email
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'True').lower() == 'true'
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
mail = Mail(app)

# Import DeepFace - move this inside a function to avoid module errors at import time
deepface_available = False
def init_deepface():
    global deepface_available
    try:
        from deepface import DeepFace
        logger.info("DeepFace imported successfully")
        deepface_available = True
        return True
    except ImportError as e:
        logger.error(f"Error importing DeepFace: {str(e)}")
        deepface_available = False
        return False

# Create database tables
with app.app_context():
    # Import database models
    from models.models import User, Student, Faculty, Admin, Course, Attendance, TimeTable
    
    # Create the tables
    db.create_all()
    
    # Create admin user if it doesn't exist
    admin = Admin.query.filter_by(email='admin@example.com').first()
    if not admin:
        hashed_password = bcrypt.generate_password_hash('admin123').decode('utf-8')
        admin = Admin(name='Admin', email='admin@example.com', password=hashed_password)
        db.session.add(admin)
        db.session.commit()
        logger.info("Admin user created")

# Import routes after models are defined (to avoid circular imports)
def register_blueprints():
    from routes.main_routes import main
    from routes.auth_routes import auth
    from routes.admin_routes import admin
    from routes.faculty_routes import faculty
    from routes.student_routes import student

    # Register blueprints
    app.register_blueprint(main)
    app.register_blueprint(auth, url_prefix='/auth')
    app.register_blueprint(admin, url_prefix='/admin')
    app.register_blueprint(faculty, url_prefix='/faculty')
    app.register_blueprint(student, url_prefix='/student')

# Initialize the application
with app.app_context():
    # Try to import DeepFace
    init_deepface()
    
    # Register blueprints
    register_blueprints()
    
    # Import necessary modules for login_manager
    from models.models import Student, Faculty, Admin
    
    @login_manager.user_loader
    def load_user(user_id):
        # Extract user type from the user_id (format: "type_id")
        if '_' not in user_id:
            return None
        
        user_type, user_id = user_id.split('_', 1)
        
        if user_type == 'student':
            return Student.query.get(int(user_id))
        elif user_type == 'faculty':
            return Faculty.query.get(int(user_id))
        elif user_type == 'admin':
            return Admin.query.get(int(user_id))
        return None

if __name__ == '__main__':
    app.run(debug=True)
