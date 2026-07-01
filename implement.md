
# Project Goal

## Multi-Agent AI Research Platform

### Vision

Build an AI system that behaves like a junior research analyst.

Instead of answering one prompt, it can autonomously:

* Understand the user's research goal
* Break it into subtasks
* Search trusted sources
* Download and analyze PDFs
* Extract structured information
* Verify claims
* Store knowledge
* Generate charts
* Write a professional research report
* Answer follow-up questions using previous research

Essentially, the system should feel like **Perplexity + NotebookLM + Deep Research + ChatGPT**, but implemented by you.

---

# Example User Query

```
Research the AI chip market in 2026.
Compare NVIDIA, AMD, Groq, Cerebras.

Include

• market trends
• revenues
• AI products
• funding
• risks
• opportunities

Generate charts and export to PDF.
```

The user presses **Generate Report**.

After a few minutes they receive:

✓ Executive Summary

✓ Industry Analysis

✓ Company Comparison

✓ Revenue Charts

✓ Funding Charts

✓ SWOT Analysis

✓ Risks

✓ Future Outlook

✓ References

✓ PDF Report

This is the experience you're building.

---

# Final Product

Imagine a web application.

```
+--------------------------------------------------+

        AI Research Assistant

-----------------------------------------------

Research Topic

[ AI Chip Market in 2026                 ]

Research Depth

(o) Quick
(o) Standard
(o) Deep

Sources

✓ Web
✓ PDFs
✓ Research Papers
✓ SEC Filings

Output

✓ Charts
✓ PDF
✓ Markdown

                Generate Report

-----------------------------------------------

Live Progress

✓ Planning

✓ Searching

✓ Reading PDFs

✓ Verifying Facts

✓ Writing Report

✓ Creating Charts

✓ Exporting PDF

-----------------------------------------------

Final Report
```

---

# Core Features

## 1. AI Research Planning

Instead of immediately searching,

The system first asks:

"What exactly do I need to do?"

Planner Agent creates a structured execution plan.

Example

```
Goal

Research AI chip market.

↓

Break into tasks

↓

Find market reports

↓

Find financial reports

↓

Compare companies

↓

Generate charts

↓

Write report
```

This is why LangGraph is used.

---

## 2. Autonomous Web Search

The Search Agent gathers information from multiple sources.

Examples

News

Blogs

Official company websites

Research firms

Government reports

Documentation

Academic papers

Search providers

```
Tavily

Brave Search

SerpAPI
```

The agent ranks results by credibility.

---

## 3. Automatic PDF Discovery

Many valuable reports are only available as PDFs.

Examples

```
Investor Reports

Whitepapers

Annual Reports

Research Papers

SEC Filings

Government Reports
```

The PDF Agent downloads them automatically.

---

## 4. Intelligent PDF Processing

Every PDF is processed through a document pipeline.

```
PDF

↓

Extract text

↓

Remove headers

↓

Detect tables

↓

Detect images

↓

Chunk text

↓

Generate embeddings

↓

Store in Vector Database
```

Libraries

```
PyMuPDF

Docling

Unstructured

LlamaParse
```

---

## 5. Knowledge Base (RAG)

After processing,

Every document becomes searchable.

User asks

```
What was NVIDIA AI revenue?
```

Instead of searching the internet again,

The system searches its own indexed documents.

This makes follow-up research much faster.

---

## 6. Structured Information Extraction

Rather than storing only text,

The system extracts structured facts.

Example

```
Company

Revenue

Funding

Employees

Headquarters

AI Products

Founders

Market Share
```

Output

```json
{
 "company":"NVIDIA",
 "revenue":"$44B",
 "employees":36000,
 "market_share":"82%"
}
```

Now charts become easy.

---

## 7. Fact Verification

LLMs hallucinate.

Every important statement must be verified.

Example

Writer says

```
AMD owns 24% market share.
```

Verification Agent

↓

Find original source

↓

Compare numbers

↓

Confidence score

↓

Verified

or

Rejected

Only verified claims appear in the report.

---

## 8. Report Generation

Writer Agent converts verified facts into a professional report.

Sections

```
Executive Summary

Industry Overview

Market Trends

Company Profiles

Competitive Analysis

SWOT

Charts

Future Outlook

References
```

Generated in Markdown first.

Then converted into PDF.

---

## 9. Chart Generation

Automatically generate

```
Revenue comparison

Funding

Market Share

Timeline

Growth

Investments
```

Using

