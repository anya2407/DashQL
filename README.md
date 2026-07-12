# 📊 DashQL

**Ask for a dashboard, get it instantly.** DashQL is an agentic AI system that turns natural-language requests into live, interactive dashboards — SQL generation, chart selection, and business insights, all driven by an LLM-orchestrated pipeline with built-in caching and data governance.

> Built as a hands-on exploration of agentic architecture design: explicit LangGraph state machines, retrieval-augmented caching, and enterprise-style data governance — applied to a text-to-SQL and BI use case.

---

## What it does

Type a request like:

```
Create a sales dashboard with total revenue, top 10 customers by order count, and monthly order trends
```

...and DashQL will:

1. Check if a similar dashboard already exists (and reuse it, refreshed with live data, if so)
2. Plan what components the dashboard needs (charts, tables, KPIs)
3. Generate SQL for each component
4. Validate the SQL against data governance rules (PII exclusion, safety checks)
5. Execute the queries against the database
6. Choose the best visualization for each result
7. Generate a short natural-language business insight summary
8. Persist the dashboard for instant reuse next time

All of this happens as a single request through an orchestrated agent pipeline — no manual SQL writing, no manual chart configuration.

---

## Architecture

DashQL is built as an **explicit multi-agent state graph** using LangGraph, rather than a single tool-calling loop. Each stage of dashboard generation is a distinct node with a narrow responsibility, making the pipeline debuggable, extensible, and easy to reason about.

```
                              START
                                │
                                ▼
                          Retrieval Node ──── cache hit ────┐
                                │                            │
                          (cache miss)                       ▼
                                │                    Load from GitHub
                                ▼                            │
                        Dashboard Planner                    │
                                │                             │
                                ▼                             │
                         SQL Generator                        │
                                │                             │
                                ▼                             │
                       Governance Check ──fail──► retry ──┐   │
                                │  (bounded retries)       │   │
                             (pass)                        │   │
                                ▼                           │   │
                         SQL Executor ◄──────────────────────┘   │
                                │                                │
                       ┌────────┴────────┐                       │
                  (fresh)            (cached)                    │
                       │                  └──────────────────────┘
                       ▼
                  Visualizer
                       │
                       ▼
                 Business Insights
                       │
                       ▼
              Save to Cache (GitHub + vector index)
                       │
                       ▼
                      END
```

**Why an explicit graph instead of a tool-calling agent?** Early versions of this project used a single LLM with bound tools (schema lookup, SQL execution) in a ReAct-style loop. That approach is genuinely agentic, but harder to debug, less predictable in API usage, and doesn't cleanly support future features like "only re-run the visualizer when the user asks to change chart type." The explicit graph trades some flexibility for reliability, debuggability, and the ability to skip expensive stages entirely on a cache hit — while every transition is still driven by LLM output (planning decisions, governance pass/fail, cache similarity), not hardcoded logic.

---

## Key features

### 🔁 Retrieval-augmented dashboard caching
Every generated dashboard is embedded (via a local `sentence-transformers` model) and indexed in a persistent Chroma vector store. Future requests are checked for similarity before regenerating from scratch — a cache hit skips planning, SQL generation, and governance entirely, going straight to execution (for fresh data) and rendering. Dashboard content itself (layout + SQL) is stored as versioned JSON in a dedicated GitHub repository, so cached dashboards always reflect live data on reuse rather than stale snapshots.

### 🛡️ Data governance layer
Before any SQL touches the database, it passes through a dedicated governance node that checks:
- **Read-only enforcement** — only `SELECT` statements are permitted (parsed via `sqlglot`, not regex/keyword matching)
- **PII exclusion** — sensitive columns (contact info, addresses, birth dates) are excluded from the schema the LLM ever sees, *and* independently checked for at the SQL level in case of hallucination
- **Bounded retry** — a failing query is sent back to the SQL Generator with the specific violation, up to a capped number of retries, before failing gracefully instead of crashing

