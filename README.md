# Enterprise RAG Document Intelligence Platform

A production-grade AI system for document intelligence using Retrieval-Augmented Generation (RAG).

## Architecture

* **Frontend:** React + Vite (Glassmorphism design)
* **Backend:** FastAPI (Python)
* **Document Ingestion:** PyMuPDF + Custom 7-step Text Cleaner
* **Embeddings:** SentenceTransformers (`all-MiniLM-L6-v2`)
* **Vector DB:** ChromaDB
* **LLM Engine:** Groq API (`llama-3.1-70b-versatile`)

## Features

* **Strict No-Hallucination Prompting:** Answers are generated *strictly* from retrieved context.
* **Citation System:** AI responses include citations mapped to the exact page and source file.
* **Smart Chunking:** Recursive character-based splitting with semantic boundaries and overlap.
* **Confidence Scoring:** Validates the semantic match between query and retrieved context.

## Setup Instructions

### 1. Backend

```bash
cd backend
python -m venv venv
source venv/bin/activate  # (or venv\Scripts\activate on Windows)
pip install -r requirements.txt
```

Create a `.env` file based on `.env.example`:
```bash
cp .env.example .env
# Edit .env and add your GROQ_API_KEY
```

Run the API:
```bash
uvicorn main:app --reload
```

### 2. Frontend

```bash
cd frontend
npm install
npm run dev
```

### 3. Docker (Optional Production Deployment)

Ensure your `.env` file is set in the `backend/` folder.

```bash
docker-compose up --build -d
```
The frontend will be available at `http://localhost`, and the backend API at `http://localhost:8000`.

## Modules Implemented
✅ Project Setup
✅ Document Ingestion & Extraction
✅ Chunking Engine
✅ Embedding System
✅ Vector Database Layer
✅ Retrieval System
✅ RAG Engine
✅ API Layer
✅ Frontend UI
✅ Docker & Production Polish
