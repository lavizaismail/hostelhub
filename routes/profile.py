from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Student
from werkzeug.utils import secure_filename
from datetime import datetime
import os

profile_bp = Blueprint('profile', __name__)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@profile_bp.route('/profile')
@login_required
def view_profile():
    user = current_user
    student = None
    
    if user.role == 'student':
        student = Student.query.filter_by(userid=user.userid).first()
    
    return render_template('profile/view.html', user=user, student=student)

@profile_bp.route('/profile/edit', methods=['GET', 'POST'])
@login_required
def edit_profile():
    user = current_user
    student = None
    
    if user.role == 'student':
        student = Student.query.filter_by(userid=user.userid).first()
    
    if request.method == 'POST':
        # Update email
        new_email = request.form.get('email')
        if new_email and new_email != user.email:
            # Check if email already exists
            existing = User.query.filter_by(email=new_email).first()
            if existing and existing.userid != user.userid:
                flash('Email already in use by another user.', 'danger')
            else:
                user.email = new_email
        
        # Update student info if applicable
        if student:
            student.phone = request.form.get('phone', student.phone)
            student.guardian_phone = request.form.get('guardian_phone', student.guardian_phone)
            student.address = request.form.get('address', student.address)
        
        db.session.commit()
        flash('Profile updated successfully!', 'success')
        return redirect(url_for('profile.view_profile'))
    
    return render_template('profile/edit.html', user=user, student=student)

@profile_bp.route('/profile/upload-picture', methods=['POST'])
@login_required
def upload_picture():
    if 'profile_picture' not in request.files:
        flash('No file selected', 'danger')
        return redirect(url_for('profile.view_profile'))
    
    file = request.files['profile_picture']
    
    if file.filename == '':
        flash('No file selected', 'danger')
        return redirect(url_for('profile.view_profile'))
    
    if file and allowed_file(file.filename):
        # Create unique filename
        filename = secure_filename(f"{current_user.userid}_{datetime.now().timestamp()}.{file.filename.rsplit('.', 1)[1].lower()}")
        filepath = os.path.join('static/uploads/profiles', filename)
        
        # Ensure directory exists
        os.makedirs('static/uploads/profiles', exist_ok=True)
        
        # Delete old profile picture if not default
        if current_user.profile_picture != 'default.png':
            old_path = os.path.join('static/uploads/profiles', current_user.profile_picture)
            if os.path.exists(old_path):
                os.remove(old_path)
        
        # Save new picture
        file.save(filepath)
        
        # Update database
        current_user.profile_picture = filename
        db.session.commit()
        
        flash('Profile picture updated successfully!', 'success')
    else:
        flash('Invalid file type. Only PNG, JPG, JPEG, and GIF are allowed.', 'danger')
    
    return redirect(url_for('profile.view_profile'))

@profile_bp.route('/profile/change-password', methods=['GET', 'POST'])
@login_required
def change_password():
    if request.method == 'POST':
        current_password = request.form.get('current_password')
        new_password = request.form.get('new_password')
        confirm_password = request.form.get('confirm_password')
        
        # Verify current password
        if not current_user.check_password(current_password):
            flash('Current password is incorrect.', 'danger')
            return redirect(url_for('profile.change_password'))
        
        # Check if new passwords match
        if new_password != confirm_password:
            flash('New passwords do not match.', 'danger')
            return redirect(url_for('profile.change_password'))
        
        # Check password length
        if len(new_password) < 6:
            flash('Password must be at least 6 characters long.', 'danger')
            return redirect(url_for('profile.change_password'))
        
        # Update password
        current_user.set_password(new_password)
        db.session.commit()
        
        flash('Password changed successfully!', 'success')
        return redirect(url_for('profile.view_profile'))
    
    return render_template('profile/change_password.html')
