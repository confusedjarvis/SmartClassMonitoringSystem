from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_required, current_user
from app import db, bcrypt
from models.models import Student, Faculty, Course, TimeTable, Attendance, student_course
from utils.forms import ManualAttendanceForm
from utils.advanced_face_recognition import process_attendance_image, load_student_embeddings
from datetime import datetime, date, time
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

# Import DeepFace with proper error handling
try:
    from deepface import DeepFace
    DEEPFACE_AVAILABLE = True
    logger.info("DeepFace imported successfully in faculty_routes")
except ImportError as e:
    DEEPFACE_AVAILABLE = False
    logger.error(f"Error importing DeepFace in faculty_routes: {str(e)}")

faculty = Blueprint('faculty', __name__)

# Faculty role verification decorator
def faculty_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_id().startswith('faculty'):
            flash('You need to be a faculty member to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@faculty.route('/dashboard')
@login_required
@faculty_required
def dashboard():
    # Get today's day name
    today = datetime.now().strftime('%A')
    
    # Get today's timetable for the faculty
    todays_classes = TimeTable.query.filter_by(
        faculty_id=int(current_user.get_id().split('_')[1]),
        day=today
    ).order_by(TimeTable.start_time).all()
    
    # Check if any class is currently ongoing
    now = datetime.now().time()
    current_class = None
    upcoming_classes = []
    
    for class_session in todays_classes:
        if class_session.start_time <= now <= class_session.end_time:
            current_class = class_session
        elif class_session.start_time > now:
            upcoming_classes.append(class_session)
    
    # Get overall stats
    total_students = db.session.query(Student).join(
        student_course, student_course.c.student_id == Student.id
    ).join(
        Course, Course.id == student_course.c.course_id
    ).join(
        TimeTable, TimeTable.course_id == Course.id
    ).filter(
        TimeTable.faculty_id == int(current_user.get_id().split('_')[1])
    ).distinct().count()
    
    total_courses = TimeTable.query.filter_by(
        faculty_id=int(current_user.get_id().split('_')[1])
    ).join(Course).distinct(Course.id).count()
    
    return render_template('faculty/dashboard.html', 
                          title='Faculty Dashboard',
                          today=today,
                          current_class=current_class,
                          upcoming_classes=upcoming_classes,
                          total_students=total_students,
                          total_courses=total_courses)

@faculty.route('/courses')
@login_required
@faculty_required
def courses():
    # Get all courses taught by this faculty
    faculty_id = int(current_user.get_id().split('_')[1])
    
    # Get the faculty's department to properly manage courses
    faculty_object = Faculty.query.get(faculty_id)
    faculty_department = faculty_object.department if faculty_object else None
    
    faculty_timetables = TimeTable.query.filter_by(faculty_id=faculty_id).all()
    
    # Create a dictionary using both course_id and department to distinguish same courses in different departments
    courses_dict = {}
    
    for tt in faculty_timetables:
        course = Course.query.get(tt.course_id)
        # Create a compound key with course_id and department
        compound_key = f"{course.id}_{course.department}"
        
        if compound_key not in courses_dict:
            courses_dict[compound_key] = {
                'course': course,
                'schedule': []
            }
        
        # Include the timetable ID in the schedule data
        courses_dict[compound_key]['schedule'].append({
            'id': tt.id,  # Add the timetable ID here
            'day': tt.day,
            'start_time': tt.start_time.strftime('%H:%M'),
            'end_time': tt.end_time.strftime('%H:%M'),
            'room': tt.room
        })
    
    return render_template('faculty/courses.html', 
                          title='My Courses',
                          courses=courses_dict)

@faculty.route('/start_session/<int:timetable_id>')
@login_required
@faculty_required
def start_session(timetable_id):
    # Get the timetable entry
    timetable = TimeTable.query.get_or_404(timetable_id)
    
    # Verify this timetable belongs to the current faculty
    faculty_id = int(current_user.get_id().split('_')[1])
    if timetable.faculty_id != faculty_id:
        flash('You do not have permission to start this session.', 'danger')
        return redirect(url_for('faculty.dashboard'))
    
    # Get the course and enrolled students
    course = Course.query.get(timetable.course_id)
    
    # Get students only from the same department as the course
    students = Student.query.filter_by(department=course.department).join(
        student_course, Student.id == student_course.c.student_id
    ).filter(
        student_course.c.course_id == course.id
    ).all()
    
    # Check if attendance has already been marked for today
    today = date.today()
    for student in students:
        existing_attendance = Attendance.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            timetable_id=timetable.id,
            date=today
        ).first()
        
        if not existing_attendance:
            # Create new attendance record (marked as absent by default)
            attendance = Attendance(
                student_id=student.id,
                course_id=course.id,
                timetable_id=timetable.id,
                date=today,
                is_present=False,
                marked_by=current_user.email
            )
            db.session.add(attendance)
    
    db.session.commit()
    
    # Redirect to the attendance taking page
    return redirect(url_for('faculty.take_attendance', timetable_id=timetable_id))

