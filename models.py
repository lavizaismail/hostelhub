from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin
from datetime import datetime
from werkzeug.security import generate_password_hash, check_password_hash

db = SQLAlchemy()

# ============= MAINTENANCE STAFF TABLE =============
class MaintenanceStaff(db.Model):
    __tablename__ = 'maintenance_staff'
    
    staff_id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    specialization = db.Column(db.String(50), nullable=False)
    phone = db.Column(db.String(15))
    is_active = db.Column(db.Boolean, default=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)


# ============= USER TABLE =============
class User(UserMixin, db.Model):
    __tablename__ = 'users'
    
    userid = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    email = db.Column(db.String(100), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    role = db.Column(db.String(20), nullable=False)
    is_active = db.Column(db.Boolean, default=False, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    notifications = db.relationship('Notification', backref='user', lazy=True, foreign_keys='Notification.userid')
    
    def set_password(self, password):
        self.password = generate_password_hash(password)
    
    def check_password(self, password):
        return check_password_hash(self.password, password)
    
    def get_id(self):
        return str(self.userid)


# ============= STUDENT TABLE =============
class Student(db.Model):
    __tablename__ = 'students'
    
    studentid = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    rollnumber = db.Column(db.String(20), unique=True, nullable=False)
    fullname = db.Column(db.String(100), nullable=False)
    phone = db.Column(db.String(15))
    email = db.Column(db.String(100))
    address = db.Column(db.Text)
    year = db.Column(db.Integer)
    course = db.Column(db.String(100))  # ← ADD THIS LINE!
    gender = db.Column(db.String(10))
    enrollmentdate = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    user = db.relationship('User', backref='student', uselist=False)
    allocations = db.relationship('RoomAllocation', backref='student', lazy=True)
    payments = db.relationship('Payment', backref='student', lazy=True)
    complaints = db.relationship('Complaint', backref='student', lazy=True)

# ============= ROOM TABLE =============
class Room(db.Model):
    __tablename__ = 'rooms'
    
    roomid = db.Column(db.Integer, primary_key=True)
    block = db.Column(db.String(10), nullable=False)
    roomnumber = db.Column(db.String(10), nullable=False)
    floor = db.Column(db.Integer)
    capacity = db.Column(db.Integer, nullable=False)
    current_occupancy = db.Column(db.Integer, default=0)
    monthly_rent = db.Column(db.Float, nullable=False)
    gender = db.Column(db.String(10))
    facilities = db.Column(db.Text)
    status = db.Column(db.String(20), default='vacant')
    amenities = db.Column(db.Text)
    
    # Relationships
    allocations = db.relationship('RoomAllocation', backref='room', lazy=True)
    complaints = db.relationship('Complaint', backref='room', lazy=True)
    
    def is_available(self):
        """Check if room is available for allocation"""
        return self.current_occupancy < self.capacity and self.status != 'maintenance'


# ============= ROOM ALLOCATION TABLE =============
class RoomAllocation(db.Model):
    __tablename__ = 'room_allocations'
    
    allocationid = db.Column(db.Integer, primary_key=True)
    studentid = db.Column(db.Integer, db.ForeignKey('students.studentid'), nullable=False)
    roomid = db.Column(db.Integer, db.ForeignKey('rooms.roomid'), nullable=False)
    request_date = db.Column(db.DateTime, default=datetime.utcnow)  # ✅ ADD THIS
    allocationdate = db.Column(db.DateTime)  # When actually allocated
    checkout_date = db.Column(db.DateTime)
    status = db.Column(db.String(20), default='pending_approval')
    rejection_reason = db.Column(db.Text)  # ✅ ADD THIS

# ============= PAYMENT TABLE =============
class Payment(db.Model):
    __tablename__ = 'payments'
    
    paymentid = db.Column(db.Integer, primary_key=True)
    studentid = db.Column(db.Integer, db.ForeignKey('students.studentid'), nullable=False)
    amount = db.Column(db.Float, nullable=False)
    
    # Original datetime field (when payment record was created)
    paymentdate = db.Column(db.DateTime, default=datetime.utcnow)
    
    paymentmethod = db.Column(db.String(50))
    transactionid = db.Column(db.String(100))
    status = db.Column(db.String(20), default='pending')  # ✅ FIXED DEFAULT
    receiptpath = db.Column(db.String(200))
    month = db.Column(db.String(20))
    year = db.Column(db.Integer)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # ✅ NEW FIELDS FOR PAYMENT SUBMISSION:
    payment_date = db.Column(db.Date)  # Date student made payment
    payment_time = db.Column(db.Time)  # Time student made payment
    bank_name = db.Column(db.String(100))  # Bank name
    payer_name = db.Column(db.String(100))  # Name on bank account
    
    # ✅ NEW FIELDS FOR VERIFICATION:
    verified_by = db.Column(db.Integer, db.ForeignKey('users.userid'))  # Accountant who verified
    verification_date = db.Column(db.DateTime)  # When verified
    rejection_reason = db.Column(db.Text)  # Why rejected (if rejected)

# ============= COMPLAINT TABLE =============
class Complaint(db.Model):
    __tablename__ = 'complaints'
    
    complaintid = db.Column(db.Integer, primary_key=True)
    studentid = db.Column(db.Integer, db.ForeignKey('students.studentid'), nullable=False)
    roomid = db.Column(db.Integer, db.ForeignKey('rooms.roomid'))
    
    # Main fields
    title = db.Column(db.String(200))  # ✅ ADD THIS
    complainttype = db.Column(db.String(50), nullable=False)  # Keep this
    category = db.Column(db.String(50))  # ✅ ADD THIS
    description = db.Column(db.Text, nullable=False)
    location = db.Column(db.String(200))  # ✅ ADD THIS
    attachment = db.Column(db.String(200))  # ✅ ADD THIS for file uploads
    
    # Status fields
    status = db.Column(db.String(20), default='open')
    priority = db.Column(db.String(20), default='medium')
    
    # Assignment & Resolution
    assigned_staff_id = db.Column(db.Integer, db.ForeignKey('maintenance_staff.staff_id'))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    resolvedat = db.Column(db.DateTime)
    resolutionnotes = db.Column(db.Text)
    
    # Relationships
    staff = db.relationship('MaintenanceStaff', backref='complaints')

# ============= NOTIFICATION TABLE (NEW!) =============
class Notification(db.Model):
    __tablename__ = 'notifications'
    
    notifid = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.userid'), nullable=False)
    title = db.Column(db.String(200), nullable=False)
    message = db.Column(db.Text, nullable=False)
    type = db.Column(db.String(20), default='info')  # ✅ ADD THIS
    link = db.Column(db.String(200))  # ✅ ADD THIS
    is_read = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

# ============= AUDIT LOG TABLE =============
class AuditLog(db.Model):
    __tablename__ = 'audit_logs'
    
    logid = db.Column(db.Integer, primary_key=True)
    userid = db.Column(db.Integer, db.ForeignKey('users.userid'))
    action = db.Column(db.String(100), nullable=False)
    entity_type = db.Column(db.String(50))  # e.g., 'user', 'room', 'complaint'
    entity_id = db.Column(db.Integer)  # ← ADD THIS LINE!
    details = db.Column(db.Text)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)
    ipaddress = db.Column(db.String(50))
    
    # Relationships
    user = db.relationship('User', backref='audit_logs')
