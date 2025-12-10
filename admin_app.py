import streamlit as st
import pandas as pd
import plotly.express as px
import os
import shutil
import json
from datetime import datetime

# --- Internal Imports ---
from rag import ingest_document
from db import get_all_documents, delete_document_metadata, init_db, get_logs
from vector_store import delete_document_embeddings
from db_schema_v2 import create_enhanced_schema, get_all_employees
from workflow_engine import LeaveWorkflowEngine

# --- Initialization ---
st.set_page_config(page_title="HRFlux Admin Portal", layout="wide", page_icon="🏢")

# Ensure DBs are initialized
init_db()
create_enhanced_schema()

# --- Sidebar Navigation ---
st.sidebar.title("HRFlux Admin")
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/3135/3135715.png", width=100)
nav_option = st.sidebar.radio(
    "Navigation", 
    ["Dashboard", "Query Logs", "Escalations", "Document Manager", "Settings"]
)

st.sidebar.markdown("---")
st.sidebar.markdown("© 2024 HRFlux System")

# --- 1. Dashboard Module ---
if nav_option == "Dashboard":
    st.title("📊 HR Admin Dashboard")
    
    # KPIs
    st.subheader("Key Performance Indicators")
    col1, col2, col3 = st.columns(3)
    
    employees = get_all_employees()
    pending_leaves = LeaveWorkflowEngine.get_pending_requests()
    escalations = LeaveWorkflowEngine.get_all_escalations()
    pending_escalations = [e for e in escalations if e['status'] == 'pending']
    
    with col1:
        st.metric("Total Employees", len(employees))
    with col2:
        st.metric("Pending Leave Approvals", len(pending_leaves))
    with col3:
        st.metric("Active Escalations", len(pending_escalations), delta_color="inverse")
        
    st.markdown("---")
    
    # Pending Approvals Section
    st.subheader("📝 Pending Approvals")
    
    if not pending_leaves:
        st.info("No pending leave requests.")
    else:
        for req in pending_leaves:
            # req structure: (id, employee_id, leave_type, start_date, end_date, total_days, reason, status, approver_id, approved_at, comments, submitted_at, full_name, department)
            # Adjust index based on workflow_engine query
            req_id, emp_id, leave_type, start, end, days, reason, status = req[0], req[1], req[2], req[3], req[4], req[5], req[6], req[7]
            full_name = req[12] # Based on query joins
            department = req[13]
            
            with st.expander(f"{full_name} ({leave_type.upper()}) - {days} days", expanded=True):
                c1, c2 = st.columns([3, 1])
                with c1:
                    st.markdown(f"**Department:** {department}")
                    st.markdown(f"**Dates:** {start} to {end}")
                    st.markdown(f"**Reason:** {reason}")
                with c2:
                    action_col1, action_col2 = st.columns(2)
                    with action_col1:
                        if st.button("✅ Approve", key=f"app_{req_id}"):
                            res = LeaveWorkflowEngine.approve_leave_request(req_id, "ADMIN", "Approved via Admin Dashboard")
                            if res['success']:
                                st.success("Approved!")
                                st.rerun()
                            else:
                                st.error(res['message'])
                    with action_col2:
                        if st.button("❌ Reject", key=f"rej_{req_id}"):
                            res = LeaveWorkflowEngine.reject_leave_request(req_id, "ADMIN", "Rejected via Admin Dashboard")
                            if res['success']:
                                st.warning("Rejected!")
                                st.rerun()
                            else:
                                st.error(res['message'])

# --- 2. Query Logs Module ---
elif nav_option == "Query Logs":
    st.title("📜 Query Logs & Monitoring")
    
    logs = get_logs()
    
    if not logs:
        st.info("No interaction logs found.")
    else:
        # Convert to DataFrame for easier display
        df_logs = pd.DataFrame(logs, columns=['ID', 'User', 'Question', 'Answer', 'Timestamp'])
        
        # Filters
        filter_user = st.text_input("Filter by User ID/Name")
        if filter_user:
            df_logs = df_logs[df_logs['User'].str.contains(filter_user, case=False, na=False)]
            
        st.dataframe(df_logs.sort_values(by="Timestamp", ascending=False), use_container_width=True)

