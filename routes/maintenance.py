from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, Complaint
from functools import wraps
from datetime import datetime, date
from utils.notifications import create_notification

maintenance_bp = Blueprint('maintenance', __name__, url_prefix='/maintenance')


def maintenance_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'maintenance':
            flash('Access denied. Maintenance staff only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@maintenance_bp.route('/dashboard')
@login_required
@maintenance_required
def dashboard():
    all_complaints = Complaint.query.all()
    
    # NEW STATUS NAMES
    assigned = Complaint.query.filter_by(status='assigned').all()
    in_progress = Complaint.query.filter_by(status='in_progress').all()
    resolved = Complaint.query.filter_by(status='resolved').all()
    
    my_assigned = assigned + in_progress
    
    urgent_issues = Complaint.query.filter_by(priority='High').filter(
        Complaint.status != 'resolved'
    ).all()
    
    today = date.today()
    resolved_today = [c for c in resolved if c.resolvedat and c.resolvedat.date() == today]
    
    recent_complaints = Complaint.query.order_by(
        Complaint.created_at.desc()
    ).limit(10).all()
    
    return render_template('maintenance/dashboard.html',
                           my_assigned=my_assigned,
                           my_assigned_count=len(my_assigned),
                           urgent_count=len(urgent_issues),
                           resolved_count=len(resolved),
                           resolved_today_count=len(resolved_today),
                           total_complaints_count=len(all_complaints),
                           assigned_count=len(assigned),
                           in_progress_count=len(in_progress),
                           urgent_complaints=urgent_issues,
                           recent_complaints=recent_complaints)


@maintenance_bp.route('/complaints')
@login_required
@maintenance_required
def complaints():
    status_filter = request.args.get('status', None)
    if status_filter:
        complaints = Complaint.query.filter_by(status=status_filter).order_by(
            Complaint.created_at.desc()
        ).all()
    else:
        complaints = Complaint.query.order_by(Complaint.created_at.desc()).all()
    
    return render_template('maintenance/all_complaints.html',
                           complaints=complaints,
                           current_filter=status_filter,
                           page_title='All Complaints')


@maintenance_bp.route('/my-assigned')
@login_required
@maintenance_required
def my_assigned():
    # Assigned + In Progress
    complaints = Complaint.query.filter(
        Complaint.status.in_(['assigned', 'in_progress'])
    ).order_by(Complaint.created_at.desc()).all()
    
    return render_template('maintenance/all_complaints.html',
                           complaints=complaints,
                           current_filter='my_assigned',
                           page_title='My Assigned Complaints')


@maintenance_bp.route('/urgent')
@login_required
@maintenance_required
def urgent():
    complaints = Complaint.query.filter_by(priority='High').filter(
        Complaint.status != 'resolved'
    ).order_by(Complaint.created_at.desc()).all()
    
    return render_template('maintenance/all_complaints.html',
                           complaints=complaints,
                           current_filter='urgent',
                           page_title='Urgent Issues')


@maintenance_bp.route('/resolved')
@login_required
@maintenance_required
def resolved():
    complaints = Complaint.query.filter_by(status='resolved').order_by(
        Complaint.resolvedat.desc()
    ).all()
    
    return render_template('maintenance/all_complaints.html',
                           complaints=complaints,
                           current_filter='resolved',
                           page_title='Resolved Complaints')


@maintenance_bp.route('/complaint/<int:id>')
@login_required
@maintenance_required
def complaint_detail(id):
    complaint = Complaint.query.get_or_404(id)
    return render_template('maintenance/complaint_detail.html',
                           complaint=complaint)


@maintenance_bp.route('/update-status/<int:id>', methods=['POST'])
@login_required
@maintenance_required
def update_status(id):
    complaint = Complaint.query.get_or_404(id)
    
    new_status = request.form.get('status')
    resolution_notes = request.form.get('resolution_notes', '').strip()
    
    # Update complaint
    complaint.status = new_status
    
    if resolution_notes:
        complaint.resolutionnotes = resolution_notes
    
    if new_status == 'resolved':
        complaint.resolvedat = datetime.utcnow()
    
    db.session.commit()
    
    # NOTIFY STUDENT
    student = complaint.student
    if student and student.user:
        status_text = new_status.replace('_', ' ').title()
        
        if new_status == 'resolved':
            message = f"Your complaint has been resolved."
            if resolution_notes:
                message += f"\n\nResolution: {resolution_notes}"
            notif_type = 'success'
        elif new_status == 'in_progress':
            message = f"Your complaint is now being worked on."
            if resolution_notes:
                message += f"\n\nUpdate: {resolution_notes}"
            notif_type = 'info'
        else:  # assigned
            message = f"Your complaint has been assigned."
            if resolution_notes:
                message += f"\n\nNote: {resolution_notes}"
            notif_type = 'info'
        
        create_notification(
            user_id=student.user.userid,
            title=f"🔧 Complaint Status: {status_text}",
            message=message,
            type=notif_type,
            link='/student/complaints'
        )
    
    flash(f'✅ Complaint status updated to: {new_status.replace("_", " ").title()}', 'success')
    return redirect(url_for('maintenance.dashboard'))
