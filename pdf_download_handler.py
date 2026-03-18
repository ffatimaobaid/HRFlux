"""
PDF Download Handler for Chat App
Handles document downloads and file serving.
"""

import os
import streamlit as st
from datetime import datetime
from typing import Dict, Any

def handle_document_download(response_data: Dict[str, Any]) -> bool:
    """Handle document download in chat interface."""
    try:
        if response_data.get("status") == "success":
            # Extract document information
            document_type = response_data.get("document_type", "Document")
            title = response_data.get("title", "Generated Document")
            pdf_path = response_data.get("pdf_path", "")
            download_url = response_data.get("download_url", "")
            employee_data = response_data.get("employee_data", {})
            
            # Display success message
            st.success(f"✅ {title} generated successfully!")
            
            # Show personalized information
            if employee_data:
                with st.expander("📋 Document Details"):
                    col1, col2 = st.columns(2)
                    with col1:
                        st.write("**Employee Information:**")
                        st.write(f"• Name: {employee_data.get('Employee Name', 'N/A')}")
                        st.write(f"• ID: {employee_data.get('Employee ID', 'N/A')}")
                        st.write(f"• Designation: {employee_data.get('Designation', 'N/A')}")
                    with col2:
                        st.write("**Document Details:**")
                        st.write(f"• Type: {document_type}")
                        st.write(f"• Generated: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
                        st.write(f"• Format: PDF")
            
            # Provide download button
            if pdf_path and os.path.exists(pdf_path):
                # Read PDF file
                with open(pdf_path, 'rb') as pdf_file:
                    pdf_data = pdf_file.read()
                
                # Create download button
                filename = os.path.basename(pdf_path)
                st.download_button(
                    label=f"📥 Download {document_type}",
                    data=pdf_data,
                    file_name=filename,
                    mime="application/pdf",
                    key=f"download_{filename}_{datetime.now().timestamp()}"
                )
                
                # Show preview option
                st.info("💡 **Tip:** Save the PDF to your device for future reference. The document includes official company branding and is ready for submission.")
                
            else:
                st.error("❌ PDF file not found. Please try generating the document again.")
            
            return True
            
        elif response_data.get("status") == "error":
            st.error(f"❌ Document generation failed: {response_data.get('error', 'Unknown error')}")
            return False
            
        return False
        
    except Exception as e:
        st.error(f"❌ Error handling document download: {str(e)}")
        return False

def display_document_preview(content: str, title: str = "Document Preview"):
    """Display document content preview in chat."""
    with st.expander(f"📄 {title}"):
        st.text_area(
            "Document Content",
            value=content,
            height=300,
            disabled=True,
            key=f"preview_{title}_{datetime.now().timestamp()}"
        )

def create_download_link(file_path: str, link_text: str = "Download") -> str:
    """Create a download link for the file."""
    if os.path.exists(file_path):
        filename = os.path.basename(file_path)
        return f'<a href="/download/{filename}" download="{filename}">{link_text}</a>'
    return f'<span style="color: red;">File not found: {file_path}</span>'
