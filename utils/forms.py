from flask_wtf import FlaskForm
from flask_wtf.file import FileField, FileAllowed
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField, IntegerField, HiddenField
from wtforms.validators import DataRequired, Length, Email, EqualTo, ValidationError
from models.models import Student, Faculty, Admin

class LoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class AdminLoginForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])
    remember = BooleanField('Remember Me')
    submit = SubmitField('Login')

class StudentRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    roll_number = StringField('Roll Number', validators=[DataRequired(), Length(min=2, max=20)])
    department = SelectField('Department', validators=[DataRequired()],
                            choices=[
                                ('CSE', 'Computer Science Engineering'), 
                                ('CSE-AID', 'Computer Science Engineering - AI and Data Science'),
                                ('ECE', 'Electronics & Communication Engineering'),
                                ('ECE-VLSI', 'Electronics & Communication Engineering - VLSI')
                            ])
    year = SelectField('Year', validators=[DataRequired()],
                      choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year')])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    face_data = HiddenField('Face Data')
    submit = SubmitField('Register')

    def validate_email(self, email):
        # Check if email already exists in any user table
        student = Student.query.filter_by(email=email.data).first()
        faculty = Faculty.query.filter_by(email=email.data).first()
        admin = Admin.query.filter_by(email=email.data).first()
        
        if student or faculty or admin:
            raise ValidationError('That email is already registered. Please use a different one.')

    def validate_roll_number(self, roll_number):
        student = Student.query.filter_by(roll_number=roll_number.data).first()
        if student:
            raise ValidationError('That roll number is already registered.')

class FacultyRegistrationForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    department = SelectField('Department', validators=[DataRequired()],
                            choices=[
                                ('CSE', 'Computer Science Engineering'), 
                                ('CSE-AID', 'Computer Science Engineering - AI and Data Science'),
                                ('ECE', 'Electronics & Communication Engineering'),
                                ('ECE-VLSI', 'Electronics & Communication Engineering - VLSI')
                            ])
    password = PasswordField('Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm Password', validators=[DataRequired(), EqualTo('password')])
    submit = SubmitField('Register')

    def validate_email(self, email):
        # Check if email already exists in any user table
        student = Student.query.filter_by(email=email.data).first()
        faculty = Faculty.query.filter_by(email=email.data).first()
        admin = Admin.query.filter_by(email=email.data).first()
        
        if student or faculty or admin:
            raise ValidationError('That email is already registered. Please use a different one.')

class CourseForm(FlaskForm):
    course_code = StringField('Course Code', validators=[DataRequired(), Length(min=2, max=20)])
    name = StringField('Course Name', validators=[DataRequired(), Length(min=2, max=100)])
    credits = IntegerField('Credits', validators=[DataRequired()])
    department = SelectField('Department', validators=[DataRequired()],
                            choices=[
                                ('CSE', 'Computer Science Engineering'), 
                                ('CSE-AID', 'Computer Science Engineering - AI and Data Science'),
                                ('ECE', 'Electronics & Communication Engineering'),
                                ('ECE-VLSI', 'Electronics & Communication Engineering - VLSI')
                            ])
    year = SelectField('Year', validators=[DataRequired()],
                      choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year')])
    submit = SubmitField('Add Course')

class TimeTableForm(FlaskForm):
    course_id = SelectField('Course', validators=[DataRequired()], coerce=int)
    faculty_id = SelectField('Faculty', validators=[DataRequired()], coerce=int)
    year = SelectField('Year', validators=[DataRequired()],
                      choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year')])
    day = SelectField('Day', validators=[DataRequired()],
                     choices=[
                         ('Monday', 'Monday'),
                         ('Tuesday', 'Tuesday'),
                         ('Wednesday', 'Wednesday'),
                         ('Thursday', 'Thursday'),
                         ('Friday', 'Friday'),
                         ('Saturday', 'Saturday'),
                     ])
    start_time = StringField('Start Time (HH:MM)', validators=[DataRequired()])
    end_time = StringField('End Time (HH:MM)', validators=[DataRequired()])
    room = StringField('Room', validators=[DataRequired(), Length(min=1, max=20)])
    submit = SubmitField('Add Time Table Entry')

class ManualAttendanceForm(FlaskForm):
    student_id = SelectField('Student', validators=[DataRequired()], coerce=int)
    is_present = BooleanField('Present')
    submit = SubmitField('Mark Attendance')

class ChangePasswordForm(FlaskForm):
    current_password = PasswordField('Current Password', validators=[DataRequired()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    submit = SubmitField('Change Password')

class UpdateFaceForm(FlaskForm):
    face_data = HiddenField('Face Data')
    submit = SubmitField('Update Face Biometric')

class AdminAddStudentForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    roll_number = StringField('Roll Number', validators=[DataRequired(), Length(min=2, max=20)])
    department = SelectField('Department', validators=[DataRequired()],
                            choices=[
                                ('CSE', 'Computer Science Engineering'), 
                                ('CSE-AID', 'Computer Science Engineering - AI and Data Science'),
                                ('ECE', 'Electronics & Communication Engineering'),
                                ('ECE-VLSI', 'Electronics & Communication Engineering - VLSI')
                            ])
    year = SelectField('Year', validators=[DataRequired()],
                      choices=[('1', '1st Year'), ('2', '2nd Year'), ('3', '3rd Year'), ('4', '4th Year')])
    submit = SubmitField('Add Student')

    def validate_email(self, email):
        # Check if email already exists in any user table
        student = Student.query.filter_by(email=email.data).first()
        faculty = Faculty.query.filter_by(email=email.data).first()
        admin = Admin.query.filter_by(email=email.data).first()
        
        if student or faculty or admin:
            raise ValidationError('That email is already registered. Please use a different one.')

    def validate_roll_number(self, roll_number):
        student = Student.query.filter_by(roll_number=roll_number.data).first()
        if student:
            raise ValidationError('That roll number is already registered.')

class AdminAddFacultyForm(FlaskForm):
    name = StringField('Full Name', validators=[DataRequired(), Length(min=2, max=100)])
    email = StringField('Email', validators=[DataRequired(), Email()])
    department = SelectField('Department', validators=[DataRequired()],
                            choices=[
                                ('CSE', 'Computer Science Engineering'), 
                                ('CSE-AID', 'Computer Science Engineering - AI and Data Science'),
                                ('ECE', 'Electronics & Communication Engineering'),
                                ('ECE-VLSI', 'Electronics & Communication Engineering - VLSI')
                            ])
    submit = SubmitField('Add Faculty')

    def validate_email(self, email):
        # Check if email already exists in any user table
        student = Student.query.filter_by(email=email.data).first()
        faculty = Faculty.query.filter_by(email=email.data).first()
        admin = Admin.query.filter_by(email=email.data).first()
        
        if student or faculty or admin:
            raise ValidationError('That email is already registered. Please use a different one.')

class ResetPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    new_password = PasswordField('New Password', validators=[DataRequired()])
    confirm_password = PasswordField('Confirm New Password', validators=[DataRequired(), EqualTo('new_password')])
    user_type = SelectField('User Type', choices=[('student', 'Student'), ('faculty', 'Faculty')])
    submit = SubmitField('Reset Password')
    
    def validate_email(self, email):
        if self.user_type.data == 'student':
            user = Student.query.filter_by(email=email.data).first()
        else:
            user = Faculty.query.filter_by(email=email.data).first()
            
        if not user:
            raise ValidationError(f'No {self.user_type.data} found with that email address.')

class ForgotPasswordForm(FlaskForm):
    email = StringField('Email', validators=[DataRequired(), Email()])
    submit = SubmitField('Submit')
