from flask import Blueprint, render_template, url_for, flash, redirect, request, jsonify
from flask_login import login_required, current_user
from app import db, bcrypt
from models.models import (
    Student, Faculty, Admin, Course, TimeTable, 
    Attendance, student_course, faculty_course, AdminLog
)
from utils.forms import CourseForm, TimeTableForm, ChangePasswordForm, AdminAddStudentForm, AdminAddFacultyForm, ResetPasswordForm
import random
import string
from datetime import datetime
import pandas as pd
import logging
import json
from sqlalchemy import and_, exc

# Configure logger
logger = logging.getLogger(__name__)

# Helper function to create an admin log entry
def create_admin_log(admin_user, action, details=None):
    try:
        # Get request IP if available
        ip_address = request.remote_addr if request and hasattr(request, 'remote_addr') else None
        
        # Create log entry
        admin_id = int(admin_user.get_id().split('_')[1])
        log_entry = AdminLog(
            admin_id=admin_id,
            admin_email=admin_user.email,
            action=action,
            details=details,
            ip_address=ip_address
        )
        
        db.session.add(log_entry)
        db.session.commit()
        logger.info(f"Admin log created: {action} by {admin_user.email}")
        
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error creating admin log: {str(e)}")

admin = Blueprint('admin', __name__)

# Admin role verification decorator
def admin_required(f):
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.get_id().startswith('admin'):
            flash('You need to be an administrator to access this page.', 'danger')
            return redirect(url_for('auth.login'))
        return f(*args, **kwargs)
    decorated_function.__name__ = f.__name__
    return decorated_function

@admin.route('/dashboard', methods=['GET', 'POST'])
@login_required
@admin_required
def dashboard():
    # Get counts for dashboard
    student_count = Student.query.count()
    faculty_count = Faculty.query.count()
    course_count = Course.query.count()
    pending_approvals = Student.query.filter_by(is_approved=False).count() + Faculty.query.filter_by(is_approved=False).count()
    
    # Get students with updated face biometrics needing approval
    biometric_updates = Student.query.filter_by(is_approved=False).filter(Student.face_encoding != None).all()
    
    # Recent registrations
    recent_students = Student.query.order_by(Student.created_at.desc()).limit(5).all()
    recent_faculty = Faculty.query.order_by(Faculty.created_at.desc()).limit(5).all()
    
    # Initialize forms for adding students and faculty
    add_student_form = AdminAddStudentForm()
    add_faculty_form = AdminAddFacultyForm()
    
    return render_template('admin/dashboard.html', 
                           title='Admin Dashboard',
                           student_count=student_count,
                           faculty_count=faculty_count,
                           course_count=course_count,
                           pending_approvals=pending_approvals,
                           recent_students=recent_students,
                           recent_faculty=recent_faculty,
                           biometric_updates=biometric_updates,
                           add_student_form=add_student_form,
                           add_faculty_form=add_faculty_form)

