from datetime import datetime

def format_date(date):
    """Format date to DD-MM-YYYY"""
    if date:
        return date.strftime('%d-%m-%Y')
    return 'N/A'

def format_datetime(dt):
    """Format datetime to DD-MM-YYYY HH:MM"""
    if dt:
        return dt.strftime('%d-%m-%Y %H:%M')
    return 'N/A'

def allowed_file(filename, allowed_extensions):
    """Check if file extension is allowed"""
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_extensions

def calculate_occupancy_percentage(occupied, total):
    """Calculate occupancy percentage"""
    if total == 0:
        return 0
    return round((occupied / total) * 100, 2)
