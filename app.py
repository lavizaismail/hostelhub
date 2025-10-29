from flask import Flask, render_template, redirect, url_for, request, flash
from flask_login import LoginManager, current_user, login_required
from datetime import datetime
import os

# Initialize Flask app
app = Flask(__name__)

# ============================================
# 🔧 DEPLOYMENT CONFIGURATION
# ============================================
# Check if running on Render (production) or local
if os.environ.get('DATABASE_URL'):
    # Production: Use PostgreSQL from Render
    database_url = os.environ.get('DATABASE_URL')
    # Fix postgres:// to postgresql:// (SQLAlchemy requirement)
    if database_url.startswith('postgres://'):
        database_url = database_url.replace('postgres://', 'postgresql://', 1)
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url
else:
    # Local development: Use SQLite
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///hostelhub.db'

# Use environment variable for SECRET_KEY in production
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY', 'your-secret-key-here-change-in-production')
# ============================================

app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Import db from models FIRST
from models import db

# Initialize db with app
db.init_app(app)

# Initialize login manager
login_manager = LoginManager(app)
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

# Now import models
from models import User, Student, Room, RoomAllocation, Complaint, Payment, Notification, AuditLog, MaintenanceStaff

# User loader
@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Import blueprints
from routes.auth import auth_bp
from routes.student import student_bp
from routes.warden import warden_bp
from routes.admin import admin_bp
from routes.accountant import accountant_bp
from routes.maintenance import maintenance_bp
from routes.profile import profile_bp

# Register blueprints
app.register_blueprint(auth_bp, url_prefix='/auth')
app.register_blueprint(student_bp, url_prefix='/student')
app.register_blueprint(warden_bp, url_prefix='/warden')
app.register_blueprint(admin_bp, url_prefix='/admin')
app.register_blueprint(accountant_bp, url_prefix='/accountant')
app.register_blueprint(maintenance_bp, url_prefix='/maintenance')
app.register_blueprint(profile_bp, url_prefix='/')

# Home route
@app.route('/')
def index():
    if current_user.is_authenticated:
        if current_user.role == 'admin':
            return redirect(url_for('admin.dashboard'))
        elif current_user.role == 'warden':
            return redirect(url_for('warden.dashboard'))
        elif current_user.role == 'student':
            return redirect(url_for('student.dashboard'))
        elif current_user.role == 'accountant':
            return redirect(url_for('accountant.dashboard'))
        elif current_user.role == 'maintenance':
            return redirect(url_for('maintenance.dashboard'))
    return render_template('index.html')

@app.route('/about')
def about():
    return render_template('about.html')

@app.route('/contact', methods=['POST'])
def contact():
    name = request.form.get('name', '')
    email = request.form.get('email', '')
    message = request.form.get('message', '')
    flash('Thank you for contacting us! We will get back to you soon.', 'success')
    return redirect(url_for('about'))

@app.route('/notifications')
def notifications():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    notifications = Notification.query.filter_by(
        userid=current_user.userid
    ).order_by(Notification.created_at.desc()).all()
    return render_template('notifications.html', notifications=notifications)

@app.route('/notification/read/<int:notification_id>')
def mark_notification_read(notification_id):
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    notification = Notification.query.get_or_404(notification_id)
    if notification.userid == current_user.userid:
        notification.is_read = True
        db.session.commit()
    if notification.link:
        return redirect(notification.link)
    return redirect(url_for('notifications'))

@app.route('/notifications/mark-all-read')
@login_required
def mark_all_read():
    if not current_user.is_authenticated:
        return redirect(url_for('auth.login'))
    notifications = Notification.query.filter_by(
        userid=current_user.userid,
        is_read=False
    ).all()
    for notif in notifications:
        notif.is_read = True
    db.session.commit()
    flash('✅ All notifications marked as read', 'success')
    return redirect(url_for('notifications'))

@app.route('/api/notifications/count')
@login_required
def notification_count_api():
    count = Notification.query.filter_by(
        userid=current_user.userid,
        is_read=False
    ).count()
    from flask import jsonify
    return jsonify({'count': count})

@app.route('/receipt/<int:payment_id>')
@login_required
def generate_receipt(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    # Verify payment belongs to current user or is admin/accountant
    if current_user.role == 'student':
        student = Student.query.filter_by(userid=current_user.userid).first()
        if payment.studentid != student.studentid:
            flash('Unauthorized access', 'danger')
            return redirect(url_for('student.payments'))
    elif current_user.role not in ['admin', 'accountant']:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('index'))
    
    if payment.status != 'verified':
        flash('Receipt can only be generated for verified payments', 'warning')
        return redirect(url_for('student.payments'))
    
    from utils.pdf_generator import generate_payment_receipt
    return generate_payment_receipt(payment)