@admin.route('/students')
@login_required
@admin_required
def students():
    page = request.args.get('page', 1, type=int)
    students = Student.query.order_by(Student.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/students.html', title='Manage Students', students=students)

@admin.route('/faculties')
@login_required
@admin_required
def faculties():
    page = request.args.get('page', 1, type=int)
    faculties = Faculty.query.order_by(Faculty.created_at.desc()).paginate(page=page, per_page=10)
    return render_template('admin/faculties.html', title='Manage Faculty', faculties=faculties)

@admin.route('/reset_password', methods=['GET', 'POST'])
@login_required
@admin_required
def reset_password():
    form = ResetPasswordForm()
    
    if form.validate_on_submit():
        try:
            # Find the user based on type and email
            if form.user_type.data == 'student':
                user = Student.query.filter_by(email=form.email.data).first()
                user_desc = f"Student: {user.name} ({user.roll_number})"
            else:
                user = Faculty.query.filter_by(email=form.email.data).first()
                user_desc = f"Faculty: {user.name} ({user.department})"
            
            if not user:
                flash(f'No {form.user_type.data} found with that email.', 'danger')
                return redirect(url_for('admin.reset_password'))
            
            # Generate and set new password
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            user.password = hashed_password
            
            # Save to database
            db.session.commit()
            
            # Log this action
            create_admin_log(
                current_user,
                f"Reset password for {form.user_type.data}",
                f"Reset password for {user_desc} (Email: {form.email.data})"
            )
            
            flash(f'Password has been reset for {user.name}.', 'success')
            return redirect(url_for('admin.dashboard'))
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error resetting password: {str(e)}")
            flash(f'Error resetting password: {str(e)}', 'danger')
    
    return render_template('admin/reset_password.html', title='Reset User Password', form=form)

@admin.route('/courses', methods=['GET', 'POST'])
@login_required
@admin_required
def courses():
    form = CourseForm()
    if form.validate_on_submit():
        try:
            # Check if this is an update
            is_update = request.form.get('is_update') == '1'
            course_id = request.form.get('course_id')
            
            if is_update and course_id:
                # Update existing course
                course = Course.query.get_or_404(course_id)
                
                # Check if course code changed and if it conflicts with another course
                if course.course_code != form.course_code.data or course.department != form.department.data:
                    existing_course = Course.query.filter(
                        Course.id != course.id,
                        Course.course_code == form.course_code.data,
                        Course.department == form.department.data
                    ).first()
                    
                    if existing_course:
                        flash(f'Course with code {form.course_code.data} already exists in {form.department.data} department!', 'danger')
                        return redirect(url_for('admin.courses'))
                
                # Update the course fields
                old_department = course.department
                old_year = course.year
                
                course.course_code = form.course_code.data
                course.name = form.name.data
                course.credits = form.credits.data
                course.department = form.department.data
                course.year = int(form.year.data)
                
                try:
                    db.session.commit()
                    flash(f'Course {form.name.data} ({form.course_code.data}) has been updated!', 'success')
                    
                    # If department or year changed, reassign students
                    if old_department != form.department.data or old_year != int(form.year.data):
                        # Remove all students from this course
                        students_enrolled = Student.query.join(student_course).filter(student_course.c.course_id == course.id).all()
                        for student in students_enrolled:
                            student.courses.remove(course)
                            
                        # Add new students based on new department and year
                        new_students = Student.query.filter_by(
                            department=form.department.data,
                            year=int(form.year.data)
                        ).all()
                        
                        for student in new_students:
                            student.courses.append(course)
                            
                        db.session.commit()
                        flash(f'Students have been reassigned to the updated course.', 'info')
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error updating course: {str(e)}")
                    flash(f'Error updating course: {str(e)}', 'danger')
            else:
                # Create new course
                # Check if the course with the same code already exists in this department
                existing_course = Course.query.filter_by(
                    course_code=form.course_code.data,
                    department=form.department.data
                ).first()
                
                if existing_course:
                    flash(f'Course with code {form.course_code.data} already exists in {form.department.data} department!', 'danger')
                    return redirect(url_for('admin.courses'))
                    
                # Create the new course
                course = Course(
                    course_code=form.course_code.data,
                    name=form.name.data,
                    credits=form.credits.data,
                    department=form.department.data,
                    year=int(form.year.data)
                )
                db.session.add(course)
                
                try:
                    db.session.commit()
                except exc.IntegrityError as e:
                    db.session.rollback()
                    if "UNIQUE constraint failed" in str(e):
                        flash(f'A course with code {form.course_code.data} already exists in the {form.department.data} department.', 'danger')
                    else:
                        flash(f'Database error: {str(e)}', 'danger')
                    return redirect(url_for('admin.courses'))
                
                # Auto-assign students from the same department and year to this course
                students = Student.query.filter_by(
                    department=form.department.data,
                    year=int(form.year.data)
                ).all()
                
                for student in students:
                    student.courses.append(course)
                
                try:
                    db.session.commit()
                    flash(f'Course {form.name.data} ({form.course_code.data}) has been added to the {form.department.data} department for year {form.year.data}!', 'success')
                except Exception as e:
                    db.session.rollback()
                    logger.error(f"Error assigning students to course: {str(e)}")
                    flash(f'Course was added but there was an error assigning students. Error: {str(e)}', 'warning')
            
            return redirect(url_for('admin.courses'))
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error processing course: {str(e)}")
            flash(f'Error processing course: {str(e)}', 'danger')
            return redirect(url_for('admin.courses'))
        
    page = request.args.get('page', 1, type=int)
    courses = Course.query.order_by(Course.department, Course.course_code).paginate(page=page, per_page=10)
    return render_template('admin/courses.html', title='Manage Courses', courses=courses, form=form)

@admin.route('/timetable', methods=['GET', 'POST'])
@login_required
@admin_required
def timetable():
    form = TimeTableForm()
    
    # Populate dropdown choices for courses - get courses for all departments
    form.course_id.choices = [(c.id, f"{c.course_code} - {c.name} ({c.department})") for c in Course.query.all()]
    
    # Populate dropdown choices for faculties
    form.faculty_id.choices = [(f.id, f"{f.name} ({f.department})") for f in Faculty.query.filter_by(is_approved=True).all()]
    
    if form.validate_on_submit():
        # Convert time strings to Time objects
        start_time = datetime.strptime(form.start_time.data, '%H:%M').time()
        end_time = datetime.strptime(form.end_time.data, '%H:%M').time()
        
        # Get the course to determine the department
        course = Course.query.get(form.course_id.data)
        
        # Check if faculty belongs to the same department as the course
        faculty = Faculty.query.get(form.faculty_id.data)
        
        # Check if this is an update
        is_update = request.form.get('is_update') == '1'
        timetable_id = request.form.get('timetable_id')
        
        if is_update and timetable_id:
            # Update existing timetable entry
            timetable_entry = TimeTable.query.get_or_404(timetable_id)
            
            # Check for conflicts with other entries, excluding this one
            conflicts = TimeTable.query.filter(
                TimeTable.id != timetable_id,
                TimeTable.day == form.day.data,
                TimeTable.faculty_id == form.faculty_id.data,
                TimeTable.year == int(form.year.data),
                TimeTable.start_time < end_time,
                TimeTable.end_time > start_time
            ).first()
            
            if conflicts:
                flash(f'There is a scheduling conflict with an existing class on {form.day.data} at {conflicts.start_time.strftime("%H:%M")} - {conflicts.end_time.strftime("%H:%M")}', 'danger')
                return redirect(url_for('admin.timetable'))
            
            # Update the entry
            timetable_entry.day = form.day.data
            timetable_entry.start_time = start_time
            timetable_entry.end_time = end_time
            timetable_entry.room = form.room.data
            timetable_entry.course_id = form.course_id.data
            timetable_entry.faculty_id = form.faculty_id.data
            timetable_entry.year = int(form.year.data)
            
            db.session.commit()
            flash('Timetable entry has been updated!', 'success')
            
        else:
            # Create a new timetable entry
            # Check if there's a conflict with existing timetable entries
            conflicts = TimeTable.query.filter_by(
                day=form.day.data,
                faculty_id=form.faculty_id.data,
                year=int(form.year.data)
            ).filter(
                TimeTable.start_time < end_time,
                TimeTable.end_time > start_time
            ).first()
            
            if conflicts:
                flash(f'There is a scheduling conflict with an existing class on {form.day.data} at {conflicts.start_time.strftime("%H:%M")} - {conflicts.end_time.strftime("%H:%M")}', 'danger')
                return redirect(url_for('admin.timetable'))
            
            # Create the timetable entry
            timetable_entry = TimeTable(
                day=form.day.data,
                start_time=start_time,
                end_time=end_time,
                room=form.room.data,
                course_id=form.course_id.data,
                faculty_id=form.faculty_id.data,
                year=int(form.year.data)
            )
            
            db.session.add(timetable_entry)
            db.session.commit()
            flash(f'Timetable entry has been added for {course.department} year {form.year.data}!', 'success')
        
        return redirect(url_for('admin.timetable'))
    
    # Get all timetable entries organized by day
    days = ['Monday', 'Tuesday', 'Wednesday', 'Thursday', 'Friday', 'Saturday']
    timetable_entries = {}
    
    for day in days:
        entries = TimeTable.query.filter_by(day=day).order_by(TimeTable.start_time).all()
        timetable_entries[day] = entries
    
    return render_template('admin/timetable.html', 
                          title='Manage Timetable', 
                          form=form, 
                          timetable_entries=timetable_entries,
                          days=days)

@admin.route('/approve/<user_type>/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def approve_user(user_type, user_id):
    if user_type == 'student':
        student = Student.query.get_or_404(user_id)
        student.is_approved = True
        
        # Automatically assign courses based on department and year
        department = student.department
        year = student.year
        courses = Course.query.filter_by(department=department).all()
        
        # Get currently enrolled courses to avoid duplicates
        enrolled_course_ids = [c.id for c in student.courses]
        
        for course in courses:
            # Only add course if student isn't already enrolled
            if course.id not in enrolled_course_ids:
                student.courses.append(course)
        
        try:
            db.session.commit()
            # Log this admin action
            create_admin_log(
                current_user,
                "Approved student account",
                f"Approved student: {student.name} ({student.roll_number})"
            )
            flash(f'Student {student.name} has been approved and assigned to courses!', 'success')
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error approving student: {str(e)}")
            flash(f'Error approving student: {str(e)}', 'danger')
            
        return redirect(url_for('admin.students'))
    elif user_type == 'faculty':
        faculty = Faculty.query.get_or_404(user_id)
        faculty.is_approved = True
        db.session.commit()
        
        # Log this admin action
        create_admin_log(
            current_user,
            "Approved faculty account",
            f"Approved faculty: {faculty.name} ({faculty.department})"
        )
        
        flash(f'Faculty {faculty.name} has been approved!', 'success')
        return redirect(url_for('admin.faculties'))
    else:
        flash('Invalid user type', 'danger')
        return redirect(url_for('admin.dashboard'))

@admin.route('/delete/<user_type>/<int:user_id>', methods=['POST'])
@login_required
@admin_required
def delete_user(user_type, user_id):
    try:
        if user_type == 'student':
            user = Student.query.get_or_404(user_id)
            
            # Delete student attendances
            Attendance.query.filter_by(student_id=user_id).delete()
            
            # Remove student from courses
            db.session.execute(student_course.delete().where(student_course.c.student_id == user_id))
            
            # Delete the student
            db.session.delete(user)
            db.session.commit()
            
            flash(f'Student {user.name} has been deleted!', 'success')
            return redirect(url_for('admin.students'))
            
        elif user_type == 'faculty':
            user = Faculty.query.get_or_404(user_id)
            
            # Check if faculty has timetable entries
            timetables = TimeTable.query.filter_by(faculty_id=user_id).all()
            
            if timetables:
                # For each timetable, delete associated attendances first
                for timetable in timetables:
                    # Delete attendances for this timetable
                    Attendance.query.filter_by(timetable_id=timetable.id).delete()
                
                # Delete all timetable entries for this faculty
                TimeTable.query.filter_by(faculty_id=user_id).delete()
            
            # Remove faculty from courses
            db.session.execute(faculty_course.delete().where(faculty_course.c.faculty_id == user_id))
            
            # Delete the faculty
            db.session.delete(user)
            db.session.commit()
            
            flash(f'Faculty {user.name} has been deleted!', 'success')
            return redirect(url_for('admin.faculties'))
        else:
            flash('Invalid user type', 'danger')
            return redirect(url_for('admin.dashboard'))
            
    except Exception as e:
        db.session.rollback()
        logger.error(f"Error deleting {user_type}: {str(e)}")
        flash(f'Error deleting {user_type}: {str(e)}', 'danger')
        
        if user_type == 'student':
            return redirect(url_for('admin.students'))
        else:
            return redirect(url_for('admin.faculties'))

@admin.route('/delete/course/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    try:
        course = Course.query.get_or_404(course_id)
        
        # Delete all timetable entries for this course
        timetables = TimeTable.query.filter_by(course_id=course_id).all()
        for timetable in timetables:
            # Delete all attendances for this timetable
            attendances = Attendance.query.filter_by(timetable_id=timetable.id).all()
            for attendance in attendances:
                db.session.delete(attendance)
            db.session.delete(timetable)
        
        # Delete all attendances directly associated with this course
        attendances = Attendance.query.filter_by(course_id=course_id).all()
        for attendance in attendances:
            db.session.delete(attendance)
        
        # Remove course from student_course and faculty_course association tables
        db.session.execute(student_course.delete().where(student_course.c.course_id == course_id))
        db.session.execute(faculty_course.delete().where(faculty_course.c.course_id == course_id))
        
        # Now delete the course
        db.session.delete(course)
        db.session.commit()
        
        flash(f'Course {course.name} has been deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting course: {str(e)}', 'danger')
        logger.error(f"Error deleting course: {str(e)}")
    
    return redirect(url_for('admin.courses'))

@admin.route('/delete/timetable/<int:timetable_id>', methods=['POST'])
@login_required
@admin_required
def delete_timetable(timetable_id):
    try:
        timetable = TimeTable.query.get_or_404(timetable_id)
        
        # Delete all attendances for this timetable
        attendances = Attendance.query.filter_by(timetable_id=timetable_id).all()
        for attendance in attendances:
            db.session.delete(attendance)
        
        # Delete the timetable
        db.session.delete(timetable)
        db.session.commit()
        
        flash('Timetable entry has been deleted!', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Error deleting timetable: {str(e)}', 'danger')
        logger.error(f"Error deleting timetable: {str(e)}")
    
    return redirect(url_for('admin.timetable'))

@admin.route('/attendance/report')
@login_required
@admin_required
def attendance_report():
    # Get all courses
    courses = Course.query.all()
    
    # Default to first course if no course_id is provided
    course_id = request.args.get('course_id', type=int)
    if not course_id and courses:
        course_id = courses[0].id
    
    attendance_data = []
    students = []
    course_name = ""
    
    if course_id:
        course = Course.query.get(course_id)
        if course:
            course_name = f"{course.course_code} - {course.name} ({course.department})"
            
            # Get all students enrolled in this course
            students = Student.query.join(student_course).filter(student_course.c.course_id == course_id).all()
            
            # Get attendance data for each student
            for student in students:
                attendances = Attendance.query.filter_by(student_id=student.id, course_id=course_id).all()
                present_count = sum(1 for a in attendances if a.is_present)
                total_count = len(attendances)
                attendance_percentage = (present_count / total_count * 100) if total_count > 0 else 0
                
                attendance_data.append({
                    'student_id': student.id,
                    'student_name': student.name,
                    'roll_number': student.roll_number,
                    'present_count': present_count,
                    'total_classes': total_count,
                    'attendance_percentage': attendance_percentage
                })
    
    return render_template('admin/attendance_report.html',
                          title='Attendance Report',
                          courses=courses,
                          selected_course_id=course_id,
                          course_name=course_name,
                          attendance_data=attendance_data)

@admin.route('/export/attendance/<int:course_id>')
@login_required
@admin_required
def export_attendance(course_id):
    course = Course.query.get_or_404(course_id)
    
    # Get all students enrolled in this course
    students = Student.query.join(student_course).filter(student_course.c.course_id == course_id).all()
    
    # Prepare data for export
    data = []
    for student in students:
        attendances = Attendance.query.filter_by(student_id=student.id, course_id=course_id).all()
        present_count = sum(1 for a in attendances if a.is_present)
        total_count = len(attendances)
        attendance_percentage = (present_count / total_count * 100) if total_count > 0 else 0
        
        data.append({
            'Student ID': student.id,
            'Name': student.name,
            'Roll Number': student.roll_number,
            'Present': present_count,
            'Total Classes': total_count,
            'Attendance Percentage': f"{attendance_percentage:.2f}%"
        })
    
    # Create DataFrame and export to CSV
    df = pd.DataFrame(data)
    csv_data = df.to_csv(index=False)
    
    return jsonify({
        'success': True,
        'data': csv_data,
        'filename': f"attendance_report_{course.course_code}.csv"
    })

@admin.route('/profile')
@login_required
@admin_required
def profile():
    admin_id = int(current_user.get_id().split('_')[1])
    admin = Admin.query.get(admin_id)
    
    # Initialize password form
    password_form = ChangePasswordForm()
    
    return render_template('admin/profile.html',
                          title='Admin Profile',
                          admin=admin,
                          password_form=password_form)

@admin.route('/logs')
@login_required
@admin_required
def admin_logs():
    page = request.args.get('page', 1, type=int)
    logs = AdminLog.query.order_by(AdminLog.timestamp.desc()).paginate(page=page, per_page=20)
    return render_template('admin/logs.html', title='Admin Logs', logs=logs)

@admin.route('/change_password', methods=['POST'])
@login_required
@admin_required
def change_password():
    form = ChangePasswordForm()
    if form.validate_on_submit():
        admin_id = int(current_user.get_id().split('_')[1])
        admin = Admin.query.get(admin_id)
        
        # Verify current password
        if bcrypt.check_password_hash(admin.password, form.current_password.data):
            # Hash new password
            hashed_password = bcrypt.generate_password_hash(form.new_password.data).decode('utf-8')
            admin.password = hashed_password
            db.session.commit()
            
            # Log this action
            create_admin_log(
                current_user,
                "Changed own password",
                "Admin changed their own password"
            )
            
            flash('Your password has been updated!', 'success')
        else:
            flash('Current password is incorrect. Please try again.', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
    
    return redirect(url_for('admin.profile'))

# Helper function to generate a temporary password based on name and roll number/department
def generate_temp_password(name, identifier):
    # Take first 4 characters of name (or fewer if name is shorter)
    name_part = name[:4].lower()
    
    # Take last 4 characters of identifier (roll number for students, department for faculty)
    # If identifier is shorter than 4 characters, use the whole thing
    if len(identifier) <= 4:
        id_part = identifier.lower()
    else:
        id_part = identifier[-4:].lower()
    
    # Combine them to create the temporary password
    return name_part + id_part

@admin.route('/add_student', methods=['POST'])
@login_required
@admin_required
def add_student():
    form = AdminAddStudentForm()
    if form.validate_on_submit():
        try:
            # Generate a temporary password based on name and roll number
            temp_password = generate_temp_password(form.name.data, form.roll_number.data)
            hashed_password = bcrypt.generate_password_hash(temp_password).decode('utf-8')
            
            # Create the student account
            student = Student(
                name=form.name.data,
                email=form.email.data,
                roll_number=form.roll_number.data,
                department=form.department.data,
                year=int(form.year.data),
                password=hashed_password,
                is_approved=True  # Automatically approve since admin is creating
            )
            
            db.session.add(student)
            db.session.commit()
            
            # Automatically assign courses
            courses = Course.query.filter_by(department=form.department.data, year=int(form.year.data)).all()
            for course in courses:
                student.courses.append(course)
            
            try:
                db.session.commit()
                flash(f'Account created for {form.name.data}! Temporary password: {temp_password}', 'success')
            except Exception as e:
                db.session.rollback()
                logger.error(f"Error assigning courses to student: {str(e)}")
                flash(f'Student account created but there was an error assigning courses: {str(e)}', 'warning')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating student account: {str(e)}")
            flash(f'Error creating student account: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
                
    return redirect(url_for('admin.dashboard'))

@admin.route('/add_faculty', methods=['POST'])
@login_required
@admin_required
def add_faculty():
    form = AdminAddFacultyForm()
    if form.validate_on_submit():
        try:
            # Generate a temporary password based on name and department
            temp_password = generate_temp_password(form.name.data, form.department.data)
            hashed_password = bcrypt.generate_password_hash(temp_password).decode('utf-8')
            
            # Create the faculty account
            faculty = Faculty(
                name=form.name.data,
                email=form.email.data,
                department=form.department.data,
                password=hashed_password,
                is_approved=True  # Automatically approve since admin is creating
            )
            
            db.session.add(faculty)
            db.session.commit()
            flash(f'Account created for {form.name.data}! Temporary password: {temp_password}', 'success')
            
        except Exception as e:
            db.session.rollback()
            logger.error(f"Error creating faculty account: {str(e)}")
            flash(f'Error creating faculty account: {str(e)}', 'danger')
    else:
        for field, errors in form.errors.items():
            for error in errors:
                flash(f'{getattr(form, field).label.text}: {error}', 'danger')
                
    return redirect(url_for('admin.dashboard'))