### 💡 Business insights
After data is computed, a dedicated insights agent summarizes the results in plain language — surfacing trends and standout numbers rather than leaving the user to interpret raw charts and tables alone.

### 📊 Adaptive visualization
A dedicated visualizer agent inspects each component's actual data shape (columns, sample values) and chooses the most appropriate chart type — rather than relying on fixed rules — while table and KPI components are rendered as-is.

---

## Tech stack

| Layer | Technology |
|---|---|
| Orchestration | LangGraph (explicit state graph) |
| LLM | Google Gemini (`gemini-2.5-flash`) via `langchain-google-genai` |
| Embeddings | `sentence-transformers` (`all-MiniLM-L6-v2`, local, no API cost) |
| Vector store | ChromaDB (persistent, local) |
| SQL safety | `sqlglot` (AST-based validation, not keyword blocking) |
| Database | SQLite (Northwind sample dataset) |
| Persistence | GitHub API (`PyGithub`) — versioned dashboard artifacts |
| Frontend | Streamlit |
| Visualization | Plotly |
| Data handling | pandas |

---

## Project structure

```
dashql/
├── agents/
│   ├── planner.py         # decides dashboard components from the request
│   ├── sql_generator.py   # generates SQL per component
│   ├── visualizer.py      # chooses chart types and layout
│   └── insights.py        # generates natural-language business insights
│
├── nodes/
│   └── retreival.py       # Chroma similarity search + indexing
│
├── tools/
│   ├── check_schema.py    # live schema introspection, PII-filtered
│   ├── database.py        # SQL execution with row-limit safety cap
│   ├── governance.py      # PII / forbidden-table / SELECT-only checks
│   └── github.py          # dashboard persistence (save/load JSON)
│
├── database/
│   └── northwind.db
│
├── config.py               # PII column list, forbidden tables, row limits
├── main.py                 # graph definition, state, node wiring
├── frontend.py             # Streamlit UI
└── requirements.txt
```

---

## Setup

```bash
git clone <your-repo-url>
cd dashql
python -m venv venv
venv\Scripts\activate          # Windows
pip install -r requirements.txt --break-system-packages
```

Create a `.env` file (see `.env.example`):

```
GOOGLE_API_KEY=your_gemini_api_key_here
GITHUB_TOKEN=your_github_personal_access_token_here
GITHUB_REPO=your-username/your-dashboard-storage-repo
DATABASE_PATH=database/northwind.db
CHROMA_PERSIST_DIR=vector_store/
MAX_ROW_LIMIT=200
SIMILARITY_THRESHOLD_EXACT=0.95
SIMILARITY_THRESHOLD_SIMILAR=0.75
```

Run it:

```bash
python -m streamlit run frontend.py
```

---

## Example requests

```
Show me monthly revenue trends
Create a sales dashboard with total revenue, top 10 customers by order count, and monthly order trends
Show me revenue by product category
Show me sales trends for 2013 only
```

---

## Design decisions worth noting

- **Local embeddings over API-based embeddings** for the caching layer — since cache checks happen on every request, keeping this path free, fast, and independent of external API rate limits was a deliberate reliability choice, distinct from using Gemini for the actual generation work where quality matters most.
- **GitHub as source of truth, not local disk** — dashboard artifacts are stored as real, versioned, human-inspectable JSON files in a dedicated repository rather than opaque cache entries, so cached dashboards remain auditable and diffable over time.
- **Governance as a dedicated graph node, not inline checks** — formalizing PII/safety enforcement as its own stage (with its own retry loop) rather than folding it into SQL execution keeps the security boundary explicit and independently testable.

## Known limitations / future work

- No authentication or row-level security — a production version would need per-user access control, particularly for PII-adjacent columns
- No handling for off-topic/non-analytics requests — the pipeline currently assumes every request is dashboard-related
- Similarity thresholds for caching were tuned empirically on a small set of examples and would benefit from broader calibration at scale
- CSV upload / alternate data sources are a natural extension, using the same schema-introspection pattern already in place for the Northwind database
