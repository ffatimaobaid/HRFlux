# HRFlux - AI-Powered HR Chatbot System

An intelligent HR chatbot system powered by Google Gemini AI, featuring automated leave management, document processing, and an admin dashboard for HR staff.

## 🌟 Features

### Employee Interface
- **Intelligent Q&A**: Natural language queries about HR policies, procedures, and benefits
- **Leave Management**: Submit and track leave requests with automatic validation
- **Leave Balance Tracking**: Check available leave balances in real-time
- **Multimodal Support**: Process text, images, documents, audio, and video
- **Conversation History**: Maintains context across chat sessions
- **Smart Date Parsing**: Handles natural language dates (e.g., "15 dec", "next monday")

### HR Admin Interface
- **Dashboard**: Real-time KPIs and metrics
- **Leave Approvals**: Review and approve/reject leave requests
- **Query Monitoring**: Track all employee interactions
- **Escalation Management**: Automated escalation of pending requests
- **Document Management**: Upload and manage policy documents
- **System Configuration**: Configure AI models and system settings

### Workflow Engine
- **Automated Validation**: Leave balance and overlap checking
- **Approval Workflow**: Multi-level approval system
- **Escalation System**: Auto-escalate stale requests after 7 days
- **Audit Trail**: Complete history of all requests and approvals

## 🏗️ Architecture

### Core Components

```
HRFlux/
├── agent.py                 # Main chatbot agent with intent classification
├── gemini_llm.py           # Google Gemini AI integration
├── workflow_engine.py      # Leave request workflow management
├── db_schema_v2.py         # Enhanced database schema
├── rag.py                  # Retrieval-Augmented Generation
├── vector_store.py         # Vector embeddings for semantic search
├── chat_app.py             # Employee Streamlit interface
├── admin_app.py            # HR Admin Streamlit interface
├── backend_api.py          # FastAPI backend (optional)
└── multimodal_processor.py # Image, video, audio processing
```

### Technology Stack

- **AI/ML**: Google Gemini 1.5/2.5 Flash, Sentence Transformers
- **Vector Database**: ChromaDB
- **Database**: SQLite
- **Frontend**: Streamlit
- **Backend**: FastAPI (optional)
- **Document Processing**: PyPDF2, PyMuPDF, python-docx, python-pptx
- **Multimodal**: OpenCV, MoviePy, SpeechRecognition, Tesseract OCR

## 📦 Installation

### Prerequisites

- Python 3.8+
- Google Gemini API Key
- Tesseract OCR (for image text extraction)

### Setup

1. **Clone the repository**
```bash
git clone https://github.com/ffatimaobaid/HRFlux.git
cd HRFlux
```

2. **Create virtual environment**
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

3. **Install dependencies**
```bash
pip install -r requirements.txt
```

4. **Configure API Key**
Create a `config.py` file:
```python
GEMINI_API_KEY = "your-gemini-api-key-here"
SHOW_SOURCES = True
```

5. **Initialize Database**
```bash
python db_schema_v2.py
python seed_data.py
```

6. **Ingest Policy Documents**
Place your HR policy documents in the `policy_docs/` folder and run:
```bash
python chunking.py
```

## 🚀 Usage

### Employee Chat Interface

```bash
streamlit run chat_app.py
```

**Default Credentials:**
- Username: `emp001` (or any employee ID from seed data)
- Password: `password123`

**Example Queries:**
- "What is the leave policy?"
- "I want to apply for leave from 15 dec to 20 dec"
- "What is my leave balance?"
- "How do I apply for medical reimbursement?"

### HR Admin Interface

```bash
streamlit run admin_app.py
```

**Features:**
- View and approve pending leave requests
- Monitor query logs and system metrics
- Manage escalations
- Upload new policy documents
- Configure AI model settings

### API Backend (Optional)

```bash
uvicorn backend_api:app --reload
```

Access API docs at: `http://localhost:8000/docs`

## 📊 Database Schema

### Key Tables

- **employees**: Employee profiles and credentials
- **leave_balances**: Current leave balances by type
- **leave_requests**: All leave requests with status
- **leave_balance_history**: Audit trail of balance changes
- **workflow_escalations**: Escalated pending requests
- **documents**: Uploaded policy documents
- **logs**: Chat interaction history

## 🔧 Configuration

### Model Selection

Edit `config.json` to change the AI model:
```json
{
  "model": "models/gemini-1.5-flash"
}
```

Available models:
- `models/gemini-1.5-flash` (faster, cost-effective)
- `models/gemini-2.5-flash` (latest)
- `models/gemini-1.5-pro` (more capable)

### Leave Policies

Configure in `workflow_engine.py`:
- Default leave balances
- Escalation threshold (default: 7 days)
- Weekend calculation logic

## 🧪 Testing

Run the test suite:

```bash
# Run all tests
python -m pytest tests/

# Run specific test file
python -m pytest tests/test_workflow_engine.py

# Run with coverage
python -m pytest --cov=. tests/
```

## 📁 Project Structure

```
HRFlux/
├── agent.py                    # Main agent logic
├── admin_app.py                # Admin dashboard
├── backend_api.py              # FastAPI endpoints
├── chat_app.py                 # Employee chat UI
├── chunking.py                 # Document chunking
├── config.py                   # Configuration (gitignored)
├── db.py                       # Legacy database functions
├── db_schema_v2.py             # Enhanced schema
├── embedder.py                 # Text embeddings
├── gemini_client.py            # Gemini API client
├── gemini_llm.py               # LLM query functions
├── hr_knowledge_base.py        # Structured HR knowledge
├── multimodal_processor.py     # Multimodal processing
├── rag.py                      # RAG implementation
├── vector_store.py             # Vector search
├── workflow_engine.py          # Leave workflow
├── policy_docs/                # HR policy documents
├── tests/                      # Test suite
│   ├── test_agent.py
│   ├── test_workflow_engine.py
│   └── test_database.py
└── requirements.txt            # Python dependencies
```

## 🔐 Security Notes

- **API Keys**: Never commit `config.py` to version control
- **Database**: `queries.db` contains sensitive employee data - excluded from git
- **Passwords**: Use proper hashing in production (currently simplified for demo)
- **Authentication**: Implement proper session management for production use

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit your changes (`git commit -m 'Add some AmazingFeature'`)
4. Push to the branch (`git push origin feature/AmazingFeature`)
5. Open a Pull Request

## 📝 License

This project is licensed under the MIT License.

## 👥 Authors

- Shayane Zainab 
- Hadia Mazhar
- Fatima Obaid
- Supervisor: Dr. Adil Majeed

## 🙏 Acknowledgments

- Google Gemini AI for powerful language models
- Streamlit for rapid UI development
- ChromaDB for vector storage
- The open-source community

## 📧 Contact

For questions or support, please open an issue on GitHub.

---

**Note**: This is a demonstration project. For production use, implement proper security measures, authentication, and data protection.
# hrfluxdemo
