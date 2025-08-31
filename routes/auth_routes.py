from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify, current_app
from flask_login import login_user, current_user, logout_user, login_required
from app import db, bcrypt, mail
from models.models import Student, Faculty, Admin, Course
from utils.forms import LoginForm, StudentRegistrationForm, AdminLoginForm, FacultyRegistrationForm, ForgotPasswordForm
from utils.face_utils import base64_to_image, generate_face_embedding, extract_faces_from_image
from flask_mail import Message
import os
import sys
import json
import base64
import numpy as np
from PIL import Image
from io import BytesIO
import logging

# Configure logger
logger = logging.getLogger(__name__)

# Add DeepFace to sys.path
deepface_path = '/home/rohit/Downloads/deepface-master'
if deepface_path not in sys.path:
    sys.path.append(deepface_path)

# Import DeepFace - using try/except to handle possible import errors
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    logger.info("DeepFace imported successfully in auth_routes")
except ImportError as e:
    DEEPFACE_AVAILABLE = False
    logger.error(f"Error importing DeepFace in auth_routes: {str(e)}")

auth = Blueprint('auth', __name__)

@auth.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = LoginForm()
    if form.validate_on_submit():
        # Try to find the user in Student or Faculty tables
        student = Student.query.filter_by(email=form.email.data).first()
        faculty = Faculty.query.filter_by(email=form.email.data).first()
        
        if student and bcrypt.check_password_hash(student.password, form.password.data):
            if not student.is_approved:
                flash('Your account has not been approved yet. Please wait for admin approval.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(student, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('student.dashboard'))
        elif faculty and bcrypt.check_password_hash(faculty.password, form.password.data):
            if not faculty.is_approved:
                flash('Your account has not been approved yet. Please wait for admin approval.', 'warning')
                return redirect(url_for('auth.login'))
            login_user(faculty, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('faculty.dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    
    return render_template('login.html', title='Login', form=form)

@auth.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = AdminLoginForm()
    if form.validate_on_submit():
        admin = Admin.query.filter_by(email=form.email.data).first()
        if admin and bcrypt.check_password_hash(admin.password, form.password.data):
            login_user(admin, remember=form.remember.data)
            next_page = request.args.get('next')
            return redirect(next_page) if next_page else redirect(url_for('admin.dashboard'))
        else:
            flash('Login unsuccessful. Please check email and password', 'danger')
    
    return render_template('admin_login.html', title='Admin Login', form=form)

@auth.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = StudentRegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            # Create a new student user
            student = Student(
                name=form.name.data,
                email=form.email.data,
                roll_number=form.roll_number.data,
                department=form.department.data,
                year=int(form.year.data),
                password=hashed_password,
                is_approved=False  # Wait for admin approval
            )
            
            # Process face data if provided
            if form.face_data.data:
                try:
                    # Create face_data directory if it doesn't exist
                    if not os.path.exists('face_data'):
                        os.makedirs('face_data')
                    
                    # Save the face data for the student
                    face_data_path = os.path.join('face_data', f"student_{form.roll_number.data}.jpg")
                    
                    # Use utility function to convert base64 to image and save
                    image = base64_to_image(form.face_data.data, face_data_path)
                    
                    if image and DEEPFACE_AVAILABLE:
                        # Generate face embedding using DeepFace
                        embedding = generate_face_embedding(face_data_path)
                        if embedding is not None:
                            student.set_face_encoding(np.array(embedding))
                            logger.info(f"Face encoding generated for student {form.roll_number.data}")
                        else:
                            flash('No face detected in the image. Please try again.', 'danger')
                            return render_template('register.html', title='Register', form=form)
                    else:
                        # If DeepFace is not available, still save the image but don't generate embedding
                        logger.warning("DeepFace not available, skipping face encoding generation")
                        flash('Face image saved, but face recognition features may be limited.', 'warning')
                
                except Exception as e:
                    logger.error(f"Error processing face data: {str(e)}")
                    flash('Error processing face data. Please try again.', 'danger')
                    return render_template('register.html', title='Register', form=form)
            
            # Save the student to the database
            db.session.add(student)
            db.session.commit()
            
            # Send notification email to admin (in a production environment)
            # notify_admin_about_new_registration(student)
            
            flash('Your account has been created! Please wait for admin approval before logging in.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during student registration: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('register.html', title='Register', form=form)

@auth.route('/faculty/register', methods=['GET', 'POST'])
def faculty_register():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = FacultyRegistrationForm()
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            
            # Create a new faculty user
            faculty = Faculty(
                name=form.name.data,
                email=form.email.data,
                department=form.department.data,
                password=hashed_password,
                is_approved=False  # Wait for admin approval
            )
            
            # Save the faculty to the database
            db.session.add(faculty)
            db.session.commit()
            
            flash('Your faculty account has been created! Please wait for admin approval before logging in.', 'success')
            return redirect(url_for('auth.login'))
        
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error during faculty registration: {str(e)}")
            flash('An error occurred during registration. Please try again.', 'danger')
    
    return render_template('faculty_register.html', title='Faculty Registration', form=form)

@auth.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('main.home'))

@auth.route('/forgot-password', methods=['GET', 'POST'])
def forgot_password():
    if current_user.is_authenticated:
        return redirect(url_for('main.home'))
    
    form = ForgotPasswordForm()
    if form.validate_on_submit():
        # Check if email exists in Student or Faculty database
        student = Student.query.filter_by(email=form.email.data).first()
        faculty = Faculty.query.filter_by(email=form.email.data).first()
        
        if student or faculty:
            # Log this request
            logger.info(f"Password reset requested for email: {form.email.data}")
            
            flash('Please contact your administrator to reset your password.', 'info')
            return redirect(url_for('auth.login'))
        else:
            flash('No account found with that email address.', 'danger')
    
    return render_template('forgot_password.html', title='Forgot Password', form=form)

@auth.route('/oauth/google')
def google_login():
    # This would typically use OAuth for Google authentication
    # For this implementation, we'll simulate the process
    flash('Google OAuth login is not implemented in this demo version.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/oauth/google/callback')
def google_callback():
    # This would handle the OAuth callback
    # For this implementation, we'll simulate the process
    flash('Google OAuth callback is not implemented in this demo version.', 'info')
    return redirect(url_for('auth.login'))

@auth.route('/capture_face', methods=['POST'])
def capture_face():
    try:
        # Get the image data from the request
        image_data = request.json.get('image_data')
        
        if not image_data:
            return jsonify({'success': False, 'message': 'No image data received'})
        
        # Process the image to detect faces
        try:
            # Convert base64 to image and save temporarily
            temp_path = 'temp_face.jpg'
            image = base64_to_image(image_data, temp_path)
            
            if not image:
                return jsonify({'success': False, 'message': 'Error processing image data'})
            
            # Use utility function to detect faces
            face_objs = extract_faces_from_image(temp_path)
            
            # Clean up temporary file
            if os.path.exists(temp_path):
                os.remove(temp_path)
            
            # Check if face was detected
            if not face_objs:
                return jsonify({'success': False, 'message': 'No face detected in the image. Please try again.'})
            
            return jsonify({'success': True, 'message': 'Face captured successfully'})
            
        except Exception as e:
            logger.error(f"Error processing captured face: {str(e)}")
            return jsonify({'success': False, 'message': f'Error processing face: {str(e)}'})
        
    except Exception as e:
        logger.error(f"Error in capture_face endpoint: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
