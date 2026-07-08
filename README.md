<div align="center">

# 🚀 HRFlux — AI-Powered Multi-Agent HR Assistant

### Automating 80%+ of routine HR operations through specialized AI agents, RAG-based policy retrieval, and intelligent workflow orchestration.

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.100+-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![Next.js](https://img.shields.io/badge/Next.js-15-000000?style=for-the-badge&logo=next.js&logoColor=white)](https://nextjs.org)
[![React](https://img.shields.io/badge/React-19-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
[![LangGraph](https://img.shields.io/badge/LangGraph-Multi--Agent-FF6F00?style=for-the-badge)](https://langchain-ai.github.io/langgraph/)
[![ChromaDB](https://img.shields.io/badge/ChromaDB-Vector_DB-FF6B6B?style=for-the-badge)](https://www.trychroma.com)
[![TypeScript](https://img.shields.io/badge/TypeScript-5-3178C6?style=for-the-badge&logo=typescript&logoColor=white)](https://typescriptlang.org)

---

**Final Year Project** · Department of Computer Science  
National University of Computer & Emerging Sciences (FAST-NUCES), Islamabad  
Session 2022–2026 · Supervised by **Dr. Adil Majeed**

</div>

---

##  Table of Contents

- [Problem & Motivation](#-problem--motivation)
- [Key Features](#-key-features)
- [System Architecture](#-system-architecture)
- [Multi-Agent Design](#-multi-agent-design)
- [Tech Stack](#-tech-stack)
- [Project Structure](#-project-structure)
- [Getting Started](#-getting-started)
- [API Endpoints](#-api-endpoints)
- [Security & Guardrails](#-security--guardrails)
- [Testing](#-testing)
- [Team](#-team)
- [License](#-license)

---

##  Problem & Motivation

HR departments spend up to **60% of their time** on repetitive queries — leave balances, NOC requests, policy clarifications — while employees struggle with buried information, inconsistent answers, and slow approvals. Existing FAQ tools provide generic, out-of-context responses that end up pushing queries back to HR.

**HRFlux** solves this by deploying **specialized AI agents**, each mastering a specific HR domain, coordinated through an intelligent supervisor workflow. Instead of one generic chatbot, HRFlux provides domain-accurate, policy-grounded, and context-aware assistance — reducing HR workload and improving employee experience.

---

##  Key Features

<table>
<tr>
<td width="50%">

### Multi-Agent System
- **LeaveBot** — Leave balance queries, applications, and status tracking
- **PolicyBot** — RAG-powered policy Q&A grounded in actual company documents
- **DocuBot** — Automated generation of NOCs, experience letters, and approval memos
- **EscalationBot** — Intelligent routing of sensitive/unresolvable queries to HR staff
- **AdminBot** — Natural language admin operations for HR managers

</td>
<td width="50%">

### RAG-Based Knowledge Engine
- Semantic search over HR policy documents using **ChromaDB** vector store
- Hybrid retrieval combining **dense embeddings** + **keyword search**
- Multi-format document ingestion (PDF, DOCX, PPTX, EPUB, HTML)
- **BLIP image captioning** + **Tesseract OCR** for visual content in documents
- Token-aware chunking for optimal context windows

</td>
</tr>
<tr>
<td width="50%">

### Workflow Automation
- End-to-end leave request lifecycle (apply → validate → approve/reject)
- Automatic leave balance deduction and restoration
- SLA monitoring with **proactive notifications** (APScheduler)
- Configurable escalation pipelines with full conversation history handover
- Meeting scheduling and task management

</td>
<td width="50%">

### Enterprise Security
- **JWT-based authentication** with session management
- **Role-based access control** (Employee / Admin / HR Manager)
- Input sanitization (XSS, SQL injection prevention)
- **PII detection** and content filtering
- Rate limiting and brute-force protection
- Full **audit trail** logging for compliance

</td>
</tr>
<tr>
<td width="50%">

### Dual-Portal Frontend
- **Employee Dashboard** — AI chat, leave calendar, profile, task management
- **Admin Dashboard** — Escalation management, query logs, document management, analytics, and system settings
- Real-time smart notifications
- Responsive design with **Ant Design** + **Framer Motion** animations

</td>
<td width="50%">

### Multimodal Intelligence
- **Image analysis** via CLIP embeddings and BLIP captioning
- **Audio transcription** with Whisper/SpeechRecognition
- **Video frame extraction** and analysis (OpenCV + MoviePy)
- **OCR text extraction** from scanned documents
- Multimodal RAG pipeline for cross-modal retrieval

</td>
</tr>
</table>

---

## System Architecture

```
┌──────────────────────────────────────────────────────────────────┐
│                        FRONTEND (Next.js 15)                     │
│  ┌──────────────┐  ┌──────────────┐  ┌────────────────────────┐ │
│  │ Employee Chat │  │  Leave Cal   │  │    Admin Dashboard     │ │
│  │   Dashboard   │  │  & Profile   │  │ (Logs/Escalations/Docs)│ │
│  └──────┬───────┘  └──────┬───────┘  └───────────┬────────────┘ │
└─────────┼─────────────────┼──────────────────────┼──────────────┘
          │                 │                      │
          ▼                 ▼                      ▼
┌──────────────────────────────────────────────────────────────────┐
│                    FASTAPI BACKEND (REST API)                    │
│  ┌────────────┐  ┌──────────────┐  ┌──────────────────────────┐ │
│  │ Auth Manager│  │  Guardrails  │  │   Notification Engine   │ │
│  │ + Security  │  │ + Filtering  │  │   (SLA / Reminders)     │ │
│  └─────┬──────┘  └──────┬───────┘  └────────────┬─────────────┘ │
│        │                │                       │               │
│  ┌─────▼────────────────▼───────────────────────▼─────────────┐ │
│  │              SUPERVISOR WORKFLOW (LangGraph)                │ │
│  │  ┌──────────┐ ┌──────────┐ ┌────────┐ ┌──────────────────┐│ │
│  │  │ LeaveBot │ │PolicyBot │ │DocuBot │ │  EscalationBot   ││ │
│  │  └────┬─────┘ └────┬─────┘ └───┬────┘ └────────┬─────────┘│ │
│  └───────┼─────────────┼───────────┼───────────────┼──────────┘ │
│          │             │           │               │            │
│  ┌───────▼─────────────▼───────────▼───────────────▼──────────┐ │
│  │                    CORE SERVICES                            │ │
│  │  ┌──────────┐  ┌───────────┐  ┌────────────┐  ┌─────────┐ │ │
│  │  │ RAG      │  │ Workflow  │  │ Multimodal │  │  DB     │ │ │
│  │  │ Pipeline │  │ Engine    │  │ Processor  │  │ Schema  │ │ │
│  │  └────┬─────┘  └───────────┘  └────────────┘  └────┬────┘ │ │
│  └───────┼─────────────────────────────────────────────┼──────┘ │
└──────────┼─────────────────────────────────────────────┼────────┘
           ▼                                             ▼
   ┌──────────────┐                             ┌──────────────┐
   │   ChromaDB   │                             │   SQLite DB  │
   │ Vector Store │                             │  (queries.db)│
   └──────────────┘                             └──────────────┘
```

---

## Multi-Agent Design

HRFlux uses a **Supervisor-Worker architecture** powered by **LangGraph**, where a central supervisor classifies incoming queries via an LLM-based intent router and delegates them to the appropriate specialist agent:

| Agent | Role | Key Capabilities |
|-------|------|-------------------|
| **🏖️ LeaveBot** | Leave Management | Balance checks, leave applications, status tracking, balance validation |
| **📋 PolicyBot** | Policy Expert | RAG-powered Q&A, semantic document search, policy clarification |
| **📄 DocuBot** | Document Generator | NOC letters, experience certificates, approval memos (PDF generation) |
| **🚨 EscalationBot** | Escalation Handler | Sensitive query routing, HR handover with full context, grievance logging |
| **⚙️ AdminBot** | Admin Operations | Natural language admin commands, employee management, system configuration |

Each agent inherits from `BaseHRAgent`, ensuring standardized response formatting, identity-preserving audit logging, and automatic employee context hydration. Off-topic queries (non-HR) are intercepted at the router level and rejected with a polite explanation.

---

##  Tech Stack

| Layer | Technology |
|-------|-----------|
| **Frontend** | Next.js 15, React 19, TypeScript 5, Ant Design 6, Framer Motion, TailwindCSS 4 |
| **Backend API** | FastAPI, Uvicorn, Pydantic |
| **AI/ML** | LangGraph, LangChain, Groq (Llama 3.3 70B), Google Generative AI (Gemini) |
| **Embeddings** | Sentence-Transformers, CLIP (OpenAI), BLIP (Salesforce) |
| **Vector Database** | ChromaDB (persistent storage) |
| **Relational Database** | SQLite (employee records, leave requests, notifications, audit logs) |
| **Document Processing** | PyMuPDF, PyPDF2, PDFPlumber, Tesseract OCR, python-docx, python-pptx |
| **PDF Generation** | WeasyPrint, PDFKit, Jinja2 templates |
| **Audio/Video** | OpenAI Whisper, SpeechRecognition, MoviePy, OpenCV, Librosa |
| **Security** | bcrypt, JWT tokens, rate limiting, PII detection, content filtering |
| **Scheduling** | APScheduler (SLA monitoring, proactive notifications) |
| **Testing** | pytest, pytest-mock |

---

##  Project Structure

```
hrflux_new/
├── backend/                        # Python backend (FastAPI)
│   ├── main.py                     # FastAPI app entry point & REST API routes
│   ├── agents/                     # Multi-agent architecture
│   │   ├── base_agent.py           # Abstract base class for all agents
│   │   ├── agent_router.py         # LLM-based intent classifier & query router
│   │   ├── agent_factory.py        # Agent instantiation factory
│   │   ├── leave_bot.py            # LeaveBot specialist agent
│   │   ├── policy_bot.py           # PolicyBot specialist agent
│   │   ├── docu_bot.py             # DocuBot specialist agent
│   │   ├── escalation_bot.py       # EscalationBot specialist agent
│   │   ├── session_memory.py       # Contextual session memory
│   │   └── prompts.py              # Agent system prompts
│   ├── multi_agent.py              # LangGraph supervisor workflow orchestration
│   ├── supervisor_workflow.py      # Supervisor coordination layer
│   ├── rag.py                      # RAG pipeline (ingest + retrieve)
│   ├── multimodal_rag_processor.py # Multi-modal RAG (image/audio/video)
│   ├── multimodal_processor.py     # Media processing utilities
│   ├── workflow_engine.py          # Leave approval workflows & escalation engine
│   ├── db_schema_v2.py             # Database schema & employee CRUD operations
│   ├── db.py                       # Database utilities (auth, logs, chat history)
│   ├── auth_manager.py             # Authentication with rate limiting & sessions
│   ├── security.py                 # Security middleware
│   ├── security_config.py          # Comprehensive security configuration
│   ├── guardrails.py               # Content filtering, PII detection, input validation
│   ├── notifications.py            # Notification manager (SLA alerts, reminders)
│   ├── proactive_notif.py          # Proactive notification engine
│   ├── embedder.py                 # Sentence-Transformer embedding model
│   ├── vector_store.py             # ChromaDB vector store operations
│   ├── chunking.py                 # Token-aware document chunking
│   ├── config.py                   # LLM configuration & API key management
│   ├── gemini_llm.py               # Google Gemini LLM integration
│   ├── groq_client.py              # Groq API client (Llama 3.3 70B)
│   ├── templates/                  # HTML templates (login, dashboard, documents)
│   └── tests/                      # 28 test files covering all modules
│       ├── test_module1_database.py
│       ├── test_module2_knowledge_base.py
│       ├── test_module3_hr_agent_layer.py
│       ├── test_guardrails.py
│       └── ...
│
├── frontend/                       # Next.js 15 frontend (TypeScript)
│   ├── src/
│   │   ├── app/
│   │   │   ├── login/              # Authentication page
│   │   │   ├── dashboard/          # Employee portal
│   │   │   │   ├── page.tsx        # AI Chat interface
│   │   │   │   ├── calendar/       # Leave calendar view
│   │   │   │   └── profile/        # Employee profile management
│   │   │   └── admin/              # Admin portal
│   │   │       ├── page.tsx        # Admin dashboard & analytics
│   │   │       ├── chat/           # Admin AI chat (AdminBot)
│   │   │       ├── escalations/    # Escalation management
│   │   │       ├── documents/      # Document management
│   │   │       ├── logs/           # Query audit logs
│   │   │       ├── multimodal/     # Multimodal document upload & analysis
│   │   │       └── settings/       # System configuration
│   │   ├── components/             # Reusable UI components
│   │   │   ├── Sidebar.tsx         # Employee navigation sidebar
│   │   │   ├── AdminSidebar.tsx    # Admin navigation sidebar
│   │   │   └── SmartNotification.tsx # Real-time notification system
│   │   └── hooks/                  # Custom React hooks
│   └── package.json
│
├── start.ps1                       # One-command startup script (backend + frontend)
├── requirements.txt                # Python dependencies
└── policy_docs/                    # HR policy documents for RAG ingestion
```

---

##  Getting Started

### Prerequisites

- **Python 3.10+**
- **Node.js 18+** & npm
- **Tesseract OCR** — `choco install tesseract` (Windows) or `brew install tesseract` (macOS)
- **wkhtmltopdf** — Required for PDF generation ([download](https://wkhtmltopdf.org/downloads.html))

### Quick Start (One Command)

```powershell
# Clone the repository
git clone https://github.com/ffatimaobaid/hrflux_new.git
cd hrflux_new

# Run the startup script — handles venv, dependencies, DB seeding, and launches both servers
.\start.ps1
```

The script will:
1. Create a Python virtual environment (if not exists)
2. Install all Python dependencies from `requirements.txt`
3. Initialize and seed the database
4. Launch the **backend** at `http://localhost:8000`
5. Launch the **frontend** at `http://localhost:3000`

### Manual Setup

```bash
# Backend
python -m venv venv
.\venv\Scripts\activate          # Windows
pip install -r requirements.txt
python backend/main.py           # Starts FastAPI on port 8000

# Frontend (in a separate terminal)
cd frontend
npm install
npm run dev                      # Starts Next.js on port 3000
```

### Environment Configuration

Create a `backend/config.py` file (see `backend/config.py.example`):

```python
GROQ_API_KEY = "your-groq-api-key"
GEMINI_API_KEY = "your-google-gemini-api-key"
```

---

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| `POST` | `/login` | User authentication |
| `POST` | `/signup` | New user registration |
| `POST` | `/chat` | Send message to AI agent (auto-routed) |
| `GET` | `/employees` | List all employees |
| `GET` | `/employees/{id}` | Get employee details |
| `POST` | `/employees` | Add new employee |
| `GET` | `/leave/balance/{id}` | Check leave balance |
| `POST` | `/leave/apply` | Submit leave request |
| `PUT` | `/leave/approve/{id}` | Approve/reject leave |
| `GET` | `/leave/history/{id}` | Leave request history |
| `POST` | `/upload` | Upload document for RAG ingestion |
| `POST` | `/upload-multimodal` | Upload multimodal document (image/audio/video) |
| `GET` | `/logs` | Query audit logs |
| `GET` | `/notifications/{user}` | Get user notifications |
| `GET` | `/escalations` | List escalated queries |

> Full interactive API documentation available at `http://localhost:8000/docs` (Swagger UI)

---

## Security & Guardrails

HRFlux implements **defense-in-depth** security:

- **Authentication** — bcrypt password hashing, JWT session tokens, configurable session timeouts
- **Rate Limiting** — Max login attempts with automatic lockout periods
- **Input Validation** — SQL injection prevention, XSS sanitization, input length enforcement
- **Content Filtering** — Profanity detection, inappropriate content blocking
- **PII Detection** — Automated detection of phone numbers, SSNs, credit cards, emails in chat
- **Off-Topic Rejection** — LLM-powered intent classifier blocks non-HR queries at the router level
- **Audit Logging** — Every agent interaction is logged with timestamps for compliance
- **Role-Based Access** — Separate Employee and Admin portals with distinct permissions

---

## Testing

The project includes **28 test files** covering all four modules:

```bash
# Run all tests
cd backend
python -m pytest tests/ -v

# Run specific module tests
python -m pytest tests/test_module1_database.py -v          # Database & schema
python -m pytest tests/test_module2_knowledge_base.py -v    # RAG & vector store
python -m pytest tests/test_module3_hr_agent_layer.py -v    # Agent routing & responses
python -m pytest tests/test_guardrails.py -v                # Security & content filtering
```

---

## Team

| Name | Registration | Key Contributions |
|------|-------------|-------------------|
| **Fatima Obaid** | 22I-0475 | Database design, policy document upload, EscalationBot, employee chatbot |
| **Hadia Mazhar** | 22I-0487 | HR policy integration, policy search & answering, DocuBot, admin dashboard |
| **Shayane Zainab** | 22I-1049 | Data preprocessing, knowledge base embedding & retrieval, LeaveBot, PolicyBot |

---

## License

This project was developed as a Final Year Project (FYP) at FAST-NUCES, Islamabad. All rights reserved.

---

<div align="center">

**Built with ❤️ at FAST-NUCES Islamabad**

*If you found this project interesting, feel free to ⭐ the repository!*

</div>
