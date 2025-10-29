from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, RoomAllocation, Student, Room, Complaint, User, Payment
from functools import wraps
from datetime import datetime, timedelta
from utils.notifications import create_notification

warden_bp = Blueprint('warden', __name__)

def warden_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'warden':
            flash('Access denied. Wardens only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@warden_bp.route('/dashboard')
@login_required
@warden_required
def dashboard():
    total_rooms = Room.query.count()
    occupied_rooms = Room.query.filter(Room.current_occupancy > 0).count()
    pending_requests = RoomAllocation.query.filter_by(status='pending_approval').count()
    open_complaints = Complaint.query.filter_by(status='open').count()
    
    return render_template('warden/dashboard.html',
                         total_rooms=total_rooms,
                         occupied_rooms=occupied_rooms,
                         pending_requests=pending_requests,
                         open_complaints=open_complaints)

@warden_bp.route('/pending-requests')
@login_required
@warden_required
def pending_requests():
    allocations = RoomAllocation.query\
        .filter_by(status='pending_approval')\
        .join(Student)\
        .join(Room)\
        .order_by(RoomAllocation.request_date.desc())\
        .all()
    
    return render_template('warden/pending_requests.html', allocations=allocations)

@warden_bp.route('/approve/<int:allocation_id>')
@login_required
@warden_required
def approve_request(allocation_id):
    allocation = RoomAllocation.query.get_or_404(allocation_id)
    student = Student.query.get_or_404(allocation.studentid)
    room = Room.query.get_or_404(allocation.roomid)
    
    # Check if payment already exists
    existing_payment = Payment.query.filter_by(studentid=student.studentid, status='pending').first()
    
    if existing_payment:
        flash('⚠️ Payment already created for this student.', 'warning')
        return redirect(url_for('warden.pending_requests'))
    
    # Update allocation
    allocation.status = 'pending_payment'
    
    # Calculate total (rent + 2x security)
    total_amount = room.monthly_rent + (room.monthly_rent * 2)
    
    # CREATE PAYMENT with correct status
    payment = Payment(
        studentid=student.studentid,
        amount=total_amount,
        status='pending',  # ✅ CORRECT STATUS
        month=datetime.now().strftime('%B'),
        year=datetime.now().year
    )
    
    db.session.add(payment)
    db.session.commit()
    
    # Notify student
    create_notification(
        user_id=student.userid,
        title="🎉 Room Request Approved!",
        message=f"Your room request for {room.block}-{room.roomnumber} has been approved. Please submit payment details of ₹{total_amount} (₹{room.monthly_rent} rent + ₹{room.monthly_rent * 2} security deposit).",
        type='success',
        link='/student/payments'
    )
    
    flash(f'✅ Room request approved for {student.fullname}. Awaiting payment submission.', 'success')
    return redirect(url_for('warden.pending_requests'))

@warden_bp.route('/reject/<int:allocation_id>', methods=['POST'])
@login_required
@warden_required
def reject_request(allocation_id):
    allocation = RoomAllocation.query.get_or_404(allocation_id)
    reason = request.form.get('reason', 'No reason provided')
    
    allocation.status = 'rejected'
    allocation.rejection_reason = reason  # ✅ Store reason
    db.session.commit()
    
    create_notification(
        user_id=allocation.student.userid,
        title="❌ Room Request Rejected",
        message=f"Your room request was rejected. Reason: {reason}",
        type='danger',
        link='/student/room-request'
    )
    
    flash(f'Room request rejected', 'info')
    return redirect(url_for('warden.pending_requests'))


@warden_bp.route('/complaints')
@login_required
@warden_required
def complaints():
    # Show all complaints
    complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    return render_template('warden/complaints.html', complaints=complaints)

@warden_bp.route('/complaint/<int:id>')
@login_required
@warden_required
def complaint_detail(id):
    complaint = Complaint.query.get_or_404(id)
    return render_template('warden/complaint_detail.html', complaint=complaint)

# NEW: Forward complaint to maintenance (single button)
@warden_bp.route('/forward-complaint/<int:complaint_id>', methods=['POST'])
@login_required
@warden_required
def forward_complaint(complaint_id):
    complaint = Complaint.query.get_or_404(complaint_id)
    
    if complaint.status != 'open':
        flash('This complaint has already been forwarded', 'warning')
        return redirect(url_for('warden.complaints'))
    
    # Update complaint status to forwarded
    complaint.status = 'forwarded'
    complaint.forwarded_at = datetime.utcnow()
    db.session.commit()
    
    # Get maintenance user to notify
    maintenance_user = User.query.filter_by(role='maintenance', is_active=True).first()
    if maintenance_user:
        create_notification(
            user_id=maintenance_user.userid,
            title="🔧 New Complaint Forwarded",
            message=f"Complaint '{complaint.title}' ({complaint.category}) has been forwarded to you. Please assign staff.",
            type='info',
            link='/maintenance/dashboard'
        )
    
    flash('✅ Complaint forwarded to maintenance successfully', 'success')
    return redirect(url_for('warden.complaints'))

@warden_bp.route('/room-management')
@login_required
@warden_required
def room_management():
    rooms = Room.query.order_by(Room.block, Room.roomnumber).all()
    return render_template('warden/room_management.html', rooms=rooms)

@warden_bp.route('/students')
@login_required
@warden_required
def students():
    students = Student.query.all()
    return render_template('warden/students.html', students=students)