@faculty.route('/take_attendance/<int:timetable_id>')
@login_required
@faculty_required
def take_attendance(timetable_id):
    # Get the timetable entry
    timetable = TimeTable.query.get_or_404(timetable_id)
    
    # Verify this timetable belongs to the current faculty
    faculty_id = int(current_user.get_id().split('_')[1])
    if timetable.faculty_id != faculty_id:
        flash('You do not have permission to manage this session.', 'danger')
        return redirect(url_for('faculty.dashboard'))
    
    # Get the course and today's attendance records
    course = Course.query.get(timetable.course_id)
    today = date.today()
    
    attendance_records = Attendance.query.filter_by(
        course_id=course.id,
        timetable_id=timetable.id,
        date=today
    ).all()
    
    student_attendance = []
    for record in attendance_records:
        student = Student.query.get(record.student_id)
        # Only include students from the same department as the course
        if student.department == course.department:
            student_attendance.append({
                'attendance_id': record.id,
                'student_id': student.id,
                'student_name': student.name,
                'roll_number': student.roll_number,
                'is_present': record.is_present,
                'time_in': record.time_in.strftime('%H:%M:%S') if record.time_in else None,
                'time_out': record.time_out.strftime('%H:%M:%S') if record.time_out else None
            })
    
    return render_template('faculty/take_attendance.html',
                          title='Take Attendance',
                          timetable=timetable,
                          course=course,
                          student_attendance=student_attendance)

@faculty.route('/manual_attendance/<int:timetable_id>', methods=['GET', 'POST'])
@login_required
@faculty_required
def manual_attendance(timetable_id):
    # Get the timetable entry
    timetable = TimeTable.query.get_or_404(timetable_id)
    
    # Verify this timetable belongs to the current faculty
    faculty_id = int(current_user.get_id().split('_')[1])
    if timetable.faculty_id != faculty_id:
        flash('You do not have permission to manage this session.', 'danger')
        return redirect(url_for('faculty.dashboard'))
    
    # Get the course and enrolled students
    course = Course.query.get(timetable.course_id)
    
    # Only show students from the same department as the course and same year
    students = Student.query.filter_by(
        department=course.department,
        year=timetable.year
    ).join(
        student_course, Student.id == student_course.c.student_id
    ).filter(
        student_course.c.course_id == course.id
    ).all()
    
    # Get today's attendance records
    today = date.today()
    attendance_records = {}
    
    for student in students:
        attendance = Attendance.query.filter_by(
            student_id=student.id,
            course_id=course.id,
            timetable_id=timetable.id,
            date=today
        ).first()
        
        attendance_records[student.id] = {
            'record': attendance,
            'student': student
        }
    
    form = ManualAttendanceForm()
    form.student_id.choices = [(s.id, f"{s.roll_number} - {s.name} ({s.department})") for s in students]
    
    if form.validate_on_submit():
        student_id = form.student_id.data
        is_present = form.is_present.data
        
        attendance = attendance_records[student_id]['record']
        if not attendance:
            # Create new attendance record if it doesn't exist
            attendance = Attendance(
                student_id=student_id,
                course_id=course.id,
                timetable_id=timetable.id,
                date=today,
                is_present=is_present,
                marked_by=current_user.email
            )
            db.session.add(attendance)
        else:
            # Update existing record
            attendance.is_present = is_present
            attendance.marked_by = current_user.email
            
        if is_present and not attendance.time_in:
            attendance.time_in = datetime.now()
        
        db.session.commit()
        flash(f"Attendance for {attendance_records[student_id]['student'].name} marked successfully!", 'success')
        return redirect(url_for('faculty.manual_attendance', timetable_id=timetable_id))
    
    return render_template('faculty/manual_attendance.html',
                         title='Manual Attendance',
                         form=form,
                         timetable=timetable,
                         course=course,
                         attendance_records=attendance_records)

