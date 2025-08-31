from flask_login import UserMixin
from datetime import datetime
import json
from app import db

# Association table for many-to-many relationships
student_course = db.Table('student_course',
    db.Column('student_id', db.Integer, db.ForeignKey('student.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

faculty_course = db.Table('faculty_course',
    db.Column('faculty_id', db.Integer, db.ForeignKey('faculty.id'), primary_key=True),
    db.Column('course_id', db.Integer, db.ForeignKey('course.id'), primary_key=True)
)

class User(db.Model, UserMixin):
    __abstract__ = True
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=True)  # Nullable for OAuth users
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Override get_id from UserMixin to include the user type
    def get_id(self):
        raise NotImplementedError("Subclasses must implement get_id()")

class Student(User):
    __tablename__ = 'student'
    
    roll_number = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False)
    face_encoding = db.Column(db.Text, nullable=True)  # Stored as JSON string
    is_approved = db.Column(db.Boolean, default=False)
    
    # Relationships
    courses = db.relationship('Course', secondary=student_course, backref=db.backref('students', lazy='dynamic'))
    attendances = db.relationship('Attendance', backref='student', lazy=True)
    
    def get_id(self):
        return f"student_{self.id}"
    
    def set_face_encoding(self, encoding):
        if encoding is not None:
            self.face_encoding = json.dumps(encoding.tolist())
    
    def get_face_encoding(self):
        if self.face_encoding:
            return json.loads(self.face_encoding)
        return None

class Faculty(User):
    __tablename__ = 'faculty'
    
    department = db.Column(db.String(50), nullable=False)
    google_id = db.Column(db.String(100), unique=True, nullable=True)
    is_approved = db.Column(db.Boolean, default=False)
    
    # Relationships
    courses = db.relationship('Course', secondary=faculty_course, backref=db.backref('faculties', lazy='dynamic'))
    timetables = db.relationship('TimeTable', backref='faculty', lazy=True)
    
    def get_id(self):
        return f"faculty_{self.id}"

class Admin(User):
    __tablename__ = 'admin'
    
    def get_id(self):
        return f"admin_{self.id}"

class Course(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    course_code = db.Column(db.String(20), nullable=False)  # Removed unique constraint
    name = db.Column(db.String(100), nullable=False)
    credits = db.Column(db.Integer, nullable=False)
    department = db.Column(db.String(50), nullable=False)
    year = db.Column(db.Integer, nullable=False, default=1)  # Added year field
    
    # Make the combination of course_code and department unique
    __table_args__ = (
        db.UniqueConstraint('course_code', 'department', name='_course_code_department_uc'),
    )
    
    # Relationships
    timetables = db.relationship('TimeTable', backref='course', lazy=True)
    attendances = db.relationship('Attendance', backref='course', lazy=True)

class TimeTable(db.Model):
    __tablename__ = 'time_table'  # Explicitly set table name
    
    id = db.Column(db.Integer, primary_key=True)
    day = db.Column(db.String(10), nullable=False)  # Monday, Tuesday, etc.
    start_time = db.Column(db.Time, nullable=False)
    end_time = db.Column(db.Time, nullable=False)
    room = db.Column(db.String(20), nullable=False)
    year = db.Column(db.Integer, nullable=False, default=1)  # Added year field
    
    # Foreign Keys
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    faculty_id = db.Column(db.Integer, db.ForeignKey('faculty.id'), nullable=False)
    
    # Relationships
    attendances = db.relationship('Attendance', backref='timetable', lazy=True)

class Attendance(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    date = db.Column(db.Date, nullable=False, default=datetime.utcnow().date)
    is_present = db.Column(db.Boolean, default=False)
    time_in = db.Column(db.DateTime, nullable=True)
    time_out = db.Column(db.DateTime, nullable=True)
    marked_by = db.Column(db.String(50), nullable=False)  # 'auto' or faculty email
    
    # Engagement metrics
    engagement_score = db.Column(db.Float, nullable=True)  # 0 to 100
    phone_usage_count = db.Column(db.Integer, default=0)
    
    # Foreign Keys
    student_id = db.Column(db.Integer, db.ForeignKey('student.id'), nullable=False)
    course_id = db.Column(db.Integer, db.ForeignKey('course.id'), nullable=False)
    timetable_id = db.Column(db.Integer, db.ForeignKey('time_table.id'), nullable=False)  # Fixed reference to time_table

class PhoneUsageLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    confidence = db.Column(db.Float, nullable=False)  # Detection confidence score
    
    # Foreign Keys
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    
    # Relationship
    attendance = db.relationship('Attendance', backref='phone_usage_logs')

class EngagementLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    engagement_type = db.Column(db.String(50), nullable=False)  # e.g., 'distracted', 'engaged', 'neutral'
    confidence = db.Column(db.Float, nullable=False)
    
    # Foreign Keys
    attendance_id = db.Column(db.Integer, db.ForeignKey('attendance.id'), nullable=False)
    
    # Relationship
    attendance = db.relationship('Attendance', backref='engagement_logs')

class Department(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(50), unique=True, nullable=False)

    @classmethod
    def get_default_departments(cls):
        return ['CSE', 'CSE-AID', 'ECE', 'ECE-VLSI']

class AdminLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    admin_id = db.Column(db.Integer, db.ForeignKey('admin.id'), nullable=False)
    admin_email = db.Column(db.String(120), nullable=False)
    action = db.Column(db.String(255), nullable=False)
    details = db.Column(db.Text, nullable=True)
    ip_address = db.Column(db.String(50), nullable=True)
    
    # Relationship
    admin = db.relationship('Admin', backref='logs')