"""
Enhanced Document Generation System with PDF Download
Features smart personalization, professional templates, and direct PDF download.
"""

import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from config import get_current_api_key

logger = logging.getLogger(__name__)

# Professional document templates
DOCUMENT_TEMPLATES = {
    "NOC for Visa": {
        "title": "No Objection Certificate (NOC) for Visa Application",
        "sections": [
            {
                "title": "To",
                "content": "The Consular General, Embassy of [Country]"
            },
            {
                "title": "From",
                "content": "HRFlux HR Department\\n[Company Address]\\n[City], [State], [Zip Code]\\n[Email]"
            },
            {
                "title": "Date",
                "content": datetime.now().strftime("%B %d, %Y")
            },
            {
                "title": "Subject",
                "content": "No Objection Certificate (NOC) for Visa Application"
            },
            {
                "title": "Body",
                "content": """
This is to certify that [Employee Name], bearing Employee ID [Employee ID], has been employed with [Company Name] since [Joining Date] in the position of [Designation].

We have no objection to the issuance of a visa to [Employee Name] for the purpose of [Visa Purpose]. The employee is required to travel to [Destination Country] from [Travel Start Date] to [Travel End Date] for business purposes.

We confirm that [Employee Name] will continue to receive their regular salary and benefits during this period and will resume duties upon return.

Should you require any additional information, please do not hesitate to contact our HR department at [HR Contact].

This certificate is valid for the entire duration of the travel period.

Sincerely,

HR Manager
[Company Name]
HR Department
                """
            }
        ]
    },
    "Salary Certificate": {
        "title": "Salary Certificate",
        "sections": [
            {
                "title": "Certificate Details",
                "content": """
This is to certify that [Employee Name], Employee ID: [Employee ID], is employed with [Company Name] in the position of [Designation].

Employment Period: From [Start Date] to [End Date]
Current Monthly Salary: [Monthly Salary]
Annual Salary: [Annual Salary]
Payment Method: [Payment Method]

This certificate is issued for the purpose of [Purpose] as requested by [Employee Name].

This certificate is valid for the specified employment period only.

Issued on: [Current Date]
                """
            }
        ]
    },
    "Experience Letter": {
        "title": "Work Experience Certificate",
        "sections": [
            {
                "title": "Employee Information",
                "content": """
Employee Name: [Employee Name]
Employee ID: [Employee ID]
Designation: [Designation]
Department: [Department]
Employment Period: [Start Date] to Present
                """
            },
            {
                "title": "Work Experience Summary",
                "content": """
[Employee Name] has been employed with [Company Name] since [Joining Date]. During this period, they have demonstrated excellent performance and dedication in their role as [Designation].

Key Responsibilities:
[List of key responsibilities based on designation]

Skills and Achievements:
[Employee's key skills and notable achievements during employment]

[Employee Name] has been a valuable member of our team and has contributed significantly to our organization's success.

This certificate is issued to support [Employee Name]'s professional endeavors and confirms their employment history with [Company Name].

Issued on: [Current Date]
                """
            }
        ]
    }
}

