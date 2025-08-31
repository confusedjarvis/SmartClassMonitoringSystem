from flask import Blueprint, render_template, redirect, url_for
from flask_login import current_user, login_required

main = Blueprint('main', __name__)

@main.route('/')
@main.route('/home')
def home():
    if current_user.is_authenticated:
        if current_user.get_id().startswith('admin'):
            return redirect(url_for('admin.dashboard'))
        elif current_user.get_id().startswith('faculty'):
            return redirect(url_for('faculty.dashboard'))
        elif current_user.get_id().startswith('student'):
            return redirect(url_for('student.dashboard'))
    return render_template('home.html', title='Home')

@main.route('/about')
def about():
    return render_template('about.html', title='About')
