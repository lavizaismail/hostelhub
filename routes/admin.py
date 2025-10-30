from datetime import datetime, timedelta  # ← Add timedelta here
import shutil
import os
from werkzeug.utils import secure_filename
from flask import send_file, Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required, current_user
from models import db, User, Student, Room, RoomAllocation, Payment, Complaint, AuditLog
from functools import wraps
import calendar
from utils.export import export_users_to_csv, export_rooms_to_csv, export_complaints_to_csv
from utils.audit import log_user_activation, log_room_creation

admin_bp = Blueprint('admin', __name__)

def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('Access denied. Admins only.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# ============= DASHBOARD =============
@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    total_rooms = Room.query.count()
    total_students = Student.query.count()
    total_users = User.query.count()
    occupied_rooms = Room.query.filter(Room.current_occupancy > 0).count()
    vacant_rooms = Room.query.filter(Room.current_occupancy < Room.capacity).count()
    maintenance_rooms = 0
    active_allocations = RoomAllocation.query.filter_by(status='active').count()
    pending_users = User.query.filter_by(is_active=False).count()
    
    today = datetime.today()
    months = []
    monthly_revenue = []
    
    for i in range(5, -1, -1):
        month = (today.month - i - 1) % 12 + 1
        year = today.year - ((today.month - i - 1) // 12)
        month_name = calendar.month_abbr[month]
        months.append(month_name)
        
        start_dt = datetime(year, month, 1)
        if month == 12:
            end_dt = datetime(year + 1, 1, 1)
        else:
            end_dt = datetime(year, month + 1, 1)
        
        revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'verified',
            Payment.created_at >= start_dt,
            Payment.created_at < end_dt
        ).scalar() or 0
        monthly_revenue.append(float(revenue))
    
    open_complaints = Complaint.query.filter_by(status='open').count()
    in_progress_complaints = Complaint.query.filter_by(status='in_progress').count()
    resolved_complaints = Complaint.query.filter_by(status='resolved').count()
    
    return render_template('admin/dashboard.html',
                         total_rooms=total_rooms,
                         occupied_rooms=occupied_rooms,
                         vacant_rooms=vacant_rooms,
                         maintenance_rooms=maintenance_rooms,
                         total_students=total_students,
                         total_users=total_users,
                         active_allocations=active_allocations,
                         pending_users=pending_users,
                         months=months,
                         monthly_revenue=monthly_revenue,
                         open_complaints=open_complaints,
                         in_progress_complaints=in_progress_complaints,
                         resolved_complaints=resolved_complaints)

# ============= USERS =============
@admin_bp.route('/users')
@login_required
@admin_required
def users():
    search = request.args.get('search', '')
    role_filter = request.args.get('role', '')
    status_filter = request.args.get('status', '')
    query = User.query
    
    if search:
        query = query.filter(
            db.or_(
                User.username.ilike(f'%{search}%'),
                User.email.ilike(f'%{search}%')
            )
        )
    if role_filter:
        query = query.filter_by(role=role_filter)
    if status_filter == 'active':
        query = query.filter_by(is_active=True)
    elif status_filter == 'inactive':
        query = query.filter_by(is_active=False)
    
    users = query.order_by(User.created_at.desc()).all()
    return render_template('admin/users.html', users=users)

@admin_bp.route('/activate/<int:user_id>')
@login_required
@admin_required
def activate_user(user_id):
    user = User.query.get_or_404(user_id)
    user.is_active = True
    db.session.commit()
    log_user_activation(user, True)
    flash(f'User {user.username} activated.', 'success')
    return redirect(url_for('admin.users'))

@admin_bp.route('/deactivate/<int:user_id>')
@login_required
@admin_required
def deactivate_user(user_id):
    user = User.query.get_or_404(user_id)
    if user.userid == current_user.userid:
        flash('Cannot deactivate self.', 'danger')
    else:
        user.is_active = False
        db.session.commit()
        log_user_activation(user, False)
        flash(f'User {user.username} deactivated.', 'info')
    return redirect(url_for('admin.users'))

# ============= ROOMS =============
@admin_bp.route('/rooms')
@login_required
@admin_required
def rooms():
    status_filter = request.args.get('status', '')
    block_filter = request.args.get('block', '')
    query = Room.query
    
    if status_filter:
        query = query.filter_by(status=status_filter)
    if block_filter:
        query = query.filter_by(block=block_filter)
    
    rooms = query.order_by(Room.block, Room.roomnumber).all()
    blocks = db.session.query(Room.block).distinct().all()
    blocks = [b[0] for b in blocks]
    return render_template('admin/rooms.html', rooms=rooms, blocks=blocks)

@admin_bp.route('/room/new', methods=['GET', 'POST'])
@login_required
@admin_required
def room_new():
    if request.method == 'POST':
        room = Room(
            block=request.form.get('block'),
            roomnumber=request.form.get('roomnumber'),
            capacity=int(request.form.get('capacity')),
            gender=request.form.get('gender'),
            floor=int(request.form.get('floor')),
            monthly_rent=float(request.form.get('rent', 0)),
            amenities=request.form.get('amenities'),
            status='vacant'
        )
        db.session.add(room)
        db.session.commit()
        log_room_creation(room)
        flash('Room added successfully.', 'success')
        return redirect(url_for('admin.rooms'))
    return render_template('admin/room_form.html', room=None)

@admin_bp.route('/room/edit/<int:room_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def room_edit(room_id):
    room = Room.query.get_or_404(room_id)
    if request.method == 'POST':
        room.block = request.form.get('block')
        room.roomnumber = request.form.get('roomnumber')
        room.capacity = int(request.form.get('capacity'))
        room.gender = request.form.get('gender')
        room.floor = int(request.form.get('floor'))
        room.monthly_rent = float(request.form.get('rent', 0))
        room.amenities = request.form.get('amenities')
        room.status = request.form.get('status')
        db.session.commit()
        flash('Room updated successfully.', 'success')
        return redirect(url_for('admin.rooms'))
    return render_template('admin/room_form.html', room=room)

# ============= COMPLAINTS =============
@admin_bp.route('/complaints')
@login_required
@admin_required
def complaints():
    status = request.args.get('status', None)
    priority = request.args.get('priority', None)
    query = Complaint.query.join(Student)
    
    if status:
        query = query.filter_by(status=status)
    if priority:
        query = query.filter_by(priority=priority)
    
    complaints = query.options(
        db.joinedload(Complaint.student)
    ).order_by(Complaint.created_at.desc()).all()
    
    return render_template('admin/complaints.html', complaints=complaints)

@admin_bp.route('/complaint/<int:complaint_id>')
@login_required
@admin_required
def complaint_detail(complaint_id):
    complaint = Complaint.query.join(Student).options(
        db.joinedload(Complaint.student)
    ).filter(Complaint.complaintid == complaint_id).first_or_404()
    
    # Get all active maintenance staff
    maintenance_staff = User.query.filter_by(
        role='maintenance',
        is_active=True
    ).all()
    
    print(f"DEBUG: Found {len(maintenance_staff)} maintenance staff members")
    for staff in maintenance_staff:
        print(f"  - {staff.username} (ID: {staff.userid})")
    
    return render_template('admin/complaint_detail.html', 
                         complaint=complaint, 
                         maintenance_staff=maintenance_staff)

# ✅ NEW ROUTE: Assign complaint to maintenance staff
@admin_bp.route('/complaint/<int:complaint_id>/assign', methods=['POST'])
@login_required
@admin_required
def assign_complaint(complaint_id):
    """Assign a complaint to maintenance staff"""
    complaint = Complaint.query.get_or_404(complaint_id)
    
    maintenance_id = request.form.get('maintenance_id')
    
    if not maintenance_id:
        flash('Please select a maintenance staff member.', 'danger')
        return redirect(url_for('admin.complaint_detail', complaint_id=complaint_id))
    
    # Verify the user is maintenance staff
    maintenance_staff = User.query.filter_by(
        userid=maintenance_id,
        role='maintenance',
        is_active=True
    ).first()
    
    if not maintenance_staff:
        flash('Invalid maintenance staff selected.', 'danger')
        return redirect(url_for('admin.complaint_detail', complaint_id=complaint_id))
    
    # Assign the complaint
    complaint.assignedto = maintenance_id
    complaint.status = 'in_progress'
    db.session.commit()
    
    # Notify the maintenance staff
    create_notification(
        user_id=maintenance_id,
        title="🔧 New Complaint Assigned",
        message=f"You have been assigned complaint #{complaint.complaintid}: {complaint.description[:50]}...",
        type='info',
        link=f'/maintenance/complaints/{complaint.complaintid}'
    )
    
    flash(f'Complaint assigned to {maintenance_staff.username} successfully.', 'success')
    return redirect(url_for('admin.complaint_detail', complaint_id=complaint_id))

# ============= REPORTS =============
@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    try:
        # Total counts
        total_students = Student.query.count()
        total_rooms = Room.query.count()
        available_rooms = Room.query.filter(Room.status == 'vacant').count()
        maintenance_rooms = Room.query.filter(Room.status == 'maintenance').count()
        
        # Occupied rooms (rooms with current_occupancy > 0)
        occupied_rooms = Room.query.filter(Room.current_occupancy > 0).count()
        
        # Total complaints
        total_complaints = Complaint.query.count()
        pending_complaints = Complaint.query.filter(Complaint.status == 'pending').count()
        resolved_complaints = Complaint.query.filter(Complaint.status == 'resolved').count()
        
        # Total revenue (all verified payments) - FIXED!
        total_revenue = db.session.query(db.func.sum(Payment.amount)).filter(
            Payment.status == 'verified'
        ).scalar() or 0
        
        # Payment counts
        verified_payments = Payment.query.filter(Payment.status == 'verified').count()
        pending_payments = Payment.query.filter(Payment.status == 'pending').count()
        
        # CREATE STATS DICTIONARY - ENSURE ALL VALUES ARE PRESENT
        stats = {
            'total_students': total_students,
            'total_rooms': total_rooms,
            'occupied_rooms': occupied_rooms,
            'available_rooms': available_rooms,
            'maintenance_rooms': maintenance_rooms,
            'total_complaints': total_complaints,
            'total_revenue': float(total_revenue),
            'pending_complaints': pending_complaints,
            'resolved_complaints': resolved_complaints,
            'verified_payments': verified_payments,
            'pending_payments': pending_payments
        }
        
        # DEBUG: Print stats to console
        print("=" * 50)
        print("REPORTS STATS DEBUG:")
        for key, value in stats.items():
            print(f"{key}: {value}")
        print("=" * 50)
        
        return render_template('admin/reports.html', stats=stats)
        
    except Exception as e:
        flash(f'Error generating reports: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))



# ============= AUDIT LOGS =============
@admin_bp.route('/audit-logs')
@login_required
@admin_required
def audit_logs():
    try:
        # Get filter parameters
        user_id = request.args.get('user_id', type=int)
        action = request.args.get('action', '')
        start_date = request.args.get('start_date')
        
        # Base query
        query = AuditLog.query
        
        # Apply filters
        if user_id:
            query = query.filter(AuditLog.userid == user_id)
        if action:
            query = query.filter(AuditLog.action.like(f'%{action}%'))
        if start_date:
            query = query.filter(AuditLog.timestamp >= start_date)
        
        # Get logs
        logs = query.order_by(AuditLog.timestamp.desc()).limit(200).all()
        
        # Get all users for filter dropdown
        users = User.query.all()
        
        return render_template('admin/audit_logs.html', logs=logs, users=users)
    except Exception as e:
        flash(f'Error loading audit logs: {str(e)}', 'danger')
        return redirect(url_for('admin.dashboard'))

# ============= BACKUP & RESTORE =============
@admin_bp.route('/backup')
@login_required
@admin_required
def backup_page():
    """Display backup management page"""
    backup_dir = 'backups'
    backups = []
    
    if os.path.exists(backup_dir):
        for filename in os.listdir(backup_dir):
            if filename.endswith('.db'):
                filepath = os.path.join(backup_dir, filename)
                size = os.path.getsize(filepath)
                timestamp = os.path.getmtime(filepath)
                backups.append({
                    'filename': filename,
                    'size': f'{size / 1024:.2f} KB',
                    'date': datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                })
    
    backups.sort(key=lambda x: x['date'], reverse=True)
    return render_template('admin/backup.html', backups=backups)

@admin_bp.route('/backup/create', methods=['POST'])
@login_required
@admin_required
def create_backup():
    """Create database backup"""
    try:
        backup_dir = 'backups'
        os.makedirs(backup_dir, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        backup_name = f'hostelhub_backup_{timestamp}.db'
        backup_path = os.path.join(backup_dir, backup_name)
        
        db_path = 'instance/hostelhub.db'
        if not os.path.exists(db_path):
            db_path = 'hostelhub.db'
        
        shutil.copy2(db_path, backup_path)
        flash(f'✅ Backup created successfully: {backup_name}', 'success')
    except Exception as e:
        flash(f'❌ Backup failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_page'))

@admin_bp.route('/backup/download/<filename>')
@login_required
@admin_required
def download_backup(filename):
    """Download backup file"""
    try:
        backup_path = os.path.join('backups', secure_filename(filename))
        if os.path.exists(backup_path):
            return send_file(backup_path, as_attachment=True)
        else:
            flash('Backup file not found', 'danger')
    except Exception as e:
        flash(f'Download failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_page'))

@admin_bp.route('/backup/restore/<filename>', methods=['POST'])
@login_required
@admin_required
def restore_backup(filename):
    """Restore database from backup"""
    try:
        backup_path = os.path.join('backups', secure_filename(filename))
        
        if not os.path.exists(backup_path):
            flash('Backup file not found', 'danger')
            return redirect(url_for('admin.backup_page'))
        
        db_path = 'instance/hostelhub.db'
        if not os.path.exists(db_path):
            db_path = 'hostelhub.db'
        
        safety_backup = f'backups/pre_restore_{datetime.now().strftime("%Y%m%d_%H%M%S")}.db'
        shutil.copy2(db_path, safety_backup)
        shutil.copy2(backup_path, db_path)
        
        flash(f'✅ Database restored successfully from {filename}', 'success')
        flash(f'⚠️ Safety backup created: {os.path.basename(safety_backup)}', 'info')
    except Exception as e:
        flash(f'❌ Restore failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_page'))

@admin_bp.route('/backup/delete/<filename>', methods=['POST'])
@login_required
@admin_required
def delete_backup(filename):
    """Delete backup file"""
    try:
        backup_path = os.path.join('backups', secure_filename(filename))
        if os.path.exists(backup_path):
            os.remove(backup_path)
            flash(f'✅ Backup deleted: {filename}', 'success')
        else:
            flash('Backup file not found', 'danger')
    except Exception as e:
        flash(f'❌ Delete failed: {str(e)}', 'danger')
    
    return redirect(url_for('admin.backup_page'))

# ============= EXPORT ROUTES =============
@admin_bp.route('/export/users')
@login_required
@admin_required
def export_users():
    users = User.query.all()
    return export_users_to_csv(users)

@admin_bp.route('/export/rooms')
@login_required
@admin_required
def export_rooms():
    rooms = Room.query.all()
    return export_rooms_to_csv(rooms)

@admin_bp.route('/export/complaints')
@login_required
@admin_required
def export_complaints():
    complaints = Complaint.query.all()
    return export_complaints_to_csv(complaints)
