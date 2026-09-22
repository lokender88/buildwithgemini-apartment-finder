# Apartment Finder Agent 🏙️✨

An AI-powered conversational housing assistant built with the **Google Agent Development Kit (ADK)**, **Vertex AI**, and **Agent Platform**. Apartment Finder helps renters search, evaluate, compare, and visualize rental properties with structured A2UI cards and automated move-in cost calculations.

![Apartment Finder Agent Demo](./demo.gif)

---

## 🌟 Capabilities & Architecture

Based strictly on the codebase implementation (`app/`, `frontend/`, `agents-cli-manifest.yaml`), the agent integrates the following core capabilities and Google Cloud services:

- **🔥 Google Cloud Firestore Integration**: Direct database queries against the `apartments` collection for real-time listing lookups, filtering by neighborhood, budget, bedrooms, and pet policies.
- **🖼️ Gemini Image Generation & GCS Storage**: Generates property visualizations using the `gemini-3.1-flash-lite-image` model in Vertex AI (`global` region), saving outputs as agent artifacts and hosting them on Google Cloud Storage (`gs://apartment-finder-assets-*`).
- **🧮 Agent Platform Sandbox Code Execution**: Uses `AgentEngineSandboxCodeExecutor` to safely execute Python code in isolated sandboxes to compute itemized move-in costs (first month's rent + security deposit + administrative fees).
- **📚 Vertex AI RAG Corpus Retrieval**: Grounded answers on tenant rights and leasing guidelines retrieved directly from a serverless Vertex AI RAG corpus.
- **🎨 A2UI 0.8 Rich Card Rendering**: Powered by `a2ui-agent-sdk` (version 0.8 schema and Basic Catalog) via an `after_model_callback` to format responses into interactive visual cards.
- **🧠 ADK Memory Bank**: Persists user preferences, search criteria, and move-in constraints across conversational turns.
- **🌐 Public API Integration**: Integrated `PublicApisSearchTool` to fetch public housing and community data.

---

## 🛠️ Tech Stack

- **Framework**: Google Agent Development Kit (ADK)
- **Models**: Gemini 2.5 / Gemini 3.1 Flash Lite Image
- **Database & Storage**: Google Cloud Firestore, Google Cloud Storage (GCS)
- **Knowledge Base**: Vertex AI Serverless RAG Engine
- **Code Execution**: Agent Engine Sandbox Code Executor
- **UI & Proxy**: FastAPI backend proxy (`a2a-sdk`), HTML5/CSS3 plain chat frontend with A2UI card renderer

---

## 🚀 Local Setup & Running Instructions

### Prerequisites
- Python 3.10+ and [`uv`](https://github.com/astral-sh/uv) package manager
- Authenticated Google Cloud SDK (`gcloud auth application-default login`)

### 1. Clone & Set Up Environment
```bash
git clone https://github.com/lokender88/buildwithgemini-apartment-finder.git
cd buildwithgemini-apartment-finder
uv venv
source .venv/bin/activate
uv pip install -r requirements.txt
```

### 2. Seed Firestore Database (Optional)
```bash
python seed_firestore.py
```

### 3. Run Agent Locally via ADK CLI
```bash
agents-cli run --mode a2a
```

### 4. Run Frontend Proxy & Web Interface Locally
Navigating to the `frontend/` folder, install requirements, and start the FastAPI proxy server:
```bash
cd frontend
uv pip install -r requirements.txt
export AGENT_ENGINE_RESOURCE_NAME="<your-reasoning-engine-resource-name>"
export AGENT_DIRECTORY="app"
uv run python main.py
```
*The local chat web interface will be accessible locally on port 8080.*

---

## ☁️ Deployment

### Deploying the Agent to Agent Platform
```bash
agents-cli deploy
```

### Deploying the Frontend Proxy to Cloud Run
```bash
cd frontend
gcloud run deploy apartment-finder-frontend \
    --source . \
    --region us-central1 \
    --allow-unauthenticated \
    --set-env-vars AGENT_ENGINE_RESOURCE_NAME="<your-reasoning-engine-resource-name>",AGENT_DIRECTORY="app"
```

---

## 📄 License
Apache-2.0 License
