# 🚀 M&A Agents - AI-Powered Sell-Side M&A Outreach

## 📌 Overview
The M&A Agents system automates the sell-side M&A outreach process using a multi-agent AI architecture. This platform reduces manual inefficiencies in identifying, analyzing, and engaging potential buyers by leveraging CrewAI, Exa.ai, Firecrawl, and Qdrant.

## ✨ Key Features
- ✅ **Automated Buyer Discovery** – Expands beyond seed lists using AI-powered web scraping
- ✅ **Deep Buyer Profiling** – Extracts structured investment data from buyer websites
- ✅ **News & Market Context Analysis** – Fetches relevant acquisition and funding news
- ✅ **Intelligent Buyer Matching** – AI-driven decision-making for suitability analysis
- ✅ **Hyper-Personalized Outreach** – Generates tailored emails to engage potential buyers
- ✅ **Buyer Interaction Management** – Handles responses, scheduling, and follow-ups

## 🏗️ System Architecture
The system is powered by six AI agents, each handling a specialized task:

1. **1️⃣ Discovery Agent** – Uses Exa.ai to find new buyers based on industry & AUM criteria
2. **2️⃣ Profile Scraper Agent** – Uses Firecrawl & CrewAI Scraper to collect firmographic & investment details
3. **3️⃣ News Scraper Agent** – Leverages Google News API & Serper to extract relevant buyer news
4. **4️⃣ Analysis/Matching Agent** – Uses AI reasoning to determine buyer fit based on historical transactions
5. **5️⃣ Engagement Agent** – Generates and sends highly personalized email outreach
6. **6️⃣ Response Agent** – Manages responses and assists in scheduling meetings

## 🔧 Tech Stack & Tools
| Category              | Tools & Frameworks                          |
|-----------------------|---------------------------------------------|
| AI Orchestration      | CrewAI                                      |
| Web Scraping          | Exa.ai, Firecrawl, CrewAI Scraper           |
| Data Storage          | Qdrant, MongoDB (TBD)                       |
| LLMs                  | GPT-4o, DeepSeek R1, Sonnet 3.7             |
| Cloud Infra           | AWS (SageMaker - Future)                    |
| Email Integration     | Outlook, Gmail APIs                         |

## 🛠️ Installation & Setup
1. **Install Dependencies**
```bash
# Using uv (recommended)
uv pip install -e .

# For development dependencies
uv pip install -e ".[dev]"
```

# QuickChat - Full Stack Chat Application

A real-time chat application with React frontend and FastAPI backend.

## Project Structure

```
/
├── frontend/           # React + TypeScript + Vite.js + Tailwind CSS
│   ├── src/            # React source code
│   ├── dist/           # Built frontend (after running build)
│   └── ...
├── backend/            # Backend server directory
│   ├── main.py         # Main FastAPI application
│   └── ...
├── pyproject.toml      # Project configuration and dependencies
└── uv.lock             # Dependency lock file for uv
```

## Setup & Development

### Prerequisites

- Node.js v22.14.0
- Python 3.11 or higher
- pnpm package manager
- uv package manager for Python

### Frontend Development

1. Install frontend dependencies:

```bash
cd frontend
pnpm install
```

2. Start the frontend development server:

```bash
pnpm dev
```

The frontend will be available at http://localhost:5173

### Backend Development

1. Create and activate a virtual environment (optional but recommended):

```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

2. Install Python dependencies with uv:

```bash
uv pip install -e .
```

3. Start the backend server:

```bash
# From the backend directory
cd backend
python main.py
```

The backend will be available at http://localhost:8080 (or whichever port you configure via the PORT environment variable)

### Production Build

For production, you should build the frontend and then run the backend:

1. Build the frontend:

```bash
cd frontend
pnpm build
```

2. Run the backend (which will serve the built frontend):

```bash
cd backend
python main.py
```

The complete application will be available at http://localhost:8080 (or whichever port you configure)

## Features

- Real-time chat interface with WebSocket connection that automatically adapts to any port
- Responsive design with Tailwind CSS
- TypeScript for type safety
- FastAPI backend with WebSocket support
