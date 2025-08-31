# AI-Powered Smart Attendance & Engagement Monitoring System

A comprehensive, AI-driven Attendance and Engagement Monitoring System using DeepFace for face recognition, Flask for backend services, and HTML/CSS/JavaScript for responsive frontend.

## Overview

This system supports three user roles — Admin, Faculty, and Student, with a centralized database. It features live attendance tracking using facial recognition, phone usage detection, and engagement analytics, all managed through a secure login and verification system.

## Features

### User Roles

#### Admin:
- Controls permissions and access for Students and Faculty
- Verifies all registrations before allowing system access
- Views complete attendance, engagement reports, and subject-wise data
- Manages time-tables, student-faculty-subject mapping

#### Student:
- Registers via a form + webcam-based face data (DeepFace)
- Access to personal attendance dashboard only
- Login pending until approved by Admin

#### Faculty:
- Signs in via Google OAuth (simulated in this version)
- After login, views today's time-table from the database
- Selects the current class and starts the session
- Webcam or CCTV triggers face recognition (DeepFace)
- Faculty can manually mark students if needed
- Views subject-wise attendance reports and students below 75% attendance
- Can view phone usage logs (future), and engagement stats

### System Modules

#### Face Recognition (Active):
- Uses DeepFace model for facial recognition
- Face registration via webcam on student signup
- Live recognition via webcam/CCTV during class session

#### Phone Usage Detection (Future):
- Will be integrated later
- Logs timestamped events where students use phones during class
- Available to Faculty/Admin for reports

#### Engagement Analytics (Future):
- Placeholder for student attention, emotion/sentiment analysis
- Will detect distracted students or classify engagement levels

## Tech Stack

- **Backend**: Python Flask
- **Frontend**: HTML, CSS, JavaScript, Bootstrap 5
- **Database**: SQLAlchemy (SQLite for development)
- **Face Recognition**: DeepFace
- **Authentication**: Flask-Login, OAuth integration (Google)

## Installation

1. Clone the repository:
```
git clone https://github.com/yourusername/smart-attendance-system.git
cd smart-attendance-system
```

2. Create a virtual environment and activate it:
```
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. Install the required dependencies:
```
pip install -r requirements.txt
```

4. Set up environment variables (create a .env file with the following variables):
```
SECRET_KEY=your_secret_key_here
SQLALCHEMY_DATABASE_URI=sqlite:///site.db
GOOGLE_CLIENT_ID=your_google_client_id
GOOGLE_CLIENT_SECRET=your_google_client_secret
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=True
MAIL_USERNAME=your_email@gmail.com
MAIL_PASSWORD=your_email_password
```

5. Run the application:
```
python run.py
```

## Usage

### Initial Setup

On first run, an admin account is automatically created with the following credentials:
- Email: admin@example.com
- Password: admin123

Use these credentials to log in and start managing the system.

### Admin Workflow

1. Log in as an admin
2. Approve new student and faculty registrations
3. Add courses to the system
4. Create the timetable by assigning courses to faculty members
5. View attendance reports and manage user accounts

### Faculty Workflow

1. Log in as a faculty member
2. View today's schedule on the dashboard
3. Start a session for the current class
4. Use automatic face recognition to mark attendance or mark attendance manually
5. View attendance reports for your courses

### Student Workflow

1. Register with face data capture
2. Log in after admin approval
3. View your attendance status and course schedule
4. Monitor your attendance percentage across all courses

## Directory Structure

- `/static`: Contains CSS, JavaScript, and image files
- `/templates`: HTML templates organized by user role
- `/models`: Database models
- `/routes`: Route handlers for different user roles
- `/utils`: Utility functions including face recognition
- `/face_data`: Storage for student face data

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- DeepFace library for facial recognition
- Flask and its extensions for web framework
- Bootstrap for responsive UI components
# SmartClassMonitoringSystem
# SmartClassMonitoringSystem
