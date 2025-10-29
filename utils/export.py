import csv
from io import StringIO, BytesIO
from flask import make_response
from reportlab.lib.pagesizes import A4, landscape
from reportlab.lib import colors
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import inch
from datetime import datetime

def export_to_csv(data, headers, filename):
    """Export data to CSV"""
    si = StringIO()
    writer = csv.writer(si)
    
    # Write headers
    writer.writerow(headers)
    
    # Write data
    for row in data:
        writer.writerow(row)
    
    output = make_response(si.getvalue())
    output.headers["Content-Disposition"] = f"attachment; filename={filename}"
    output.headers["Content-type"] = "text/csv"
    return output

def export_users_to_csv(users):
    """Export users list to CSV"""
    headers = ['User ID', 'Username', 'Email', 'Role', 'Active', 'Created At']
    data = []
    
    for user in users:
        data.append([
            user.userid,
            user.username,
            user.email,
            user.role,
            'Yes' if user.is_active else 'No',
            user.created_at.strftime('%d-%m-%Y') if user.created_at else 'N/A'
        ])
    
    return export_to_csv(data, headers, f'users_export_{datetime.now().strftime("%Y%m%d")}.csv')

def export_rooms_to_csv(rooms):
    """Export rooms list to CSV"""
    headers = ['Room ID', 'Block', 'Room Number', 'Capacity', 'Status', 'Gender', 'Floor', 'Monthly Rent', 'Current Occupancy']
    data = []
    
    for room in rooms:
        data.append([
            room.roomid,
            room.block,
            room.roomnumber,
            room.capacity,
            room.status,
            room.gender,
            room.floor,
            room.monthly_rent,
            room.current_occupancy or 0
        ])
    
    return export_to_csv(data, headers, f'rooms_export_{datetime.now().strftime("%Y%m%d")}.csv')

def export_complaints_to_csv(complaints):
    """Export complaints to CSV"""
    headers = ['Complaint ID', 'Title', 'Student', 'Category', 'Priority', 'Status', 'Created Date', 'Resolved Date']
    data = []
    
    for c in complaints:
        data.append([
            c.complaintid,
            c.title,
            c.student.name,
            c.category,
            c.priority,
            c.status,
            c.created_at.strftime('%d-%m-%Y') if c.created_at else 'N/A',
            c.resolved_date.strftime('%d-%m-%Y') if c.resolved_date else 'Pending'
        ])
    
    return export_to_csv(data, headers, f'complaints_export_{datetime.now().strftime("%Y%m%d")}.csv')

def export_payments_to_csv(payments):
    """Export payments to CSV"""
    headers = ['Payment ID', 'Student', 'Amount', 'Type', 'Mode', 'Status', 'Payment Date', 'Verified Date']
    data = []
    
    for p in payments:
        data.append([
            p.paymentid,
            p.student.name,
            f'₹{p.amount}',
            p.payment_type,
            p.payment_mode,
            p.status,
            p.payment_date.strftime('%d-%m-%Y') if p.payment_date else 'N/A',
            p.verification_date.strftime('%d-%m-%Y') if p.verification_date else 'Pending'
        ])
    
    return export_to_csv(data, headers, f'payments_export_{datetime.now().strftime("%Y%m%d")}.csv')


def export_table_to_pdf(title, headers, data, filename):
    """Generic PDF export for tables"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=landscape(A4))
    elements = []
    styles = getSampleStyleSheet()
    
    # Title
    title_para = Paragraph(f"<b>{title}</b>", styles['Title'])
    elements.append(title_para)
    elements.append(Spacer(1, 0.3*inch))
    
    # Add generation date
    date_para = Paragraph(f"Generated on: {datetime.now().strftime('%d-%m-%Y %H:%M')}", styles['Normal'])
    elements.append(date_para)
    elements.append(Spacer(1, 0.2*inch))
    
    # Create table
    table_data = [headers] + data
    table = Table(table_data)
    
    # Style table
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 10),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.lightgrey]),
    ]))
    
    elements.append(table)
    doc.build(elements)
    
    buffer.seek(0)
    response = make_response(buffer.getvalue())
    response.headers["Content-Disposition"] = f"attachment; filename={filename}"
    response.headers["Content-type"] = "application/pdf"
    return response
