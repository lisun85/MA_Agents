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
pip install crewai[tools] qdrant-client firecrawl-py
