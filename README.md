# AI Invoice Auditor

This repository contains the initial scaffold for the AI Invoice Auditor capstone.

## Commit 1

This is the baseline implementation for the first commit in the project plan:

- repository scaffold
- frozen contracts and configuration
- PostgreSQL, Qdrant, and Redis infrastructure
- initial database schemas

## Commit 2

This milestone adds the file intake monitor, Redis/LLM cache foundations, and the completed mock ERP service container. It includes the queue-based watcher and the first Bedrock/Redis compatibility layer described in the plan.

## Commit 3

This milestone adds extraction for PDF, DOCX, and PNG files, the agent and Streamlit container images, and the internal invoice validation logic using Decimal-based arithmetic checks.

## Getting started

1. Copy `.env.example` to `.env` and fill in values.
2. Run `docker compose up -d postgres qdrant redis`.
3. Build Python services as they are added in later commits.