@faculty.route('/auto_attendance/<int:timetable_id>', methods=['GET', 'POST'])
@login_required
@faculty_required
def auto_attendance(timetable_id):
    # Get the timetable entry
    timetable = TimeTable.query.get_or_404(timetable_id)
    
    # Verify this timetable belongs to the current faculty
    faculty_id = int(current_user.get_id().split('_')[1])
    if timetable.faculty_id != faculty_id:
        flash('You do not have permission to manage this session.', 'danger')
        return redirect(url_for('faculty.dashboard'))
    
    # Get the course
    course = Course.query.get(timetable.course_id)
    
    if request.method == 'POST':
        try:
            # Get the image data from the request
            image_data = request.json.get('image_data')
            
            if not image_data:
                return jsonify({'success': False, 'message': 'No image data received'})
            
            # Load student embeddings database - using students from the correct department and year
            students = Student.query.filter_by(
                department=course.department,
                year=timetable.year
            ).join(
                student_course, Student.id == student_course.c.student_id
            ).filter(
                student_course.c.course_id == course.id
            ).all()
            
            # Create a temporary database mapping with student IDs
            student_db = {}
            face_data_dir = 'face_data'  # Directory where face images are stored
            
            # First load all student embeddings from the face_data directory
            raw_embeddings = load_student_embeddings(face_data_dir)
            
            # Filter to only include students in this course/department/year
            for student in students:
                roll_number = student.roll_number
                if roll_number in raw_embeddings:
                    student_db[roll_number] = raw_embeddings[roll_number]
            
            # Get today's date
            today = date.today()
            
            # Process the image and recognize students
            recognized_students, annotated_image = process_attendance_image(image_data, student_db)
            
            if not recognized_students:
                return jsonify({
                    'success': True,
                    'message': 'No students recognized in the image.',
                    'recognized_students': [],
                    'annotated_image': annotated_image
                })
            
            # Mark attendance for recognized students
            marked_students = []
            for recognition in recognized_students:
                roll_number = recognition['student_id']
                confidence = recognition['confidence']
                
                # Find the student in the database
                student = Student.query.filter_by(roll_number=roll_number).first()
                
                if student:
                    # Check if attendance record exists
                    attendance = Attendance.query.filter_by(
                        student_id=student.id,
                        course_id=course.id,
                        timetable_id=timetable.id,
                        date=today
                    ).first()
                    
                    if attendance:
                        attendance.is_present = True
                        attendance.marked_by = 'auto'
                        if not attendance.time_in:
                            attendance.time_in = datetime.now()
                    else:
                        # Create new attendance record
                        attendance = Attendance(
                            student_id=student.id,
                            course_id=course.id,
                            timetable_id=timetable.id,
                            date=today,
                            is_present=True,
                            marked_by='auto',
                            time_in=datetime.now()
                        )
                        db.session.add(attendance)
                    
                    marked_students.append({
                        'id': student.id,
                        'name': student.name,
                        'roll_number': student.roll_number,
                        'confidence': f"{confidence:.2f}"
                    })
            
            # Commit the database changes
            db.session.commit()
            
            return jsonify({
                'success': True,
                'message': f'Successfully recognized {len(marked_students)} students',
                'recognized_students': marked_students,
                'annotated_image': annotated_image
            })
                
        except Exception as e:
            logger.error(f"Error in auto_attendance endpoint: {str(e)}")
            return jsonify({'success': False, 'message': f'Error: {str(e)}'})
    
    # If GET request, render the auto attendance page
    return render_template('faculty/auto_attendance.html',
                          title='Automatic Attendance',
                          timetable=timetable,
                          course=course,
                          current_datetime=datetime.now())

