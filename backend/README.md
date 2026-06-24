# Cloud Crew AI — Backend

Python 3.12+ backend implementing the Cloud Crew AI multiagent AWS architecture advisor.

## Architecture

Feature + Clean Architecture. Dependency direction: `interface → application → domain` and `infrastructure → domain`. The domain is pure — no FastAPI, no LangGraph, no LLM SDK imports.

## Setup

```bash
cd backend
python -m venv .venv
source .venv/bin/activate          # Linux/macOS
# or: .venv\Scripts\activate       # Windows

pip install -e ".[dev]"
```

## Run tests

```bash
# All tests with coverage
pytest

# Verbose, stop on first failure
pytest -v -x

# Domain tests only
pytest tests/domain/

# Application tests only
pytest tests/application/
```

## Project structure

```
backend/
├── src/
│   ├── features/
│   │   └── crew/
│   │       ├── domain/          # Pure — no frameworks
│   │       │   ├── value_objects/
│   │       │   ├── entities/
│   │       │   ├── agents/      # Agent rules per specialist
│   │       │   └── ports/       # Protocols (interfaces)
│   │       ├── application/
│   │       │   └── use_cases/
│   │       └── infrastructure/  # Adapters (fakes + curated catalog)
│   └── shared/                  # Config, DI factory
└── tests/
    ├── domain/
    └── application/
```