```
Pandas

Matplotlib

Plotly
```

---

## 10. Export System

Export

```
Markdown

PDF

DOCX
```

---

## 11. Persistent Memory

The assistant remembers

Previous reports

Downloaded PDFs

Previous searches

Extracted entities

Visited websites

So later

```
Compare today's report
with last month's report.
```

works immediately.

---

# Multi-Agent Architecture

```
                     USER

                       │

                       ▼

              Planner Agent

                       │

        ┌──────────────┼─────────────┐

        ▼              ▼             ▼

 Search Agent     PDF Agent     Memory Agent

        │              │             │

        ▼              ▼             ▼

 Search Web     Parse PDFs     Retrieve Data

        │              │

        └──────────────┘

               │

               ▼

       Information Collector

               │

               ▼

      Extraction Agent

               │

               ▼

       Fact Checker

               │

               ▼

        Writer Agent

               │

               ▼

      Chart Generator

               │

               ▼

       Export Agent

               │

               ▼

           Final Report
```

---

# LangGraph Workflow

```
START

↓

Planner

↓

Parallel Execution

↓

Search

+

Download PDFs

+

Memory Retrieval

↓

Merge Results

↓

Extract Facts

↓

RAG Retrieval

↓

Fact Verification

↓

Writer

↓

Charts

↓

Export

↓

END
```

Notice the middle stages run **in parallel** where possible to reduce latency.

---

# Complete Technology Stack

## Frontend

* Next.js
* React
* TypeScript
* Tailwind CSS
* shadcn/ui
* React Query
* WebSockets (live progress)
* PDF viewer
* Chart.js or Recharts for report preview

---

## Backend

* Python
* FastAPI
* Pydantic
* Uvicorn

---

## AI

* LangGraph
* LangChain
* Google Gemini 

---

## Search

* Tavily

---

## PDF Processing

* Docling


---

## RAG

* OpenAI Embeddings
* ChromaDB (development)
* Pinecone (production)
* FAISS (local alternative)

---

## Database

* PostgreSQL

Stores:

* Users
* Reports
* Metadata
* Extracted entities
* Search history

---

## Cache

* Redis

Stores:

* Session state
* Agent state
* Temporary results
* Frequently used searches

---

## Charts

* Pandas
* Matplotlib
* Plotly

---

## Export

* Markdown
* ReportLab or WeasyPrint (PDF)
* python-docx (DOCX)

---

## Deployment

* Railway / Render 
*

---

# Suggested Backend Structure

```text
backend/
├── app/
│   ├── api/                 # FastAPI routes
│   ├── agents/              # Planner, Search, PDF, RAG, etc.
│   ├── graph/               # LangGraph workflow and state
│   ├── prompts/             # Prompt templates
│   ├── tools/               # Search, parsing, embeddings
│   ├── rag/                 # Vector store and retrieval logic
│   ├── services/            # Report, export, memory
│   ├── database/            # SQLAlchemy models and migrations
│   ├── schemas/             # Pydantic models
│   ├── utils/               # Logging, config, helpers
│   └── main.py              # FastAPI entry point
├── tests/
├── Dockerfile
└── requirements.txt
```

```text
frontend/
├── app/
├── components/
├── hooks/
├── lib/
├── services/                # API client
├── types/
└── public/
```

---

# Development Roadmap

## Phase 1 — Foundation

* Set up FastAPI backend and Next.js frontend.
* Implement authentication (optional for MVP).
* Create basic project structure and configuration.
* Add logging, environment management, and Docker.

## Phase 2 — Research Engine

* Build the Planner Agent.
* Integrate web search.
* Implement PDF download and parsing.
* Add document chunking and embedding generation.
* Set up the vector database and RAG pipeline.

## Phase 3 — Multi-Agent Orchestration

* Define the LangGraph state.
* Implement Planner, Search, PDF, Extractor, Fact Checker, Writer, and Chart agents.
* Enable parallel execution where appropriate.
* Add retry and error-handling logic.

## Phase 4 — Report Generation

* Generate structured reports with citations.
* Create charts from extracted data.
* Support PDF, Markdown, and DOCX exports.
* Stream live progress updates to the UI.

## Phase 5 — Production Readiness

* Add Redis caching.
* Persist reports and metadata in PostgreSQL.
* Add evaluation metrics (retrieval quality, citation coverage, factual consistency).
* Implement monitoring, rate limiting, and comprehensive testing.
* Deploy with Docker to a cloud platform.


