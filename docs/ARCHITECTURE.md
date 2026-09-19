# Architecture

```mermaid
flowchart LR
    user[Auditor / Operator] --> ui[Streamlit UI\nport 8501]
    ui --> agent[AI Agent\nFastAPI\nport 8000]
    agent --> db[(PostgreSQL\naudit + ERP)]
    agent --> redis[(Redis\ncache)]
    agent --> qdrant[(Qdrant\nvector store)]
    agent --> erp[Mock ERP\nFastAPI\nport 8001]
    incoming[Incoming invoices\nread-only bind mount] --> agent
    agent --> reports[Reports volume\nJSON + HTML]

    classDef infra fill:#eef6ff,stroke:#4f8df7,stroke-width:1px;
    class ui,agent,db,redis,qdrant,erp,incoming,reports infra;
```

## Runtime flow

1. The monitor sees new files in the incoming directory and records file events.
2. The agent extracts text, detects language, translates, and parses invoice fields.
3. Internal and ERP validators compare invoice numbers, amounts, and PO data.
4. Reports are persisted to PostgreSQL and the reports volume.
5. Retrieval and SQL routing answer auditor questions using Qdrant and relational data.
