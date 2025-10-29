import re

def validate_phone(phone):
    """Validate phone number format"""
    pattern = r'^[+]?[0-9]{10,15}$'
    return re.match(pattern, phone) is not None

def validate_email(email):
    """Validate email format"""
    pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
    return re.match(pattern, email) is not None

def validate_rollnumber(rollnumber):
    """Validate roll number format"""
    return len(rollnumber) >= 3 and rollnumber.isalnum()
