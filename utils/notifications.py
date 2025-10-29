from flask import current_app
from flask_mail import Mail, Message
from models import db, Notification
from datetime import datetime

mail = Mail()

# ============= EMAIL FUNCTIONS (Your existing code) =============
def send_email(to, subject, body):
    """Send email notification"""
    try:
        msg = Message(
            subject=subject,
            recipients=[to],
            body=body,
            sender=current_app.config['MAIL_DEFAULT_SENDER']
        )
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Email error: {e}")
        return False

def send_room_allocation_email(student_email, student_name, room_details):
    """Send room allocation confirmation email"""
    subject = "Room Allocation Confirmation"
    body = f"""
Dear {student_name},

Your room allocation has been approved!

Room Details:
- Block: {room_details['block']}
- Room Number: {room_details['roomnumber']}
- Floor: {room_details['floor']}

Please contact the hostel office for further instructions.

Best regards,
Hostel Management
"""
    return send_email(student_email, subject, body)

def send_complaint_update_email(student_email, student_name, complaint_title, status):
    """Send complaint status update email"""
    subject = f"Complaint Update: {complaint_title}"
    body = f"""
Dear {student_name},

Your complaint "{complaint_title}" has been updated.

Current Status: {status.upper()}

Thank you for your patience.

Best regards,
Hostel Management
"""
    return send_email(student_email, subject, body)


# ============= IN-APP NOTIFICATION FUNCTIONS (NEW - ADD THESE) =============
def create_notification(user_id, title, message, type='info', link=None):
    """Create in-app notification for user"""
    try:
        notification = Notification(
            userid=user_id,
            title=title,
            message=message,
            type=type,
            link=link
        )
        db.session.add(notification)
        db.session.commit()
        return notification
    except Exception as e:
        print(f"Notification error: {e}")
        db.session.rollback()
        return None

def notify_room_allocation(student, room, status='approved'):
    """Notify student about room allocation"""
    if status == 'approved':
        title = "🎉 Room Allocation Approved!"
        message = f"Your room request for {room.block}-{room.roomnumber} has been approved. Welcome to your new room!"
        type_val = 'success'
        link = '/student/my-room'
    else:
        title = "❌ Room Request Rejected"
        message = f"Your room request for {room.block}-{room.roomnumber} has been rejected. Please contact the warden."
        type_val = 'danger'
        link = '/student/request-room'
    
    # Create in-app notification
    create_notification(student.userid, title, message, type_val, link)

def notify_complaint_status(complaint, new_status):
    """Notify student about complaint status change"""
    status_messages = {
        'assigned': {
            'title': '🔧 Complaint Assigned',
            'message': f'Your complaint "{complaint.title}" has been assigned to maintenance staff.',
            'type': 'info'
        },
        'in_progress': {
            'title': '⚙️ Work in Progress',
            'message': f'Maintenance staff is working on your complaint "{complaint.title}".',
            'type': 'info'
        },
        'resolved': {
            'title': '✅ Complaint Resolved',
            'message': f'Your complaint "{complaint.title}" has been resolved!',
            'type': 'success'
        },
        'closed': {
            'title': '🔒 Complaint Closed',
            'message': f'Your complaint "{complaint.title}" has been closed.',
            'type': 'success'
        }
    }
    
    notification_data = status_messages.get(new_status)
    if notification_data:
        create_notification(
            complaint.student.userid,
            notification_data['title'],
            notification_data['message'],
            notification_data['type'],
            '/student/complaints'
        )

def notify_payment_verification(payment, student):
    """Notify student about payment verification"""
    title = "💰 Payment Verified"
    message = f"Your payment of ₹{payment.amount} has been verified successfully."
    create_notification(student.userid, title, message, 'success', '/student/payments')

# ADD THESE FUNCTIONS TO THE END OF YOUR CURRENT notifications.py

def notify_room_request_submission(student, room):
    """Notify warden when student submits room request"""
    from models import User
    wardens = User.query.filter_by(role='warden', is_active=True).all()
    for warden in wardens:
        create_notification(
            warden.userid,
            '🏠 New Room Request',
            f'{student.fullname} has submitted a room request for {room.block}-{room.roomnumber}.',
            'info',
            '/warden/pending-requests'
        )

def notify_complaint_submission(complaint, student):
    """Notify warden and maintenance when complaint is submitted"""
    from models import User
    
    # Notify warden
    wardens = User.query.filter_by(role='warden', is_active=True).all()
    for warden in wardens:
        create_notification(
            warden.userid,
            '⚠️ New Complaint',
            f'{student.fullname} reported: {complaint.title}',
            'warning',
            f'/warden/complaint/{complaint.complaintid}'
        )
    
    # Notify maintenance staff
    maintenance_users = User.query.filter_by(role='maintenance', is_active=True).all()
    for maint in maintenance_users:
        create_notification(
            maint.userid,
            '🔧 New Complaint',
            f'New {complaint.category} complaint: {complaint.title}',
            'info',
            f'/maintenance/complaint/{complaint.complaintid}'
        )

def notify_payment_submission(payment, student):
    """Notify accountant when student submits payment"""
    from models import User
    accountants = User.query.filter_by(role='accountant', is_active=True).all()
    for accountant in accountants:
        create_notification(
            accountant.userid,
            '💰 New Payment Submitted',
            f'{student.fullname} submitted ₹{payment.amount} for verification.',
            'info',
            '/accountant/pending-payments'
        )
