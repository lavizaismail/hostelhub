# init_db.py - Safe database initialization script

from app import app, db
from models import User, Student, Room, RoomAllocation, Complaint, Payment, MaintenanceStaff, Notification
from werkzeug.security import generate_password_hash
from datetime import datetime
import os

def init_database():
    """Initialize database with tables (ONLY if they don't exist) and default users"""
    
    with app.app_context():
        print("🔄 Checking database tables...")
        
        # Create tables ONLY if they don't exist (safe)
        db.create_all()
        print("✅ All tables ensured to exist!")
        
        # Check if database is empty (no users exist)
        user_count = User.query.count()
        
        if user_count == 0:
            print("📝 Creating default users...")
            
            # Create default admin user
            admin = User(
                username='admin',
                email='admin@hostelhub.com',
                password=generate_password_hash('admin123'),
                role='admin',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            # Create default warden
            warden = User(
                username='warden',
                email='warden@hostelhub.com',
                password=generate_password_hash('warden123'),
                role='warden',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            # Create default accountant
            accountant = User(
                username='accountant',
                email='accountant@hostelhub.com',
                password=generate_password_hash('accountant123'),
                role='accountant',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            # Create default maintenance staff
            maintenance_user = User(
                username='maintenance',
                email='maintenance@hostelhub.com',
                password=generate_password_hash('maintenance123'),
                role='maintenance',
                is_active=True,
                created_at=datetime.utcnow()
            )
            
            db.session.add(admin)
            db.session.add(warden)
            db.session.add(accountant)
            db.session.add(maintenance_user)
            db.session.commit()
            
            print("\n✅ Database initialized successfully!")
            print("\n🔐 DEFAULT LOGIN CREDENTIALS:")
            print("━" * 50)
            print("Admin:")
            print("   Username: admin")
            print("   Password: admin123")
            print("\nWarden:")
            print("   Username: warden")
            print("   Password: warden123")
            print("\nAccountant:")
            print("   Username: accountant")
            print("   Password: accountant123")
            print("\nMaintenance:")
            print("   Username: maintenance")
            print("   Password: maintenance123")
            print("━" * 50)
        else:
            print(f"✅ Database already has {user_count} users. Skipping user creation.")
            print("ℹ️  Tables verified/created, but existing data preserved!")

if __name__ == '__main__':
    init_database()