# --- 3. Escalations Management Module ---
elif nav_option == "Escalations":
    st.title("🚨 Escalation Management")
    
    # Check for new escalations button
    if st.button("Run Escalation Check"):
        res = LeaveWorkflowEngine.check_and_escalate_stale_requests()
        if res.get('escalated_count', 0) > 0:
            st.warning(f"Escalated {res['escalated_count']} stale requests!")
            st.rerun()
        else:
            st.success("No new stale requests found.")
    
    st.markdown("---")
    
    all_escalations = LeaveWorkflowEngine.get_all_escalations()
    
    if not all_escalations:
        st.info("No escalations found.")
    else:
        # Separate pending and resolved
        pending = [e for e in all_escalations if e['status'] == 'pending']
        resolved = [e for e in all_escalations if e['status'] == 'resolved']
        
        tab1, tab2 = st.tabs(["🔴 Pending", "🟢 Resolved"])
        
        with tab1:
            if not pending:
                st.success("No pending escalations.")
            else:
                for esc in pending:
                    with st.container(border=True):
                        col1, col2 = st.columns([3, 1])
                        with col1:
                            st.markdown(f"**ID:** {esc['id']} | **Type:** {esc['request_type']}")
                            st.markdown(f"**Employee:** {esc['employee_name']} ({esc['employee_id']})")
                            st.markdown(f"**Reason:** {esc['reason']}")
                            st.caption(f"Escalated At: {esc['escalated_at']}")
                        with col2:
                            resolve_note = st.text_input("Resolution Note", key=f"note_{esc['id']}")
                            if st.button("Resolve", key=f"res_{esc['id']}"):
                                if resolve_note:
                                    res = LeaveWorkflowEngine.resolve_escalation(esc['id'], resolve_note)
                                    if res['success']:
                                        st.success("Marked as resolved!")
                                        st.rerun()
                                else:
                                    st.error("Please add a resolution note.")
                                    
        with tab2:
            if not resolved:
                st.info("No resolved escalations.")
            else:
                # Use a dataframe for resolved history
                st.dataframe(pd.DataFrame(resolved))

# --- 4. Document Manager (Legacy) ---
elif nav_option == "Document Manager":
    st.title("📂 Knowledge Base Manager")
    
    # Upload Section
    st.subheader("Upload New Policy Documents")
    
    file = st.file_uploader(
        "Choose a file (PDF, Word, PPT, HTML, EPUB, Images, Video, Audio)",
        type=[
            "pdf", "docx", "pptx", "html", "epub",
            "jpg", "jpeg", "png", "gif", "bmp", "tiff", "webp",
            "mp4", "avi", "mov", "mkv", "wmv", "flv", "webm",
            "mp3", "wav", "m4a", "flac", "aac", "ogg",
        ]
    )
    
    if file:
        os.makedirs("policy_docs", exist_ok=True)
        file_path = os.path.join("policy_docs", file.name)

        with st.spinner("Uploading and indexing content..."):
            try:
                # Save the file locally
                with open(file_path, "wb") as f:
                    f.write(file.read())

                # Ingest the file
                chunks, avg_tokens, doc_id = ingest_document(file_path)
                if chunks is None:
                    st.error("File could not be processed. Check logs.")
                else:
                    st.success(f"Indexed {chunks} chunks. Avg tokens: {avg_tokens:.2f}")
            except Exception as e:
                st.error(f"Failed to process: {e}")
                
    st.markdown("---")
    
    # Document List
    st.subheader("Existing Documents")
    docs = get_all_documents()
    
    if not docs:
        st.info("No documents found.")
    else:
        for doc in docs:
            col1, col2, col3 = st.columns([4, 2, 1])
            with col1:
                st.markdown(f"**{doc[1]}**")
                st.caption(f"Uploaded: {doc[2][:10]}")
            with col2:
                st.markdown(f"Avg Tokens: `{doc[3]:.2f}`")
            with col3:
                if st.button("Delete", key=f"del_{doc[0]}"):
                    filename = doc[1]
                    doc_id = doc[0]

                    # Delete metadata
                    delete_document_metadata(doc_id)

                    # Delete local files
                    try:
                        os.remove(os.path.join("policy_docs", filename))
                        shutil.rmtree(f"chroma/{doc_id}", ignore_errors=True)
                    except Exception:
                        pass

                    # Delete embeddings
                    try:
                        delete_document_embeddings(str(doc_id))
                    except Exception as e:
                        st.warning(f"Failed to delete embeddings: {e}")

                    st.rerun()

# --- 5. Settings Module ---
elif nav_option == "Settings":
    st.title("⚙️ System Settings")
    
    st.subheader("AI Model Configuration")
    model_options = ["models/gemini-1.5-flash", "models/gemini-2.5-flash", "models/gemini-1.5-pro"]
    default_model = "models/gemini-1.5-flash"
    
    config_path = "config.json"
    if os.path.exists(config_path):
        with open(config_path, "r") as f:
            try:
                config = json.load(f)
                default_model = config.get("model", default_model)
            except json.JSONDecodeError:
                pass

    selected_model = st.selectbox("Choose Gemini Model", model_options, index=model_options.index(default_model))
    
    if st.button("Save Configuration"):
        with open(config_path, "w") as f:
            json.dump({"model": selected_model}, f)
        st.success(f"Model updated to: {selected_model}")

