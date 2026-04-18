# 🏢 HRFlux Multi-Agent Architecture

## 1. Overview
HRFlux utilizes a **Distributed Multi-Agent Architecture** to handle complex HR operations. Instead of a single, monolithic AI model, the system is divided into specialized **Domain Agents**. Each agent is an autonomous logical unit responsible for a specific HR department.

---

## 2. Core Components

### 🏗️ BaseHRAgent (The Foundation)
Found in `base_agent.py`, this abstract base class defines the communication protocol for the entire system. 
- **Standardized Handling**: Every agent implements a `handle()` method.
- **Shared Context**: Pre-hydrates agents with employee profiles and balances.
- **Audit Trails**: Built-in centralized logging for HR transparency.

### 🏝️ LeaveBot (The Operational Specialist)
Managed in `leave_bot.py`.
- Responsible for the lifecycle of leave requests.
- Directly interfaces with the **Workflow Engine** for strict date and balance validation.
- Handles both advisory (e.g., "Do I have enough days?") and operational (e.g., "Apply for leave") intents.

### 📜 PolicyBot (The RAG Specialist)
Managed in `policy_bot.py`.
- Implements **Retrieval-Augmented Generation (RAG)**.
- Queries a **ChromaDB Vector Store** to retrieve facts from the Company Handbook and Policy PDFs.
- Ensures answers are 100% grounded in authorized text with source attribution.

### 📄 DocuBot (The Templating Specialist)
Managed in `docu_bot.py`.
- Specialized in official HR correspondence.
- Uses dynamic templating to generate NOCs, Experience Letters, and Salary Certificates.
- Integrated with internal data sources to ensure PII accuracy.

### 🚨 EscalationBot (The Triage Specialist)
Managed in `escalation_bot.py`.
- Performs **Sentiment Analysis** and issue categorization.
- Handles grievances, payroll disputes, and harassment claims.
- Generates high-priority **HR Tickets** and assigns them to human officers based on SLAs.

---

## 3. Communication Pattern: Supervisor-Specialist
The system uses a **Supervisor Orchestration Pattern** (implemented in `supervisor_workflow.py`):
1. **User Query**: Received via the FastAPI endpoint.
2. **Intent Classification**: The Supervisor identifies the user's intent.
3. **Delegation**: The Supervisor invokes the specific Specialist Agent's `handle()` method.
4. **Validation**: The Specialist returns a structured JSON envelope.
5. **Final Response**: The Supervisor synthesizes the specialist's findings into a professional response.

---

## 4. Key Advantages
- **Modularity**: New bots (e.g., PayrollBot, TrainingBot) can be added by simply extending `BaseHRAgent`.
- **Accuracy**: Independent system prompts prevent "Prompt Dilution" and ensure the bots stay in their specific lanes.
- **Scalability**: Logic for different departments is isolated, making debugging and maintenance significantly easier.