@faculty.route('/attendance/report')
@login_required
@faculty_required
def attendance_report():
    faculty_id = int(current_user.get_id().split('_')[1])
    faculty_object = Faculty.query.get(faculty_id)
    faculty_department = faculty_object.department if faculty_object else None
    
    # Get all courses taught by this faculty
    timetables = TimeTable.query.filter_by(faculty_id=faculty_id).all()
    courses = {}
    
    for tt in timetables:
        course = Course.query.get(tt.course_id)
        # Use compound key to distinguish same course codes in different departments
        key = f"{course.id}_{course.department}"
        if key not in courses:
            courses[key] = course
    
    # Default to first course if no course_id is provided
    course_id = request.args.get('course_id', type=int)
    if not course_id and courses:
        course_id = list(courses.values())[0].id
    
    attendance_data = []
    course_name = ""
    
    if course_id:
        course = Course.query.get(course_id)
        if course:
            course_name = f"{course.course_code} - {course.name} ({course.department})"
            
            # Get all students enrolled in this course, filtered by department
            students = Student.query.filter_by(department=course.department).join(
                student_course, Student.id == student_course.c.student_id
            ).filter(
                student_course.c.course_id == course_id
            ).all()
            
            # Get attendance data for each student
            for student in students:
                attendances = Attendance.query.filter_by(
                    student_id=student.id, 
                    course_id=course_id
                ).all()
                
                present_count = sum(1 for a in attendances if a.is_present)
                total_count = len(attendances)
                attendance_percentage = (present_count / total_count * 100) if total_count > 0 else 0
                
                low_attendance = attendance_percentage < 75
                
                attendance_data.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'roll_number': student.roll_number,
                    'present_count': present_count,
                    'total_classes': total_count,
                    'attendance_percentage': attendance_percentage,
                    'low_attendance': low_attendance
                })
    
    return render_template('faculty/attendance_report.html',
                          title='Attendance Report',
                          courses=courses.values(),
                          selected_course_id=course_id,
                          course_name=course_name,
                          attendance_data=attendance_data)

@faculty.route('/profile')
@login_required
@faculty_required
def profile():
    faculty_id = int(current_user.get_id().split('_')[1])
    faculty = Faculty.query.get(faculty_id)
    
    # Initialize password form
    from utils.forms import ChangePasswordForm
    password_form = ChangePasswordForm()
    
    return render_template('faculty/profile.html',
                          title='Faculty Profile',
                          faculty=faculty,
                          password_form=password_form)

