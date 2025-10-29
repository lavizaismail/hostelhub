from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from models import db, User, Student, Notification
from flask_login import login_user, logout_user, login_required
from datetime import datetime

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        role = request.form.get('role', 'student')
        
        # Check if user already exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists!', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered!', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            password=generate_password_hash(password),
            role=role,
            is_active=False
        )
        
        db.session.add(new_user)
        db.session.flush()  # Get userid
        
        # If student, create student profile
        # If student, create student profile
        if role == 'student':
            fullname = request.form.get('fullname')
            phone = request.form.get('phone')
            rollnumber = request.form.get('rollnumber')
            course = request.form.get('course')  # ← NOW THIS WILL WORK!
            year = request.form.get('year')
            gender = request.form.get('gender')
    
     # Auto-generate roll number if not provided
            if not rollnumber:
                import time
                rollnumber = f"STUD{int(time.time())}"
    
            student = Student(
                userid=new_user.userid,
                rollnumber=rollnumber,
                fullname=fullname,
                phone=phone,
                email=email,  # Use email from user registration
                course=course,  # ← NOW VALID!
                year=int(year) if year else None,
                gender=gender
            )
            db.session.add(student)

            # ✅ NOTIFY ADMIN - NEW STUDENT REGISTRATION
            admins = User.query.filter_by(role='admin').all()
            for admin in admins:
                notification = Notification(
                    userid=admin.userid,
                    title='👤 New Student Registered',
                    message=f'New student {fullname} has registered (Email: {email})',
                    type='success',
                    link='/admin/users',
                    is_read=False,
                    created_at=datetime.utcnow()
                )
                db.session.add(notification)
        
        db.session.commit()
        
        flash('Registration successful! Please wait for admin approval before logging in.', 'success')
        return redirect(url_for('auth.login'))
    
    return render_template('auth/register.html')

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        user = User.query.filter_by(username=username).first()
        
        if user and check_password_hash(user.password, password):
            if not user.is_active:
                flash('Your account has been deactivated!', 'danger')
                return redirect(url_for('auth.login'))
            
            login_user(user)
            
            # Redirect based on role
            if user.role == 'admin':
                return redirect(url_for('admin.dashboard'))
            elif user.role == 'student':
                return redirect(url_for('student.dashboard'))
            elif user.role == 'warden':
                return redirect(url_for('warden.dashboard'))
            elif user.role == 'accountant':
                return redirect(url_for('accountant.dashboard'))
            elif user.role == 'maintenance':
                return redirect(url_for('maintenance.dashboard'))
            else:
                return redirect(url_for('index'))
        else:
            flash('Invalid username or password!', 'danger')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('auth.login'))
