from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Payment, Student, RoomAllocation, Room
from functools import wraps
from datetime import datetime
from utils.notifications import create_notification
from utils.audit import log_payment_verification

accountant_bp = Blueprint('accountant', __name__)

def accountant_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'accountant':
            flash('Access denied. Accountants only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@accountant_bp.route('/dashboard')
@login_required
@accountant_required
def dashboard():
    status_filter = request.args.get('status', 'all')
    
    pending_count = Payment.query.filter_by(status='paid').count()
    verified_count = Payment.query.filter_by(status='verified').count()
    
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status == 'verified'
    ).scalar() or 0
    
    outstanding_amount = db.session.query(db.func.sum(Payment.amount)).filter(
        Payment.status.in_(['pending', 'paid'])
    ).scalar() or 0
    
    if status_filter == 'paid':
        payments = Payment.query.filter_by(status='paid').order_by(Payment.created_at.desc()).limit(50).all()
    elif status_filter == 'verified':
        payments = Payment.query.filter_by(status='verified').order_by(Payment.created_at.desc()).limit(50).all()
    else:
        payments = Payment.query.order_by(Payment.created_at.desc()).limit(50).all()
    
    return render_template('accountant/dashboard.html',
                           pending_count=pending_count,
                           verified_count=verified_count,
                           total_revenue=float(total_revenue),
                           outstanding_amount=float(outstanding_amount),
                           payments=payments)

@accountant_bp.route('/pending-payments')
@login_required
@accountant_required
def pending_payments():
    payments = Payment.query.filter_by(
        status='paid'
    ).order_by(Payment.created_at.desc()).all()
    
    return render_template('accountant/pending_payments.html', payments=payments)

# ✅ ADD THIS MISSING ROUTE:
@accountant_bp.route('/payment-detail/<int:payment_id>')
@login_required
@accountant_required
def payment_detail(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    allocation = RoomAllocation.query.filter_by(
        studentid=payment.studentid
    ).first()
    
    return render_template('accountant/payment_detail.html', 
                         payment=payment,
                         allocation=allocation)

@accountant_bp.route('/verify-payment/<int:payment_id>', methods=['POST'])
@login_required
@accountant_required
def verify_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.status != 'paid':
        flash('This payment has already been processed', 'warning')
        return redirect(url_for('accountant.pending_payments'))
    
    payment.status = 'verified'
    payment.verified_by = current_user.userid
    payment.verification_date = datetime.utcnow()
    
    allocation = RoomAllocation.query.filter_by(
        studentid=payment.studentid,
        status='pending_payment'
    ).first()
    
    if allocation:
        allocation.status = 'active'
        allocation.allocation_date = datetime.utcnow()
        
        room = Room.query.get(allocation.roomid)
        if room:
            room.current_occupancy = (room.current_occupancy or 0) + 1
            
            create_notification(
                user_id=payment.student.userid,
                title="🎉 Payment Verified & Room Allocated!",
                message=f"Your payment has been verified and Room {room.block}-{room.roomnumber} has been allocated to you. Welcome!",
                type='success',
                link='/student/my-room'
            )
            
            flash(f'✅ Payment verified and Room {room.block}-{room.roomnumber} allocated to {payment.student.fullname}', 'success')
    
    db.session.commit()
    log_payment_verification(payment, 'verified')
    
    return redirect(url_for('accountant.pending_payments'))

@accountant_bp.route('/reject-payment/<int:payment_id>', methods=['POST'])
@login_required
@accountant_required
def reject_payment(payment_id):
    payment = Payment.query.get_or_404(payment_id)
    
    if payment.status != 'paid':
        flash('This payment has already been processed', 'warning')
        return redirect(url_for('accountant.pending_payments'))
    
    reason = request.form.get('reason', 'Invalid payment details')
    
    payment.status = 'pending'
    payment.rejection_reason = reason
    payment.transactionid = None
    payment.bank_name = None
    payment.payment_date = None
    payment.payment_time = None
    payment.payer_name = None
    
    db.session.commit()
    
    create_notification(
        user_id=payment.student.userid,
        title="❌ Payment Rejected",
        message=f"Your payment submission was rejected. Reason: {reason}. Please resubmit correct details.",
        type='danger',
        link='/student/payments'
    )
    
    log_payment_verification(payment, 'rejected')
    flash(f'Payment rejected. Student notified to resubmit.', 'info')
    
    return redirect(url_for('accountant.pending_payments'))

@accountant_bp.route('/payment-history')
@login_required
@accountant_required
def payment_history():
    payments = Payment.query.order_by(Payment.created_at.desc()).all()
    return render_template('accountant/payment_history.html', payments=payments)
