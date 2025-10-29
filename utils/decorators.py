from functools import wraps
from flask import flash, redirect, url_for
from flask_login import current_user

def role_required(role):
    """Decorator to restrict access by role"""
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            if not current_user.is_authenticated:
                flash('Please login to access this page.', 'danger')
                return redirect(url_for('auth.login'))
            if current_user.role != role:
                flash('Access denied.', 'danger')
                return redirect(url_for('index'))
            return f(*args, **kwargs)
        return decorated_function
    return decorator