# Context processor for notifications
@app.context_processor
def inject_notifications():
    if current_user.is_authenticated:
        unread_count = Notification.query.filter_by(
            userid=current_user.userid,
            is_read=False
        ).count()
        return {'unread_notifications': unread_count}
    return {'unread_notifications': 0}

# Error handlers
@app.errorhandler(404)
def not_found_error(error):
    return render_template('errors/404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    db.session.rollback()
    return render_template('errors/500.html'), 500

def create_default_maintenance_staff():
    """Create maintenance staff members for each complaint category"""
    staff_list = [
        ('John Doe', 'plumbing', '+91-9876543210'),
        ('Smith Williams', 'electrical', '+91-9876543211'),
        ('Robert Brown', 'cleaning', '+91-9876543212'),
        ('Michael Davis', 'furniture', '+91-9876543213'),
        ('David Wilson', 'wifi', '+91-9876543214'),
        ('James Taylor', 'other', '+91-9876543215'),
    ]
    
    for name, specialization, phone in staff_list:
        existing = MaintenanceStaff.query.filter_by(name=name).first()
        if not existing:
            staff = MaintenanceStaff(
                name=name,
                specialization=specialization,
                phone=phone,
                is_active=True
            )
            db.session.add(staff)
            print(f"✅ Created maintenance staff: {name} - {specialization.title()}")
    db.session.commit()

# Database initialization (LOCAL DEVELOPMENT ONLY)
if __name__ == '__main__':
    with app.app_context():
        print("🔨 Creating database...")
        db.create_all()
        print("✅ Database created!")
        
        # Create uploads directory
        os.makedirs('static/uploads/complaints', exist_ok=True)
        
        # Create default users only if they don't exist
        if not User.query.filter_by(username='admin').first():
            admin = User(username='admin', email='admin@hostelhub.com', role='admin', is_active=True)
            admin.set_password('admin123')
            db.session.add(admin)
            db.session.commit()
            print("✅ Admin created: admin / admin123")
        
        if not User.query.filter_by(username='warden').first():
            warden = User(username='warden', email='warden@hostelhub.com', role='warden', is_active=True)
            warden.set_password('warden123')
            db.session.add(warden)
            db.session.commit()
            print("✅ Warden created: warden / warden123")
        
        if not User.query.filter_by(username='accountant').first():
            accountant = User(username='accountant', email='accountant@hostelhub.com', role='accountant', is_active=True)
            accountant.set_password('accountant123')
            db.session.add(accountant)
            db.session.commit()
            print("✅ Accountant created: accountant / accountant123")
        
        if not User.query.filter_by(username='maintenance').first():
            maintenance = User(username='maintenance', email='maintenance@hostelhub.com', role='maintenance', is_active=True)
            maintenance.set_password('maintenance123')
            db.session.add(maintenance)
            db.session.commit()
            print("✅ Default maintenance created: maintenance / maintenance123")
        
        # Create maintenance staff
        create_default_maintenance_staff()
        
        # Create sample rooms
        if Room.query.count() == 0:
            sample_rooms = [
                Room(block='A', roomnumber='101', floor=1, capacity=2, current_occupancy=0,
                     monthly_rent=5000, gender='male', facilities='AC, Attached Bathroom, WiFi'),
                Room(block='A', roomnumber='102', floor=1, capacity=2, current_occupancy=0,
                     monthly_rent=5000, gender='male', facilities='AC, Attached Bathroom, WiFi'),
                Room(block='B', roomnumber='101', floor=1, capacity=2, current_occupancy=0,
                     monthly_rent=5000, gender='female', facilities='AC, Attached Bathroom, WiFi'),
                Room(block='B', roomnumber='102', floor=1, capacity=2, current_occupancy=0,
                     monthly_rent=5000, gender='female', facilities='AC, Attached Bathroom, WiFi'),
            ]
            for room in sample_rooms:
                db.session.add(room)
            db.session.commit()
            print("✅ Sample rooms created!")
    
    # Run the development server (only runs locally)
    print("\n🚀 Starting HostelHub Development Server...")
    print("📍 Local URL: http://127.0.0.1:5000")
    app.run(debug=True, host='0.0.0.0', port=5000)
