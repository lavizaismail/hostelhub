from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Student, Room, RoomAllocation, Complaint, Payment, Notification, User
from functools import wraps
from datetime import datetime
from werkzeug.utils import secure_filename
from utils.audit import log_complaint_creation
from utils.notifications import create_notification
from utils.pdf_generator import generate_payment_receipt  # ← ADD THIS IMPORT
import os

student_bp = Blueprint('student', __name__)

def student_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'student':
            flash('Access denied. Students only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@student_bp.route('/dashboard')
@login_required
@student_required
def dashboard():
    student = Student.query.filter_by(userid=current_user.userid).first()
    
    allocation = RoomAllocation.query.filter_by(
        studentid=student.studentid,
        status='active'
    ).first()
    
    pending_payments = Payment.query.filter_by(
        studentid=student.studentid
    ).filter(Payment.status.in_(['pending', 'paid'])).all()
    
    complaints = Complaint.query.filter_by(
        studentid=student.studentid
    ).order_by(Complaint.created_at.desc()).limit(5).all()
    
    total_dues = sum(p.amount for p in pending_payments)
    
    return render_template('student/dashboard.html',
                         student=student,
                         allocation=allocation,
                         total_dues=total_dues,
                         complaints=complaints)

@student_bp.route('/my-room')
@login_required
@student_required
def my_room():
    student = Student.query.filter_by(userid=current_user.userid).first()
    
    allocation = RoomAllocation.query.filter_by(
        studentid=student.studentid,
        status='active'
    ).first()
    
    if not allocation:
        flash('You do not have an active room allocation', 'info')
        return redirect(url_for('student.request_room'))
    
    return render_template('student/my_room.html', allocation=allocation, student=student)

@student_bp.route('/request-room', methods=['GET', 'POST'])
@login_required
@student_required
def request_room():
    student = Student.query.filter_by(userid=current_user.userid).first()
    
    # 🐛 DEBUG: Check database state
    all_rooms = Room.query.all()
    print(f"DEBUG: Total rooms in DB: {len(all_rooms)}")
    print(f"DEBUG: Student gender: {student.gender if student else 'NO STUDENT'}")
    
    # ✅ FIXED: Use current_occupancy (with underscore) everywhere
    available_rooms = Room.query.filter(
        db.or_(
            Room.current_occupancy < Room.capacity,
            Room.current_occupancy == None,
            Room.current_occupancy == 0
        )
    ).filter(
        db.or_(
            Room.gender == student.gender,
            Room.gender == 'mixed'
        )
    ).all()
    
    # 🐛 DEBUG: Show what rooms were found
    print(f"DEBUG: Available rooms found: {len(available_rooms)}")
    for room in available_rooms:
        print(f"  - Room {room.roomnumber}: gender={room.gender}, capacity={room.capacity}, occupancy={room.current_occupancy}")
    
    # Check if student already has active allocation
    has_allocation = RoomAllocation.query.filter_by(
        studentid=student.studentid,
        status='active'
    ).first()
    
    if has_allocation:
        flash('You already have an active room.', 'warning')
        return redirect(url_for('student.dashboard'))
    
    if request.method == 'POST':
        roomid = request.form.get('roomid')
        preferences = request.form.get('preferences', '')
        
        room = Room.query.get(roomid)
        
        if not room or not room.is_available():
            flash('Selected room is not available.', 'danger')
            return redirect(url_for('student.request_room'))
        
        if room.gender != student.gender and room.gender != 'mixed':
            flash('Selected room gender restriction does not match.', 'danger')
            return redirect(url_for('student.request_room'))
        
        allocation = RoomAllocation(
            studentid=student.studentid,
            roomid=room.roomid,
            status='pending_approval',
        )
        
        db.session.add(allocation)
        db.session.commit()
        
        # ✅ NOTIFY ALL WARDENS - NEW ROOM REQUEST
        wardens = User.query.filter_by(role='warden', is_active=True).all()
        for warden in wardens:
            create_notification(
                user_id=warden.userid,
                title="🏠 New Room Request",
                message=f"New room request from {student.fullname} for Room {room.block}-{room.roomnumber}",
                type='info',
                link='/warden/pending-requests'
            )
        
        flash('Room request submitted successfully. Await approval.', 'success')
        return redirect(url_for('student.dashboard'))
    
    return render_template('student/room_request.html', rooms=available_rooms, student=student)

@student_bp.route('/complaint', methods=['GET', 'POST'])
@login_required
@student_required
def lodge_complaint():
    student = Student.query.filter_by(userid=current_user.userid).first()
    
    # Check for any allocation (pending or active)
    any_allocation = RoomAllocation.query.filter_by(
        studentid=student.studentid
    ).filter(RoomAllocation.status.in_(['pending_approval', 'active', 'pending_payment'])).first()
    
    if not any_allocation:
        flash('⚠️ You must request a room first before lodging any complaints.', 'warning')
        return redirect(url_for('student.request_room'))
    
    # Check for active allocation
    active_allocation = RoomAllocation.query.filter_by(
        studentid=student.studentid,
        status='active'
    ).first()
    
    # ✅ HANDLE POST REQUEST (FORM SUBMISSION)
    if request.method == 'POST':
        title = request.form.get('title')
        description = request.form.get('description')
        category = request.form.get('category')
        priority = request.form.get('priority', 'medium')
        complaint_type = request.form.get('complaint_type')
        location = request.form.get('location', '')
        
        if complaint_type == 'room' and not active_allocation:
            flash('⚠️ Room-specific complaints require an allocated room.', 'warning')
            return render_template('student/complaint_form.html',
                                 allocation=active_allocation,
                                 any_allocation=any_allocation)
        
        roomid = None
        location_text = ''
        
        if complaint_type == 'room':
            roomid = active_allocation.roomid
            location_text = f"Room {active_allocation.room.block}-{active_allocation.room.roomnumber}"
        else:
            if not location.strip():
                flash('Please specify the location for general area complaints.', 'warning')
                return render_template('student/complaint_form.html',
                                     allocation=active_allocation,
                                     any_allocation=any_allocation)
            location_text = location
        
        complaint = Complaint(
            studentid=student.studentid,
            title=title,
            complainttype=category,
            category=category,
            description=description,
            priority=priority,
            roomid=roomid,
            location=location_text,
            status='open'
        )
        
        # Handle file attachment
        if 'attachment' in request.files:
            file = request.files['attachment']
            if file and file.filename:
                file.seek(0, 2)
                file_size = file.tell()
                file.seek(0)
                
                if file_size > 5 * 1024 * 1024:
                    flash('⚠️ Attachment file size must be less than 5MB', 'warning')
                    return render_template('student/complaint_form.html',
                                         allocation=active_allocation,
                                         any_allocation=any_allocation)
                
                filename = secure_filename(f"{int(datetime.now().timestamp())}_{file.filename}")
                filepath = os.path.join('static', 'uploads', 'complaints', filename)
                os.makedirs(os.path.dirname(filepath), exist_ok=True)
                file.save(filepath)
                complaint.attachment = f'uploads/complaints/{filename}'
        
        db.session.add(complaint)
        db.session.commit()
        
        # ✅ NOTIFY WARDENS
        wardens = User.query.filter_by(role='warden', is_active=True).all()
        for warden in wardens:
            create_notification(
                user_id=warden.userid,
                title="⚠️ New Complaint Lodged",
                message=f"New {category} complaint from {student.fullname}: {title}",
                type='warning',
                link='/warden/complaints'
            )
        
        log_complaint_creation(complaint)
        flash(f'✅ Complaint submitted successfully for {location_text}.', 'success')
        return redirect(url_for('student.complaints_list'))
    
    # ✅ HANDLE GET REQUEST (SHOW FORM) - THIS IS MANDATORY!
    return render_template('student/complaint_form.html',
                         allocation=active_allocation,
                         any_allocation=any_allocation)

@student_bp.route('/complaints')
@login_required
@student_required
def complaints_list():
    student = Student.query.filter_by(userid=current_user.userid).first()
    
    complaints = Complaint.query.filter_by(
        studentid=student.studentid
    ).order_by(Complaint.created_at.desc()).all()
    
    return render_template('student/complaints_list.html', complaints=complaints)

@student_bp.route('/payments')
@login_required
@student_required
def payments():
    student = Student.query.filter_by(userid=current_user.userid).first()
    payments = Payment.query.filter_by(studentid=student.studentid).order_by(Payment.created_at.desc()).all()
    return render_template('student/payments.html', payments=payments)

@student_bp.route('/submit-payment/<int:payment_id>', methods=['GET', 'POST'])
@login_required
@student_required
def submit_payment(payment_id):
    student = Student.query.filter_by(userid=current_user.userid).first()
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.studentid != student.studentid:
        flash('Unauthorized access', 'danger')
        return redirect(url_for('student.payments'))
    
    if payment.status != 'pending':
        flash('This payment has already been submitted', 'info')
        return redirect(url_for('student.payments'))
    
    if request.method == 'POST':
        transaction_id = request.form.get('transaction_id')
        payer_name = request.form.get('payer_name')
        payment_date_str = request.form.get('payment_date')
        payment_time_str = request.form.get('payment_time')
        bank_name = request.form.get('bank_name')
        
        if not all([transaction_id, payer_name, payment_date_str, payment_time_str, bank_name]):
            flash('All fields are required', 'warning')
            return render_template('student/submit_payment.html', payment=payment)
        
        payment.transactionid = transaction_id  # ← FIXED: was transaction_id, should be transactionid
        payment.payer_name = payer_name
        payment.paymentdate = datetime.strptime(payment_date_str, '%Y-%m-%d')
        payment.payment_time = datetime.strptime(payment_time_str, '%H:%M').time()
        payment.bank_name = bank_name
        payment.paymentmethod = request.form.get('paymentmethod', 'Online')  # ← ADD THIS
        payment.status = 'paid'
        
        db.session.commit()
        
        # ✅ NOTIFY ALL ACCOUNTANTS - NEW PAYMENT SUBMISSION
        accountants = User.query.filter_by(role='accountant', is_active=True).all()
        for accountant in accountants:
            create_notification(
                user_id=accountant.userid,
                title="💰 New Payment Submitted",
                message=f"Payment of ₹{payment.amount} submitted by {student.fullname} (TXN: {payment.transactionid})",
                type='info',
                link='/accountant/pending-payments'
            )
        
        flash('✅ Payment details submitted successfully! Awaiting accountant verification.', 'success')
        return redirect(url_for('student.payments'))
    
    return render_template('student/submit_payment.html', payment=payment)

@student_bp.route('/payment/receipt/<int:payment_id>')
@login_required
@student_required
def download_receipt(payment_id):
    """Generate and download payment receipt PDF"""
    payment = Payment.query.get_or_404(payment_id)
    
    # Get student record properly
    student = Student.query.filter_by(userid=current_user.userid).first()
    
    if not student:
        flash('Student record not found', 'danger')
        return redirect(url_for('student.payments'))
    
    # Verify payment belongs to current student
    if payment.studentid != student.studentid:
        flash('Access denied', 'danger')
        return redirect(url_for('student.payments'))
    
    # Only verified payments can have receipts
    if payment.status != 'verified':
        flash('Receipt only available for verified payments', 'warning')
        return redirect(url_for('student.payments'))
    
    # Generate PDF receipt using pdf_generator utility
    return generate_payment_receipt(payment)