def get_employee_data(username: str) -> Dict[str, str]:
    """Fetch employee data from database or session state."""
    try:
        # Import database functions
        from db_schema_v2 import get_employee
        
        # Get real employee data
        employee = get_employee(username)
        
        if employee:
            return {
                "Employee Name": employee.get('full_name', 'Unknown'),
                "Employee ID": employee.get('employee_id', 'Unknown'), 
                "Designation": employee.get('designation', 'Unknown'),
                "Department": employee.get('department', 'Unknown'),
                "Company Name": "HRFlux Technologies",
                "Joining Date": employee.get('joining_date', 'Unknown'),
                "Start Date": employee.get('joining_date', 'Unknown'),
                "End Date": datetime.now().strftime("%B %d, %Y"),
                "Monthly Salary": f"${employee.get('salary', '0')}",
                "Annual Salary": f"${int(employee.get('salary', '0')) * 12}",
                "Payment Method": "Bank Transfer",
                "HR Contact": "hr@hrflux.com",
                "HR Email": "hr@hrflux.com",
                "Company Address": "123 Business Ave, Suite 100, Tech City, TC 12345",
                "City": "Tech City",
                "State": "Technology State",
                "Zip Code": "12345",
                "Visa Purpose": "Business Conference Attendance",
                "Destination Country": "United States",
                "Travel Start Date": datetime.now().strftime("%B %d, %Y"),
                "Travel End Date": (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y"),
                "Country": "United States"
            }
        else:
            # Fallback to demo data if employee not found
            return {
                "Employee Name": username.replace('.', ' ').title(),
                "Employee ID": f"EMP{username.upper().replace('.', '')}", 
                "Designation": "Employee",
                "Department": "General",
                "Company Name": "HRFlux Technologies",
                "Joining Date": "January 15, 2022",
                "Start Date": "January 15, 2022",
                "End Date": datetime.now().strftime("%B %d, %Y"),
                "Monthly Salary": "$5,000",
                "Annual Salary": "$60,000",
                "Payment Method": "Bank Transfer",
                "HR Contact": "hr@hrflux.com",
                "HR Email": "hr@hrflux.com",
                "Company Address": "123 Business Ave, Suite 100, Tech City, TC 12345",
                "City": "Tech City",
                "State": "Technology State",
                "Zip Code": "12345",
                "Visa Purpose": "Business Conference Attendance",
                "Destination Country": "United States",
                "Travel Start Date": datetime.now().strftime("%B %d, %Y"),
                "Travel End Date": (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y"),
                "Country": "United States"
            }
            
    except Exception as e:
        logger.error(f"Error fetching employee data: {e}")
        # Return demo data as fallback
        return {
            "Employee Name": username.replace('.', ' ').title(),
            "Employee ID": f"EMP{username.upper().replace('.', '')}", 
            "Designation": "Employee",
            "Department": "General",
            "Company Name": "HRFlux Technologies",
            "Joining Date": "January 15, 2022",
            "Start Date": "January 15, 2022",
            "End Date": datetime.now().strftime("%B %d, %Y"),
            "Monthly Salary": "$5,000",
            "Annual Salary": "$60,000",
            "Payment Method": "Bank Transfer",
            "HR Contact": "hr@hrflux.com",
            "HR Email": "hr@hrflux.com",
            "Company Address": "123 Business Ave, Suite 100, Tech City, TC 12345",
            "City": "Tech City",
            "State": "Technology State",
            "Zip Code": "12345",
            "Visa Purpose": "Business Conference Attendance",
            "Destination Country": "United States",
            "Travel Start Date": datetime.now().strftime("%B %d, %Y"),
            "Travel End Date": (datetime.now() + timedelta(days=10)).strftime("%B %d, %Y"),
            "Country": "United States"
        }

def personalize_template(template_data: Dict, employee_data: Dict[str, str]) -> str:
    """Replace placeholders with actual employee data."""
    template_text = ""
    
    for section in template_data.get("sections", []):
        section_content = section.get("content", "")
        # Replace all placeholders with employee data
        for key, value in employee_data.items():
            placeholder = f"[{key}]"
            if placeholder in section_content:
                section_content = section_content.replace(placeholder, value)
        
        template_text += f"\n\n{section.get('title', '')}\n{'='*40}\n{section_content}\n"
    
    return template_text

def generate_text_document(template_data: Dict, employee_data: Dict[str, str]) -> str:
    """Generate clean text document for PDF conversion."""
    document_title = template_data.get('title', 'HR Document')
    
    # Create clean text content
    content_lines = []
    
    # Header
    content_lines.append("=" * 60)
    content_lines.append("HRFlux Technologies")
    content_lines.append("Official HR Document")
    content_lines.append("=" * 60)
    content_lines.append("")
    
    # Document title
    content_lines.append(f"{document_title}")
    content_lines.append("=" * len(document_title))
    content_lines.append("")
    
    # Date
    content_lines.append(f"Date: {datetime.now().strftime('%B %d, %Y')}")
    content_lines.append("")
    
    # Process template sections
    for section in template_data.get("sections", []):
        section_title = section.get("title", "")
        section_content = section.get("content", "")
        
        # Replace placeholders with employee data
        for key, value in employee_data.items():
            placeholder = f"[{key}]"
            if placeholder in section_content:
                section_content = section_content.replace(placeholder, value)
        
        # Add section
        if section_title:
            content_lines.append(section_title)
            content_lines.append("-" * len(section_title))
        
        # Add content with proper formatting
        for line in section_content.split('\\n'):
            line = line.strip()
            if line:
                content_lines.append(line)
        
        content_lines.append("")
    
    # Footer
    content_lines.append("-" * 60)
    content_lines.append("Generated by HRFlux HR System")
    content_lines.append(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}")
    content_lines.append("This is an official document - CONFIDENTIAL")
    content_lines.append("-" * 60)
    
    return '\\n'.join(content_lines)

def generate_html_document(template_data: Dict, personalized_content: str) -> str:
    """Generate professional HTML document with styling."""
    html_template = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{template_data['title']}</title>
    <style>
        body {{
            font-family: 'Arial', sans-serif;
            line-height: 1.6;
            color: #333;
            max-width: 800px;
            margin: 0 auto;
            padding: 40px 20px;
            background: #f9fafb;
        }}
        .header {{
            text-align: center;
            border-bottom: 2px solid #1f2937;
            padding-bottom: 20px;
            margin-bottom: 30px;
        }}
        .logo {{
            font-size: 24px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 10px;
        }}
        .company-name {{
            font-size: 18px;
            color: #6b7280;
            margin-bottom: 5px;
        }}
        .document-title {{
            font-size: 20px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 20px;
            text-align: center;
        }}
        .section {{
            margin-bottom: 25px;
        }}
        .section-title {{
            font-size: 16px;
            font-weight: bold;
            color: #1f2937;
            margin-bottom: 10px;
            border-bottom: 1px solid #e5e7eb;
            padding-bottom: 5px;
        }}
        .section-content {{
            white-space: pre-wrap;
            font-size: 14px;
            line-height: 1.6;
        }}
        .footer {{
            text-align: center;
            margin-top: 40px;
            padding-top: 20px;
            border-top: 1px solid #e5e7eb;
            font-size: 12px;
            color: #6b7280;
        }}
        .watermark {{
            position: fixed;
            top: 50%;
            left: 50%;
            transform: translate(-50%, -50%) rotate(-45deg);
            font-size: 72px;
            color: rgba(31, 41, 55, 0.1);
            font-weight: bold;
            pointer-events: none;
            z-index: -1;
        }}
        .confidential {{
            position: fixed;
            bottom: 20px;
            right: 20px;
            background: #dc2626;
            color: white;
            padding: 8px 16px;
            border-radius: 6px;
            font-size: 12px;
            font-weight: bold;
        }}
    </style>
</head>
<body>
    <div class="header">
        <div class="logo">HRFlux</div>
        <div class="company-name">Technologies</div>
        <div class="document-title">{template_data['title']}</div>
    </div>
    
    <div class="section">
        <pre style="font-family: 'Courier New', monospace;">{personalized_content}</pre>
    </div>
    
    <div class="footer">
        <p>Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}</p>
        <p><em>This is an official document generated by HRFlux HR System</em></p>
    </div>
    
    <div class="watermark">HRFlux</div>
    <div class="confidential">CONFIDENTIAL</div>
</body>
</html>
    """
    
    return html_template

def convert_text_to_pdf(text_content: str, output_filename: str) -> str:
    """Convert clean text to PDF with proper formatting."""
    try:
        from reportlab.lib.pagesizes import letter
        from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
        from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
        from reportlab.lib.units import inch
        from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_JUSTIFY
        from reportlab.lib.colors import black, darkblue, grey
        from io import BytesIO
        import re
        
        # Create PDF with professional formatting
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter, 
                               leftMargin=72, rightMargin=72,
                               topMargin=72, bottomMargin=36)
        styles = getSampleStyleSheet()
        story = []
        
        # Create custom styles
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=20,
            spaceAfter=20,
            spaceBefore=20,
            alignment=TA_CENTER,
            textColor=darkblue,
            fontName='Helvetica-Bold'
        )
        
        header_style = ParagraphStyle(
            'CustomHeader',
            parent=styles['Heading2'],
            fontSize=16,
            spaceAfter=15,
            spaceBefore=15,
            alignment=TA_CENTER,
            textColor=black,
            fontName='Helvetica-Bold'
        )
        
        heading_style = ParagraphStyle(
            'CustomHeading',
            parent=styles['Heading2'],
            fontSize=14,
            spaceAfter=10,
            spaceBefore=15,
            alignment=TA_LEFT,
            textColor=black,
            fontName='Helvetica-Bold'
        )
        
        normal_style = ParagraphStyle(
            'CustomNormal',
            parent=styles['Normal'],
            fontSize=11,
            spaceAfter=8,
            leading=14,
            alignment=TA_JUSTIFY,
            textColor=black,
            fontName='Helvetica'
        )
        
        footer_style = ParagraphStyle(
            'Footer',
            parent=styles['Normal'],
            fontSize=9,
            spaceAfter=3,
            alignment=TA_CENTER,
            textColor=grey,
            fontName='Helvetica'
        )
        
        # Process text content line by line
        lines = text_content.split('\\n')
        current_section = []
        
        for line in lines:
            line = line.strip()
            
            if not line:
                # Empty line - add spacer
                if current_section:
                    # Process accumulated section
                    if len(current_section) == 1:
                        # Single line - likely a heading
                        if current_section[0].startswith('='):
                            # Header line with equals
                            header_text = current_section[0].replace('=', '').strip()
                            if header_text:
                                story.append(Paragraph(header_text, header_style))
                        else:
                            story.append(Paragraph(current_section[0], heading_style))
                    else:
                        # Multiple lines - content
                        for content_line in current_section:
                            if content_line and not content_line.startswith('-'):
                                # Clean up the line for PDF
                                clean_line = re.sub(r'\s+', ' ', content_line)
                                story.append(Paragraph(clean_line, normal_style))
                    
                    current_section = []
                    story.append(Spacer(1, 12))
                continue
            
            # Check for section separators
            if line.startswith('='):
                # Header/footer separator
                if current_section:
                    # Process previous section first
                    for content_line in current_section:
                        if content_line and not content_line.startswith('-'):
                            clean_line = re.sub(r'\s+', ' ', content_line)
                            story.append(Paragraph(clean_line, normal_style))
                    current_section = []
                
                # Add the header
                header_text = line.replace('=', '').strip()
                if header_text:
                    if "HRFlux Technologies" in header_text:
                        story.append(Paragraph("HRFlux Technologies", title_style))
                        story.append(Spacer(1, 6))
                        story.append(Paragraph("Official HR Document", header_style))
                    elif "Generated by" in header_text:
                        story.append(Spacer(1, 20))
                        story.append(Paragraph(header_text.replace('=', '').strip(), footer_style))
                    else:
                        story.append(Paragraph(header_text, header_style))
                
                story.append(Spacer(1, 12))
            elif line.startswith('-'):
                # Sub-header
                if current_section:
                    # Process previous section
                    for content_line in current_section:
                        if content_line and not content_line.startswith('-'):
                            clean_line = re.sub(r'\s+', ' ', content_line)
                            story.append(Paragraph(clean_line, normal_style))
                    current_section = []
                
                subheader_text = line.replace('-', '').strip()
                if subheader_text:
                    story.append(Paragraph(subheader_text, heading_style))
                    story.append(Spacer(1, 6))
            else:
                # Regular content line
                current_section.append(line)
        
        # Process any remaining content
        if current_section:
            for content_line in current_section:
                if content_line and not content_line.startswith('-'):
                    clean_line = re.sub(r'\s+', ' ', content_line)
                    story.append(Paragraph(clean_line, normal_style))
        
        # Build PDF
        doc.build(story)
        
        # Save PDF
        pdf_data = buffer.getvalue()
        buffer.close()
        
        with open(output_filename, 'wb') as f:
            f.write(pdf_data)
        
        logger.info(f"PDF generated using clean text method: {output_filename}")
        return output_filename
        
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise Exception(f"PDF generation error: {str(e)}")

def convert_to_pdf(html_content: str, output_filename: str) -> str:
    """Convert HTML to PDF and save to file."""
    try:
        # Try different PDF generation libraries
        try:
            import weasyprint
            # Method 1: WeasyPrint (recommended - best HTML rendering)
            html_doc = weasyprint.HTML(string=html_content)
            html_doc.write_pdf(output_filename)
            logger.info(f"PDF generated using WeasyPrint: {output_filename}")
            return output_filename
            
        except ImportError:
            try:
                # Method 2: pdfkit (requires wkhtmltopdf - good HTML rendering)
                import pdfkit
                options = {
                    'page-size': 'A4',
                    'margin-top': '0.75in',
                    'margin-right': '0.75in',
                    'margin-bottom': '0.75in',
                    'margin-left': '0.75in',
                    'encoding': "UTF-8",
                    'enable-local-file-access': '',
                    'no-stop-slow-scripts': '',
                }
                pdfkit.from_string(html_content, output_filename, options=options)
                logger.info(f"PDF generated using pdfkit: {output_filename}")
                return output_filename
                
            except ImportError:
                # Method 3: ReportLab with proper HTML parsing (basic but clean)
                from reportlab.lib.pagesizes import letter
                from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer
                from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
                from reportlab.lib.units import inch
                from reportlab.lib.enums import TA_CENTER, TA_LEFT
                from io import BytesIO
                import re
                
                # Create basic PDF with clean formatting
                buffer = BytesIO()
                doc = SimpleDocTemplate(buffer, pagesize=letter, 
                                       leftMargin=72, rightMargin=72,
                                       topMargin=72, bottomMargin=18)
                styles = getSampleStyleSheet()
                story = []
                
                # Create custom styles
                title_style = ParagraphStyle(
                    'CustomTitle',
                    parent=styles['Heading1'],
                    fontSize=18,
                    spaceAfter=30,
                    alignment=TA_CENTER,
                    textColor='#1f2937'
                )
                
                heading_style = ParagraphStyle(
                    'CustomHeading',
                    parent=styles['Heading2'],
                    fontSize=14,
                    spaceAfter=12,
                    spaceBefore=20,
                    textColor='#1f2937'
                )
                
                normal_style = ParagraphStyle(
                    'CustomNormal',
                    parent=styles['Normal'],
                    fontSize=11,
                    spaceAfter=6,
                    leading=14,
                    textColor='#333333'
                )
                
                # Extract content from HTML (clean parsing)
                # Remove HTML tags and extract clean text
                clean_text = re.sub(r'<[^<]+?>', '', html_content)
                clean_text = re.sub(r'&nbsp;', ' ', clean_text)
                clean_text = re.sub(r'&amp;', '&', clean_text)
                clean_text = re.sub(r'&lt;', '<', clean_text)
                clean_text = re.sub(r'&gt;', '>', clean_text)
                
                # Split into sections by "=====" (section separators)
                sections = clean_text.split('=====')
                
                for section in sections:
                    section = section.strip()
                    if not section:
                        continue
                    
                    # Extract title and content
                    lines = section.split('\\n')
                    if lines:
                        # First line is usually the title
                        title = lines[0].strip()
                        if title and len(title) < 100:  # Reasonable title length
                            story.append(Paragraph(title, heading_style))
                        
                        # Rest is content
                        content_lines = lines[1:] if len(lines) > 1 else []
                        for line in content_lines:
                            line = line.strip()
                            if line and line != 'Body':  # Skip empty lines and "Body" marker
                                # Convert line breaks to spaces for proper paragraph formatting
                                clean_line = ' '.join(line.split())
                                if clean_line:
                                    story.append(Paragraph(clean_line, normal_style))
                                    story.append(Spacer(1, 6))
                    
                    story.append(Spacer(1, 12))
                
                # Add footer
                footer_style = ParagraphStyle(
                    'Footer',
                    parent=styles['Normal'],
                    fontSize=9,
                    spaceAfter=3,
                    alignment=TA_CENTER,
                    textColor='#6b7280'
                )
                
                story.append(Spacer(1, 20))
                story.append(Paragraph("Generated by HRFlux HR System", footer_style))
                story.append(Paragraph(f"Generated on {datetime.now().strftime('%B %d, %Y at %I:%M %p')}", footer_style))
                
                # Build PDF
                doc.build(story)
                
                # Save PDF
                pdf_data = buffer.getvalue()
                buffer.close()
                
                with open(output_filename, 'wb') as f:
                    f.write(pdf_data)
                
                logger.info(f"PDF generated using ReportLab (clean format): {output_filename}")
                return output_filename
                
    except Exception as e:
        logger.error(f"PDF generation failed: {e}")
        raise Exception(f"PDF generation error: {str(e)}")

@tool
def tool_generate_enhanced_document(document_type: str, username: str, specific_requirements: str = "") -> str:
    """
    Generate an enhanced HR document with personalization and PDF download capability.
    
    Args:
        document_type: Type of document (NOC for Visa, Salary Certificate, Experience Letter)
        username: Employee username for personalization
        specific_requirements: Any additional text to include
    
    Returns:
        JSON string with document content and download information
    """
    print(f"🔧 DEBUG: tool_generate_enhanced_document called!")
    print(f"📝 Document Type: {document_type}")
    print(f"👤 Username: {username}")
    print(f"📋 Requirements: {specific_requirements}")
    
    try:
        # Get employee data for personalization
        employee_data = get_employee_data(username)
        print(f"👤 Employee data fetched: {employee_data.get('Employee Name', 'N/A')}")
        
        # Get template
        template_data = DOCUMENT_TEMPLATES.get(document_type, {})
        if not template_data:
            print(f"❌ Template not found for: {document_type}")
            return json.dumps({"error": f"Document type '{document_type}' not supported"})
        
        print(f"✅ Template found: {template_data.get('title')}")
        
        # Personalize template using clean text method
        personalized_content = generate_text_document(template_data, employee_data)
        
        # Add specific requirements if provided
        if specific_requirements:
            personalized_content += f"\\n\\nAdditional Requirements:\\n{specific_requirements}"
        
        # Generate HTML document (for preview)
        html_content = generate_html_document(template_data, personalized_content)
        
        # Create PDF filename
        safe_username = username.replace(' ', '_').lower()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"documents/{safe_username}_{document_type.replace(' ', '_').lower()}_{timestamp}.pdf"
        
        # Ensure documents directory exists
        os.makedirs("documents", exist_ok=True)
        
        # Convert to PDF using clean text (better formatting)
        pdf_path = convert_text_to_pdf(personalized_content, pdf_filename)
        print(f"📄 PDF generated: {pdf_path}")
        
        # Generate download URL (for web interface)
        download_url = f"/download_document/{os.path.basename(pdf_path)}"
        
        result_data = {
            "status": "success",
            "document_type": document_type,
            "title": template_data['title'],
            "content": personalized_content,
            "html_content": html_content,
            "pdf_path": pdf_path,
            "download_url": download_url,
            "employee_data": employee_data,
            "generated_at": datetime.now().isoformat(),
            "message": f"✅ {document_type} generated successfully! Click below to download."
        }
        
        print(f"✅ Document generation completed successfully!")
        return json.dumps(result_data)
        
    except Exception as e:
        print(f"❌ Document generation failed: {e}")
        logger.error(f"Enhanced document generation failed: {e}")
        return json.dumps({
            "status": "error",
            "error": str(e)
        })

@tool
def tool_draft_document(document_type: str, employee_details_str: str, specific_requirements: str) -> str:
    """
    Draft an official HR document (like an NOC, Salary Certificate, or Experience Letter).
    
    Args:
        document_type: The type of document requested (e.g., "NOC for Visa", "Salary Certificate").
        employee_details_str: Relevant employee info (name, joining date, etc.) formatted as a string.
        specific_requirements: Any specific text or address the user wants included.
        
    Returns:
        The drafted document as markdown.
    """
    try:
        llm = ChatGroq(
            temperature=0.2, 
            model_name="llama-3.3-70b-versatile",
            groq_api_key=get_current_api_key()
        )
        
        prompt = f"""
You are an expert HR Administrator.
Please draft an official {document_type} based on the following details.
Do not make up fake company names, simply use HRFlux.
Use a highly professional, pristine business letter format.

Employee Details:
{employee_details_str}

Specific Requirements:
{specific_requirements}

Output ONLY the document draft text.
"""
        response = llm.invoke(prompt)
        return json.dumps({
            "status": "success",
            "draft": response.content.strip()
        })
    except Exception as e:
        logger.error(f"Failed to draft document: {e}")
        return json.dumps({"error": str(e)})

# Enhanced tool list (only use enhanced tools)
docu_bot_tools = [tool_generate_enhanced_document]
