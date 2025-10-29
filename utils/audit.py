from models import db, AuditLog
from flask_login import current_user
from flask import request
from datetime import datetime

def log_login(user):
    try:
        log = AuditLog(
            userid=user.userid,
            action='login',
            entity_type='user',
            entity_id=user.userid,
            details=f'User {user.username} logged in',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_logout(user):
    try:
        log = AuditLog(
            userid=user.userid,
            action='logout',
            entity_type='user',
            entity_id=user.userid,
            details=f'User {user.username} logged out',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_user_creation(user):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='create_user',
            entity_type='user',
            entity_id=user.userid,
            details=f'User {user.username} created with role {user.role}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_user_activation(user, status):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='user_activation_change',
            entity_type='user',
            entity_id=user.userid,
            details=f'User {user.username} {"activated" if status else "deactivated"}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_room_creation(room):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='room_created',
            entity_type='room',
            entity_id=room.roomid,
            details=f'Room {room.block}-{room.roomnumber} created',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_room_update(room):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='room_updated',
            entity_type='room',
            entity_id=room.roomid,
            details=f'Room {room.block}-{room.roomnumber} updated',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_room_deletion(room):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='room_deleted',
            entity_type='room',
            entity_id=room.roomid,
            details=f'Room {room.block}-{room.roomnumber} deleted',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_room_allocation(allocation, student, room):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='room_allocation',
            entity_type='allocation',
            entity_id=allocation.allocationid,
            details=f'Room {room.block}-{room.roomnumber} allocated to {student.name}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_room_status_change(room, old_status, new_status):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='room_status_change',
            entity_type='room',
            entity_id=room.roomid,
            details=f'Room {room.block}-{room.roomnumber} status changed from {old_status} to {new_status}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_complaint_creation(complaint):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='complaint_created',
            entity_type='complaint',
            entity_id=complaint.complaintid,
            details=f'Complaint created: {complaint.title}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_complaint_status_change(complaint, old_status, new_status):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='complaint_status_change',
            entity_type='complaint',
            entity_id=complaint.complaintid,
            details=f'Complaint status changed from {old_status} to {new_status}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_payment_verification(payment, status):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='payment_verification',
            entity_type='payment',
            entity_id=payment.paymentid,
            details=f'Payment {status} for student {payment.student.fullname}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()

def log_settings_change(setting_name, old_value, new_value):
    try:
        log = AuditLog(
            userid=current_user.userid if current_user.is_authenticated else None,
            action='settings_change',
            entity_type='settings',
            details=f'{setting_name} changed from {old_value} to {new_value}',
            ipaddress=request.remote_addr,
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        db.session.commit()
    except Exception as e:
        print(f"Audit log error: {e}")
        db.session.rollback()
