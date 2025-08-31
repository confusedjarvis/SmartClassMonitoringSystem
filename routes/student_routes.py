from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_required, current_user
from app import db
from models.models import Student, Course, Attendance, student_course
from datetime import datetime, date
import calendar
import logging
import os
import base64
from PIL import Image
from io import BytesIO
import numpy as np
import cv2
from utils.deepface import represent

# Configure logger
logger = logging.getLogger(__name__)

student = Blueprint('student', __name__)

# Student role verification decorator
def student_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_id().startswith('student'):
            flash('You need to be a student to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@student.route('/dashboard')
@login_required
@student_required
def dashboard():
    student_id = int(current_user.get_id().split('_')[1])
    
    # Get the courses this student is enrolled in
    enrolled_courses = Course.query.join(
        student_course, Course.id == student_course.c.course_id
    ).filter(
        student_course.c.student_id == student_id
    ).all()
    
    # Get attendance summary for each course
    course_attendance = []
    total_classes = 0
    total_present = 0
    
    for course in enrolled_courses:
        attendances = Attendance.query.filter_by(
            student_id=student_id,
            course_id=course.id
        ).all()
        
        present_count = sum(1 for a in attendances if a.is_present)
        course_total = len(attendances)
        
        # Calculate attendance percentage
        attendance_percentage = (present_count / course_total * 100) if course_total > 0 else 0
        
        # Determine status (good or bad attendance)
        status = 'good' if attendance_percentage >= 75 else 'bad'
        
        course_attendance.append({
            'course_id': course.id,
            'course_code': course.course_code,
            'course_name': course.name,
            'present_count': present_count,
            'total_classes': course_total,
            'attendance_percentage': attendance_percentage,
            'status': status
        })
        
        total_classes += course_total
        total_present += present_count
    
    # Calculate overall attendance percentage
    overall_percentage = (total_present / total_classes * 100) if total_classes > 0 else 0
    
    # Get today's classes
    today = datetime.now().strftime('%A')  # e.g., 'Monday'
    todays_timetable = []
    
    for course in enrolled_courses:
        # Get the timetable entries for this course on the current day
        from models.models import TimeTable
        timetables = TimeTable.query.filter_by(
            course_id=course.id,
            day=today
        ).order_by(TimeTable.start_time).all()
        
        for tt in timetables:
            # Check if attendance has been marked
            attendance = Attendance.query.filter_by(
                student_id=student_id,
                course_id=course.id,
                timetable_id=tt.id,
                date=date.today()
            ).first()
            
            # Get faculty name
            from models.models import Faculty
            faculty = Faculty.query.get(tt.faculty_id)
            
            todays_timetable.append({
                'course_code': course.course_code,
                'course_name': course.name,
                'start_time': tt.start_time.strftime('%H:%M'),
                'end_time': tt.end_time.strftime('%H:%M'),
                'room': tt.room,
                'faculty_name': faculty.name if faculty else 'Unknown',
                'attendance_marked': attendance is not None,
                'is_present': attendance.is_present if attendance else False
            })
    
    return render_template('student/dashboard.html',
                          title='Student Dashboard',
                          course_attendance=course_attendance,
                          overall_percentage=overall_percentage,
                          todays_timetable=todays_timetable)

@student.route('/courses')
@login_required
@student_required
def courses():
    student_id = int(current_user.get_id().split('_')[1])
    
    # Get the courses this student is enrolled in
    enrolled_courses = Course.query.join(
        student_course, Course.id == student_course.c.course_id
    ).filter(
        student_course.c.student_id == student_id
    ).all()
    
    courses_data = []
    
    for course in enrolled_courses:
        # Get the timetable entries for this course
        from models.models import TimeTable, Faculty
        timetables = TimeTable.query.filter_by(course_id=course.id).all()
        
        schedule = []
        for tt in timetables:
            faculty = Faculty.query.get(tt.faculty_id)
            
            schedule.append({
                'day': tt.day,
                'start_time': tt.start_time.strftime('%H:%M'),
                'end_time': tt.end_time.strftime('%H:%M'),
                'room': tt.room,
                'faculty_name': faculty.name if faculty else 'Unknown'
            })
        
        courses_data.append({
            'course_id': course.id,
            'course_code': course.course_code,
            'course_name': course.name,
            'credits': course.credits,
            'department': course.department,
            'schedule': schedule
        })
    
    return render_template('student/courses.html',
                          title='My Courses',
                          courses=courses_data)

@student.route('/attendance')
@login_required
@student_required
def attendance():
    student_id = int(current_user.get_id().split('_')[1])
    
    # Get the courses this student is enrolled in
    enrolled_courses = Course.query.join(
        student_course, Course.id == student_course.c.course_id
    ).filter(
        student_course.c.student_id == student_id
    ).all()
    
    # Get selected course (default to first course)
    course_id = request.args.get('course_id', type=int)
    if not course_id and enrolled_courses:
        course_id = enrolled_courses[0].id
    
    # Initialize data for chart
    months = list(calendar.month_abbr)[1:]  # Jan, Feb, ...
    monthly_attendance = {month: {'present': 0, 'absent': 0} for month in months}
    
    # Get attendance data for selected course
    attendance_records = []
    selected_course = None
    
    if course_id:
        selected_course = Course.query.get(course_id)
        
        if selected_course:
            attendances = Attendance.query.filter_by(
                student_id=student_id,
                course_id=course_id
            ).order_by(Attendance.date.desc()).all()
            
            # Process each attendance record
            for attendance in attendances:
                # Get timetable details
                from models.models import TimeTable
                timetable = TimeTable.query.get(attendance.timetable_id)
                
                # Format for display
                attendance_records.append({
                    'date': attendance.date.strftime('%Y-%m-%d'),
                    'day': attendance.date.strftime('%A'),
                    'is_present': attendance.is_present,
                    'time_in': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None,
                    'time_out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else None,
                    'room': timetable.room if timetable else 'Unknown'
                })
                
                # Update monthly data for chart
                month = calendar.month_abbr[attendance.date.month]
                if attendance.is_present:
                    monthly_attendance[month]['present'] += 1
                else:
                    monthly_attendance[month]['absent'] += 1
    
    # Calculate attendance stats
    attendance_stats = None
    if selected_course:
        attendances = Attendance.query.filter_by(
            student_id=student_id,
            course_id=course_id
        ).all()
        
        present_count = sum(1 for a in attendances if a.is_present)
        total_count = len(attendances)
        
        attendance_percentage = (present_count / total_count * 100) if total_count > 0 else 0
        attendance_status = 'Good' if attendance_percentage >= 75 else 'Poor'
        
        attendance_stats = {
            'present_count': present_count,
            'total_count': total_count,
            'attendance_percentage': attendance_percentage,
            'status': attendance_status
        }
    
    # Format chart data
    chart_data = {
        'labels': months,
        'present': [monthly_attendance[month]['present'] for month in months],
        'absent': [monthly_attendance[month]['absent'] for month in months]
    }
    
    return render_template('student/attendance.html',
                          title='My Attendance',
                          courses=enrolled_courses,
                          selected_course=selected_course,
                          attendance_records=attendance_records,
                          attendance_stats=attendance_stats,
                          chart_data=chart_data)

@student.route('/profile')
@login_required
@student_required
def profile():
    student_id = int(current_user.get_id().split('_')[1])
    student = Student.query.get(student_id)
    
    # Check if face data exists
    has_face_data = student.face_encoding is not None
    
    # Initialize forms
    from utils.forms import ChangePasswordForm, UpdateFaceForm
    password_form = ChangePasswordForm()
    face_form = UpdateFaceForm()
    
    return render_template('student/profile.html',
                          title='My Profile',
                          student=student,
                          has_face_data=has_face_data,
                          password_form=password_form,
                          face_form=face_form)

@student.route('/change_password', methods=['POST'])
@login_required
@student_required
def change_password():
    from app import bcrypt
    from utils.forms import ChangePasswordForm
    form = ChangePasswordForm()
    if form.validate_on_submit():
        student_id = int(current_user.get_id().split('_')[1])
        student = Student.query.get(student_id)
        
        # Verify current password
        if bcrypt.check_password_hash(student.password, form.current_password.data):
            # Hash new password
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            student.password = hashed_password
            db.session.commit()
            
            flash('Your password has been updated!', 'success')
        else:
            flash('Current password is incorrect. Please try again.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('student.profile'))

@student.route('/update_face', methods=['POST'])
@login_required
@student_required
def update_face():
    from utils.forms import UpdateFaceForm
    form = UpdateFaceForm()
    if form.validate_on_submit():
        try:
            # Get student
            student_id = int(current_user.get_id().split('_')[1])
            student = Student.query.get(student_id)
            
            # Process face data
            face_data = form.face_data.data
            if face_data:
                # Decode the base64 image
                image_data = face_data.split(',')[1]
                image_bytes = base64.b64decode(image_data)
                nparr = np.frombuffer(image_bytes, np.uint8)
                image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
                
                # Save the image
                face_data_path = os.path.join('face_data', f"student_{student.roll_number}.jpg")
                if not os.path.exists('face_data'):
                    os.makedirs('face_data')
                cv2.imwrite(face_data_path, image)
                
                # Generate face encoding using DeepFace
                try:
                    from utils.deepface import represent
                    face_objs = represent(image, model_name="VGG-Face", enforce_detection=True, detector_backend="opencv")
                    
                    if face_objs:
                        face_encoding = face_objs[0]['embedding']
                        student.set_face_encoding(face_encoding)
                        
                        # Set approval status to false, requiring admin to approve again
                        student.is_approved = False
                        db.session.commit()
                        
                        logger.info(f"Face encoding updated for student {student.roll_number}")
                        flash('Your face biometric has been updated! Please wait for admin approval before it becomes active.', 'success')
                    else:
                        flash('No face detected in the image. Please try again.', 'danger')
                except Exception as e:
                    logger.error(f"Error processing face: {str(e)}")
                    flash('Error processing face. Please try again with a clearer photo.', 'danger')
            else:
                flash('No face data provided. Please try again.', 'danger')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error updating face data: {str(e)}")
            flash(f'An error occurred: {str(e)}', 'danger')
    
    return redirect(url_for('student.profile'))