@faculty.route('/change_password', methods=['POST'])
@login_required
@faculty_required
def change_password():
    from utils.forms import ChangePasswordForm
    form = ChangePasswordForm()
    if form.validate_on_submit():
        faculty_id = int(current_user.get_id().split('_')[1])
        faculty = Faculty.query.get(faculty_id)
        
        # Verify current password
        if bcrypt.check_password_hash(faculty.password, form.current_password.data):
            # Hash new password
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            faculty.password = hashed_password
            db.session.commit()
            
            flash('Your password has been updated!', 'success')
        else:
            flash('Current password is incorrect. Please try again.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('faculty.profile'))

@faculty.route('/attendance/details/<int:student_id>/<int:course_id>')
@login_required
@faculty_required
def attendance_details(student_id, course_id):
    faculty_id = int(current_user.get_id().split('_')[1])
    
    # Check if this faculty teaches this course
    teaches_course = TimeTable.query.filter_by(
        faculty_id=faculty_id,
        course_id=course_id
    ).first() is not None
    
    if not teaches_course:
        flash('You do not have permission to view this data.', 'danger')
        return redirect(url_for('faculty.attendance_report'))
    
    student = Student.query.get_or_404(student_id)
    course = Course.query.get_or_404(course_id)
    
    # Get detailed attendance for this student in this course
    attendances = Attendance.query.filter_by(
        student_id=student_id,
        course_id=course_id
    ).order_by(Attendance.date.desc()).all()
    
    attendance_details = []
    for attendance in attendances:
        timetable = TimeTable.query.get(attendance.timetable_id)
        
        attendance_details.append({
            'date': attendance.date.strftime('%Y-%m-%d'),
            'day': attendance.date.strftime('%A'),
            'is_present': attendance.is_present,
            'time_in': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None,
            'time_out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else None,
            'room': timetable.room,
            'marked_by': attendance.marked_by
        })
    
    return render_template('faculty/attendance_details.html',
                         title=f'Attendance Details - {student.name}',
                         student=student,
                         course=course,
                         attendance_details=attendance_details)

@faculty.route('/mark_attendance/<int:attendance_id>/<int:status>', methods=['POST'])
@login_required
@faculty_required
def mark_attendance(attendance_id, status):
    try:
        # Get the attendance record
        attendance = Attendance.query.get_or_404(attendance_id)
        
        # Verify this attendance belongs to a course/timetable assigned to the current faculty
        faculty_id = int(current_user.get_id().split('_')[1])
        timetable = TimeTable.query.get_or_404(attendance.timetable_id)
        
        if timetable.faculty_id != faculty_id:
            return jsonify({'success': False, 'message': 'You do not have permission to modify this attendance record'})
        
        # Update the attendance status
        attendance.is_present = bool(status)
        attendance.marked_by = current_user.email
        
        # Update time_in if marking present and not already set
        if bool(status) and not attendance.time_in:
            attendance.time_in = datetime.now()
        
        db.session.commit()
        
        return jsonify({
            'success': True, 
            'message': f"Student marked {'present' if bool(status) else 'absent'} successfully",
            'is_present': attendance.is_present,
            'time_in': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None
        })
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error updating attendance: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})

@faculty.route('/attendance/get_students/<int:timetable_id>', methods=['GET'])
@login_required
@faculty_required
def get_attendance_students(timetable_id):
    try:
        # Get the timetable entry
        timetable = TimeTable.query.get_or_404(timetable_id)
        
        # Verify this timetable belongs to the current faculty
        faculty_id = int(current_user.get_id().split('_')[1])
        if timetable.faculty_id != faculty_id:
            return jsonify({'success': False, 'message': 'You do not have permission to access this data'})
        
        # Get the course
        course = Course.query.get(timetable.course_id)
        
        # Get students enrolled in this course and from the same department
        students = Student.query.filter_by(department=course.department, year=timetable.year).join(
            student_course, Student.id == student_course.c.student_id
        ).filter(
            student_course.c.course_id == course.id
        ).all()
        
        # Get today's attendance records
        today = date.today()
        attendance_records = {}
        
        for student in students:
            attendance = Attendance.query.filter_by(
                student_id=student.id,
                course_id=course.id,
                timetable_id=timetable.id,
                date=today
            ).first()
            
            # Create a record if it doesn't exist
            if not attendance:
                attendance = Attendance(
                    student_id=student.id,
                    course_id=course.id,
                    timetable_id=timetable.id,
                    date=today,
                    is_present=False,
                    marked_by=current_user.email
                )
                db.session.add(attendance)
                db.session.commit()
            
            attendance_records[student.id] = {
                'attendance_id': attendance.id,
                'is_present': attendance.is_present,
                'time_in': attendance.time_in.strftime('%H:%M:%S') if attendance.time_in else None,
                'time_out': attendance.time_out.strftime('%H:%M:%S') if attendance.time_out else None
            }
        
        # Prepare student data for the response
        student_data = [{
            'id': student.id,
            'name': student.name,
            'roll_number': student.roll_number,
            'attendance_id': attendance_records[student.id]['attendance_id'],
            'is_present': attendance_records[student.id]['is_present'],
            'time_in': attendance_records[student.id]['time_in'],
            'time_out': attendance_records[student.id]['time_out']
        } for student in students]
        
        return jsonify({
            'success': True,
            'students': student_data,
            'course_name': f"{course.course_code} - {course.name}",
            'year': timetable.year
        })
        
    except Exception as e:
        logger.error(f"Error getting attendance students: {str(e)}")
        return jsonify({'success': False, 'message': f'Error: {str(e)}'})
