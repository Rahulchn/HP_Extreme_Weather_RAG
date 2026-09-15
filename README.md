# Himachal Pradesh Extreme Weather RAG

An evidence-grounded retrieval-augmented generation system for exploring rainfall, cloudburst, and flash-flood records across **Kangra, Mandi, Shimla, and Kullu** from **2011 to 2026**. Data for 2026 is treated as partial telemetry and is never presented as a complete annual series.

The Streamlit application routes each question to a controlled retrieval path, builds a provenance-rich evidence pack, generates an answer through a configured Hugging Face model, and validates its citations before displaying it.

## What it supports

- Quantitative rainfall and event queries through parameterized SQLite functions
- Qualitative disaster-report retrieval through a local FAISS vector index
- Hybrid questions that combine measurements with reported impacts
- Explicit rejection of unsupported geographies, parameters, and dates
- Evidence labels such as `OBSERVED`, `CALCULATED`, `REPORTED`, and `MIXED`
- Citation-integrity checks and transparent evidence-pack inspection

## Architecture

```text
User question
    |
    v
Deterministic query router
    |-------------------------------|
    v                               v
SQLite structured retrieval     FAISS semantic retrieval
    |                               |
    |---------------+---------------|
                    v
              Evidence pack
                    v
        Hugging Face generation
                    v
       Deterministic validation
                    v
        Streamlit answer + sources
```

See [`docs/retrieval_architecture.md`](docs/retrieval_architecture.md) and [`docs/query_routing_rules.md`](docs/query_routing_rules.md) for the detailed contracts and routing rules.

## Quick start

Python 3.11 or newer is recommended.

```bash
python -m venv .venv
```

Activate the environment, then install dependencies:

```bash
python -m pip install -r requirements.txt
```

Copy `.env.example` to `.env` and add a Hugging Face read token:

```dotenv
HF_TOKEN=your_token_here
HF_MODEL=Qwen/Qwen2.5-7B-Instruct
HF_PROVIDER=featherless-ai
HF_TIMEOUT=30
HF_TEMPERATURE=0.1
HF_MAX_TOKENS=1024
```

Run the application from the repository root:

```bash
streamlit run app/main.py
```

## Offline smoke test

Retrieval and validation can be checked without making an LLM request:

```bash
python -c "from app.rag_engine import execute_query; r = execute_query('What was the maximum rainfall in Kangra in 2023?', bypass_llm=True); print(r.answer); print(r.validation_status)"
```

## Included data

The repository includes the artifacts needed to run the current validated system:

- `data/master/hp_extreme_weather.db`
- `data/master/document_chunks.json`
- `data/knowledge_base/vector_store/`
- Curated processed rainfall and event tables under `data/processed/`
- Evaluation fixtures, provenance reports, and audit documentation

The large raw IMD grids, source PDFs, milestone backups, local scratch diagnostics, and `.env` credentials are intentionally excluded from Git. Source provenance remains documented in `reports/source_registry.csv` and the acquisition/audit reports. The raw corpus can be reacquired with the scripts under `scripts/` where source endpoints remain available.

## Validation snapshot

The checked-in readiness report records passing structured, document, hybrid, unsupported-query, citation, security, and backend-integrity checks. See [`reports/final_demo_readiness.md`](reports/final_demo_readiness.md).

## Important scope notes

- Coverage is limited to Kangra, Mandi, Shimla, and Kullu.
- Supported hazards are rainfall, cloudburst, and flash flood.
- 2026 observations are partial and annual totals are withheld.
- Generated answers depend on the configured Hugging Face provider; retrieval itself runs locally.
- This is an academic decision-support and research demonstration, not an operational warning system.
