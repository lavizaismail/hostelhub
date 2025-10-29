@admin_bp.route('/reports')
@login_required
@admin_required
def reports():
    # Calculate report statistics
    total_users = User.query.count()
    total_students = Student.query.count()
    total_rooms = Room.query.count()
    occupied_rooms = Room.query.filter(Room.current_occupancy > 0).count()
    
    # Payment statistics
    total_revenue = db.session.query(db.func.sum(Payment.amount)).filter_by(status='verified').scalar() or 0
    pending_payments = Payment.query.filter_by(status='pending').count()
    
    # Complaint statistics
    total_complaints = Complaint.query.count()
    resolved_complaints = Complaint.query.filter_by(status='resolved').count()
    pending_complaints = Complaint.query.filter(Complaint.status.in_(['open', 'in_progress'])).count()
    
    # Active allocations
    active_allocations = RoomAllocation.query.filter_by(status='active').count()
    
    return render_template('admin/reports.html',
                         total_users=total_users,
                         total_students=total_students,
                         total_rooms=total_rooms,
                         occupied_rooms=occupied_rooms,
                         total_revenue=total_revenue,
                         pending_payments=pending_payments,
                         total_complaints=total_complaints,
                         resolved_complaints=resolved_complaints,
                         pending_complaints=pending_complaints,
                         active_allocations=active_allocations)
