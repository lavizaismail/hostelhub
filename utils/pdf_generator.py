from models import RoomAllocation
from reportlab.lib.pagesizes import A4
from reportlab.lib import colors
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, HRFlowable
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from flask import make_response
from io import BytesIO
from datetime import datetime

def generate_payment_receipt(payment):
    """Generate an enhanced professional PDF receipt"""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=40, 
        leftMargin=40, 
        topMargin=40, 
        bottomMargin=40
    )
    
    elements = []
    styles = getSampleStyleSheet()
    
    # ========== CUSTOM STYLES ==========
    header_style = ParagraphStyle(
        'Header',
        parent=styles['Heading1'],
        fontSize=28,
        textColor=colors.HexColor('#4F46E5'),
        spaceAfter=5,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    tagline_style = ParagraphStyle(
        'Tagline',
        parent=styles['Normal'],
        fontSize=10,
        textColor=colors.HexColor('#6B7280'),
        spaceAfter=10,
        alignment=TA_CENTER,
        fontName='Helvetica-Oblique'
    )
    
    title_style = ParagraphStyle(
        'Title',
        parent=styles['Heading2'],
        fontSize=18,
        textColor=colors.HexColor('#1F2937'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    # ========== HEADER SECTION ==========
    header = Paragraph("🏨 HOSTELHUB", header_style)
    tagline = Paragraph("Your Home Away From Home", tagline_style)
    
    elements.append(header)
    elements.append(tagline)
    elements.append(HRFlowable(width="100%", thickness=2, color=colors.HexColor('#4F46E5')))
    elements.append(Spacer(1, 0.2*inch))
    
    title = Paragraph("PAYMENT RECEIPT", title_style)
    elements.append(title)
    
    # ========== RECEIPT INFO BOX ==========
    receipt_info = [
        ['Receipt No:', f'#{payment.paymentid}', 
         'Date:', payment.verification_date.strftime('%d %B %Y') if payment.verification_date else 'N/A']
    ]
    
    receipt_table = Table(receipt_info, colWidths=[1.5*inch, 1.5*inch, 1*inch, 2*inch])
    receipt_table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), colors.HexColor('#F3F4F6')),
        ('FONTNAME', (0, 0), (0, 0), 'Helvetica-Bold'),
        ('FONTNAME', (2, 0), (2, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('TEXTCOLOR', (0, 0), (-1, -1), colors.HexColor('#374151')),
        ('PADDING', (0, 0), (-1, -1), 8),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))
    
    elements.append(receipt_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # ========== STUDENT DETAILS ==========
    # Get room allocation
    allocation = RoomAllocation.query.filter_by(
        studentid=payment.studentid,
        status='active'
    ).first()
    
    # Get course and year (safe fallback)
    course = getattr(payment.student, 'course', None) or 'N/A'
    year = getattr(payment.student, 'year', None) or 'N/A'
    
    student_data = [
        # Header
        [Paragraph('<b>STUDENT INFORMATION</b>', styles['Normal'])],
        [''],
        # Details
        ['Full Name:', payment.student.fullname],
        ['Roll Number:', payment.student.rollnumber],
        ['Course:', f'{course} - Year {year}'],
        ['Email:', payment.student.email or 'N/A'],
        ['Phone:', payment.student.phone or 'N/A'],
    ]
    
    student_table = Table(student_data, colWidths=[2*inch, 4*inch])
    student_table.setStyle(TableStyle([
        # Header row
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#4F46E5')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('PADDING', (0, 0), (-1, 0), 10),
        
        # Label column
        ('FONTNAME', (0, 2), (0, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, -1), 10),
        ('TEXTCOLOR', (0, 2), (-1, -1), colors.HexColor('#374151')),
        ('PADDING', (0, 2), (-1, -1), 8),
        ('VALIGN', (0, 2), (-1, -1), 'TOP'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#4F46E5')),
        ('BACKGROUND', (0, 2), (-1, -1), colors.HexColor('#FAFAFA')),
    ]))
    
    elements.append(student_table)
    elements.append(Spacer(1, 0.2*inch))
    
    # ========== ROOM INFO (if allocated) ==========
    if allocation:
        try:
            if hasattr(allocation, 'allocationdate') and allocation.allocationdate:
                allocation_date_str = allocation.allocationdate.strftime('%d %B %Y')
            else:
                allocation_date_str = 'N/A'
        except:
            allocation_date_str = 'N/A'
    
        room_data = [
            [Paragraph('<b>ROOM INFORMATION</b>', styles['Normal'])],
            [''],
            ['Room Number:', f"{allocation.room.block}-{allocation.room.roomnumber}"],
            ['Allocation Date:', allocation_date_str],
        ]
    
        room_table = Table(room_data, colWidths=[2*inch, 4*inch])
        room_table.setStyle(TableStyle([
        # Header
            ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#10B981')),
            ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
            ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, 0), 12),
            ('SPAN', (0, 0), (-1, 0)),
            ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
            ('PADDING', (0, 0), (-1, 0), 10),
        
        # Content
            ('FONTNAME', (0, 2), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 2), (-1, -1), 10),
            ('TEXTCOLOR', (0, 2), (-1, -1), colors.HexColor('#374151')),
            ('PADDING', (0, 2), (-1, -1), 8),
        
        # Grid
            ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
            ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#10B981')),
            ('BACKGROUND', (0, 2), (-1, -1), colors.HexColor('#F0FDF4')),
        ]))
    
        elements.append(room_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # ========== PAYMENT DETAILS ==========
    payment_data = [
        [Paragraph('<b>PAYMENT DETAILS</b>', styles['Normal'])],
        [''],
        ['Payment Month:', payment.month],
        ['Payment Date:', payment.paymentdate.strftime('%d %B %Y')],
        ['Payment Method:', (payment.paymentmethod or 'N/A').title()],
        ['Transaction ID:', payment.transactionid or 'N/A'],
        ['Verification Date:', payment.verification_date.strftime('%d %B %Y') if payment.verification_date else 'N/A'],
        ['Status:', '✓ VERIFIED'],
        [''],
        ['Total Amount Paid:', f'₹{payment.amount:,.2f}'],
    ]
    
    payment_table = Table(payment_data, colWidths=[2*inch, 4*inch])
    payment_table.setStyle(TableStyle([
        # Header
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#F59E0B')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 12),
        ('SPAN', (0, 0), (-1, 0)),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('PADDING', (0, 0), (-1, 0), 10),
        
        # Labels
        ('FONTNAME', (0, 2), (0, -2), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 2), (-1, -2), 10),
        ('TEXTCOLOR', (0, 2), (-1, -2), colors.HexColor('#374151')),
        ('PADDING', (0, 2), (-1, -2), 8),
        
        # Status row - Green
        ('TEXTCOLOR', (1, 7), (1, 7), colors.HexColor('#10B981')),
        ('FONTNAME', (1, 7), (1, 7), 'Helvetica-Bold'),
        ('FONTSIZE', (1, 7), (1, 7), 11),
        
        # Total amount row - Highlighted
        ('BACKGROUND', (0, -1), (-1, -1), colors.HexColor('#10B981')),
        ('TEXTCOLOR', (0, -1), (-1, -1), colors.white),
        ('FONTNAME', (0, -1), (-1, -1), 'Helvetica-Bold'),
        ('FONTSIZE', (0, -1), (-1, -1), 14),
        ('ALIGN', (1, -1), (1, -1), 'RIGHT'),
        ('PADDING', (0, -1), (-1, -1), 10),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.HexColor('#E5E7EB')),
        ('BOX', (0, 0), (-1, -1), 2, colors.HexColor('#F59E0B')),
        ('BACKGROUND', (0, 2), (-1, -2), colors.HexColor('#FFFBEB')),
    ]))
    
    elements.append(payment_table)
    elements.append(Spacer(1, 0.4*inch))
    
    # ========== FOOTER ==========
    footer_style = ParagraphStyle(
        'Footer',
        parent=styles['Normal'],
        fontSize=8,
        textColor=colors.HexColor('#6B7280'),
        alignment=TA_CENTER,
        leading=12
    )
    
    footer_text = f"""
    <para alignment="center">
    <b>━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━</b><br/>
    <b>HostelHub Management System</b><br/>
    Thank you for your payment. This is a computer-generated receipt.<br/>
    For any queries, contact: <b>support@hostelhub.com</b> | Phone: <b>+91-1234-567890</b><br/>
    <i>Generated on {datetime.now().strftime('%d %B %Y at %I:%M %p IST')}</i>
    </para>
    """
    
    footer = Paragraph(footer_text, footer_style)
    elements.append(footer)
    
    # Build PDF
    doc.build(elements)
    buffer.seek(0)
    
    # Create response
    response = make_response(buffer.getvalue())
    response.headers['Content-Type'] = 'application/pdf'
    response.headers['Content-Disposition'] = f'attachment; filename=HostelHub_Receipt_{payment.paymentid}.pdf'
    
    return response
