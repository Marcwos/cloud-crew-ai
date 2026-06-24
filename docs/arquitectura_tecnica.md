# Cloud Crew AI — Arquitectura técnica

> Documento de base para construcción. Acompaña a [`propuesta_cloud_crew_ai_v2.md`](./propuesta_cloud_crew_ai_v2.md).
> **Versión:** 2.0 · **Estado:** Decisiones cerradas · listo para scaffolding

---

## 1. Principio rector

> **Conceptos antes que código.** Definimos contratos, puertos y el grafo *antes* de implementar.
> El valor de la app no es generar un diagrama: es generar el **razonamiento trazable y correcto** detrás de cada decisión de arquitectura AWS.

Dos reglas no negociables que atraviesan todo el diseño:

1. **El dominio es independiente.** La lógica de la crew (agentes, estado, debate, decisión) no conoce FastAPI, ni LangGraph, ni el proveedor de LLM, ni React. Todo lo externo entra por **puertos** (interfaces) y se implementa con **adaptadores**.
2. **La verdad antes que la cobertura.** Un agente nunca recomienda un servicio AWS que no pueda justificar contra una fuente de conocimiento. Preferimos decir menos y que todo sea correcto.

---

## 2. Decisiones de arquitectura (cerradas)

| Tema | Decisión | Razón |
|---|---|---|
| **Estilo (back y front)** | **Feature + Clean Architecture** | Organización por feature (screaming architecture) con capas limpias internas. El dominio queda portable. |
| **Grounding AWS** | **Catálogo curado ahora, RAG después** | Demo-safe y sin infra extra para el MVP; el puerto `KnowledgeSource` permite enchufar RAG sin reescribir. |
| **Proveedor LLM** | **Puerto `LLMProvider` + adaptadores** | Anthropic, OpenAI, DeepSeek, Bedrock intercambiables por config. Habilita *tiering* de modelos. |
| **Tiempo real** | **SSE (Server-Sent Events)** | El flujo es backend→frontend; SSE es más simple y se reconecta solo. |
| **Paralelismo** | **Fan-out real con LangGraph** | Los 5 especialistas corren concurrentes de verdad: es la innovación a mostrar. |
| **Persistencia** | **Memoria primero, PostgreSQL después** | Ambas detrás del puerto `CrewRepository`. Cambiar una por otra no toca el dominio. |
| **Debate** | **1 ronda de revisión cruzada (tope)** | Protege el ritmo de la demo; ampliable por config. |

---

## 3. Vista de alto nivel

```
┌─────────────┐      SSE (eventos)      ┌──────────────────────────────┐
│  Frontend   │ ◄───────────────────    │  Backend (FastAPI)           │
│ React+Vite  │                         │  ┌────────────────────────┐  │
│ Oficina 2D  │  ───────────────────►   │  │ Feature: crew          │  │
└─────────────┘   POST /sessions        │  │  domain ← app ← infra  │  │
                                        │  └───────────┬────────────┘  │
                                        └──────────────┼───────────────┘
                              ┌─────────────┬──────────┼───────────┬────────────┐
                              ▼             ▼          ▼            ▼            ▼
                         LLMProvider   KnowledgeSrc  Orchestr.  CrewRepo   EventPublisher
                         (adapters)    (catalog/RAG) (LangGraph) (mem/PG)   (SSE)
```

Cada flecha del segundo nivel es un **puerto** del dominio con uno o más **adaptadores**. El dominio depende de las interfaces, nunca de las implementaciones.

---

## 4. Puertos del dominio (las interfaces que importan)

```python
# Borrador conceptual — contratos, no implementación final

class LLMProvider(Protocol):
    """Puerto LLM. Un adaptador por proveedor."""
    async def complete(self, request: LLMRequest) -> LLMResponse: ...

class KnowledgeSource(Protocol):
    """Fuente de verdad sobre servicios AWS. Catálogo hoy, RAG mañana."""
    async def services_for(self, domain: AgentDomain, need: str) -> list[ServiceFact]: ...

class CrewRepository(Protocol):
    """Persistencia de sesiones y planes. Memoria hoy, PostgreSQL mañana."""
    async def save(self, session: CrewSession) -> None: ...
    async def get(self, session_id: str) -> CrewSession | None: ...

class EventPublisher(Protocol):
    """Empuja AgentEvent al frontend. Adaptador SSE."""
    async def publish(self, session_id: str, event: AgentEvent) -> None: ...
```

> **Esto es el corazón de la decisión "LLM con adapter".** Los agentes reciben un `LLMProvider`; no saben ni les importa si detrás hay Claude, GPT, DeepSeek o Bedrock.

### Adaptadores LLM previstos

| Adaptador | Proveedor | Nota |
|---|---|---|
| `AnthropicAdapter` | Anthropic API | Claude directo. |
| `OpenAIAdapter` | OpenAI | GPT. |
| `DeepSeekAdapter` | DeepSeek | Económico para especialistas. |
| `BedrockAdapter` | Amazon Bedrock | Coherente con el tema AWS del evento. |

La selección es por **config** (`LLM_PROVIDER=...`) y permite *tiering*: un modelo para Leslie y otro, más barato, para los especialistas. Un `LLMProviderFactory` resuelve el adaptador en el *composition root*.

---

## 5. El grafo de la crew (LangGraph)

```
                    ┌──────────────┐
                    │   ENTRADA    │  (reto del usuario)
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │   LESLIE     │  triage: requisitos + restricciones → reparte
                    └──────┬───────┘
              ┌─────┬──────┼──────┬─────────┐   (fan-out REAL en paralelo)
              ▼     ▼      ▼      ▼         ▼
           ┌────┐ ┌────┐ ┌────┐ ┌─────┐ ┌─────┐
           │ALAN│ │EDGAR││HEDY│ │GRACE│ │VINT │
           └─┬──┘ └─┬──┘ └─┬──┘ └──┬──┘ └──┬──┘
             └──────┴──────┼───────┴───────┘   (fan-in)
                           ▼
                    ┌──────────────┐
                    │   REVIEW     │  revisión cruzada (1 ronda) con trade-offs
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │   LESLIE     │  consolidación → plan integral
                    └──────┬───────┘
                           ▼
                    ┌──────────────┐
                    │   SALIDA     │  arquitectura + justificación por servicio
                    └──────────────┘
```

> LangGraph vive en la capa de **infraestructura** (`orchestration`). Es un *detalle*: implementa el flujo, pero las decisiones de cada nodo delegan en los casos de uso y agentes del dominio.

**Aristas condicionales:**
- Reto trivial → especialistas no relevantes aportan lo mínimo.
- Conflicto fuerte en `review` → 1 re-propuesta acotada (tope para no romper el tiempo).

---

## 6. Estado compartido y modelos del dominio

```python
# Borrador conceptual

class Constraint(BaseModel):
    kind: Literal["cost", "security", "latency", "scale", "compliance"]
    detail: str

class ServiceFact(BaseModel):           # viene de KnowledgeSource (verdad)
    name: str                           # "AWS Lambda"
    category: str
    when_to_use: str
    source: str                         # catálogo o cita RAG

class Proposal(BaseModel):
    agent: str
    services: list[str]
    rationale: str
    alternatives_rejected: list[str]
    trade_offs: str

class Review(BaseModel):
    reviewer: str
    target_agent: str
    challenge: str
    trade_off: str

class AgentEvent(BaseModel):            # para el frontend en vivo
    agent: str
    action: Literal["idle","moving","analyzing","proposing","reviewing","done"]
    status: str
    message: str

class CrewState(BaseModel):
    session_id: str
    challenge: str
    constraints: list[Constraint]
    tasks: dict[str, str]
    proposals: list[Proposal]
    reviews: list[Review]
    final_plan: FinalPlan | None
    events: list[AgentEvent]
```

> **Regla de validez:** una `Proposal` sin `rationale` y `alternatives_rejected` es inválida. Sin justificación, no hay propuesta.

---

## 7. Contrato de eventos en tiempo real (SSE)

El backend emite eventos por SSE; el frontend mueve y anima a los personajes según `action`.

```json
{
  "type": "agent_event",
  "session_id": "abc123",
  "agent": "alan",
  "action": "analyzing",
  "status": "in_progress",
  "message": "Evaluando Lambda vs Fargate para carga variable",
  "timestamp": "..."
}
```

Mapeo `action` → oficina 2D:
`idle` (escritorio) · `moving` (camina a su estación) · `analyzing` (piensa) · `proposing` (habla) · `reviewing` (cuestiona a otro) · `done` (listo).

---

## 8. Estructura de carpetas — Backend (Feature + Clean)

```
backend/
├── src/
│   ├── features/
│   │   └── crew/                          # FEATURE principal
│   │       ├── domain/                     # PURO — sin frameworks
│   │       │   ├── entities/               # CrewSession, Proposal, Review, FinalPlan
│   │       │   ├── value_objects/          # Constraint, ServiceFact, AgentEvent
│   │       │   ├── agents/                 # reglas/criterio de cada especialista
│   │       │   │   ├── leslie.py           # triage + consolidación
│   │       │   │   ├── alan.py · edgar.py · hedy.py · grace.py · vint.py
│   │       │   └── ports/                  # INTERFACES
│   │       │       ├── llm_provider.py
│   │       │       ├── knowledge_source.py
│   │       │       ├── crew_repository.py
│   │       │       └── event_publisher.py
│   │       ├── application/                # CASOS DE USO (orquestan dominio vía puertos)
│   │       │   └── use_cases/
│   │       │       ├── run_crew_session.py
│   │       │       └── get_session.py
│   │       ├── infrastructure/             # ADAPTADORES (implementan puertos)
│   │       │   ├── llm/                    # anthropic_, openai_, deepseek_, bedrock_adapter.py
│   │       │   ├── knowledge/              # curated_catalog_adapter.py (hoy) · rag_adapter.py (después)
│   │       │   ├── orchestration/          # langgraph_graph.py (el grafo vive acá)
│   │       │   ├── persistence/            # in_memory_repo.py (hoy) · postgres_repo.py (después)
│   │       │   └── events/                 # sse_event_publisher.py
│   │       └── interface/                  # ENTRADA HTTP
│   │           ├── routes.py               # POST /sessions, GET /sessions/{id}
│   │           ├── sse.py                  # stream de eventos
│   │           └── schemas.py              # DTOs request/response
│   ├── shared/                             # config, DI/factory, tipos comunes, errores
│   └── main.py                             # COMPOSITION ROOT: arma puertos↔adaptadores
└── tests/
    ├── domain/                             # agentes y reglas (rápidos, sin IO)
    ├── application/                        # casos de uso con adaptadores fake
    └── integration/                        # grafo completo + SSE
```

**Dirección de dependencias:** `interface → application → domain` y `infrastructure → domain`. El dominio no importa nada hacia afuera. Las dependencias se inyectan en `main.py`.

---

## 9. Estructura de carpetas — Frontend (Feature + Clean)

```
frontend/
├── src/
│   ├── features/
│   │   └── crew-office/                    # FEATURE principal
│   │       ├── domain/                      # tipos PUROS (TS): AgentEvent, CrewState, Plan
│   │       ├── application/                 # lógica de UI desacoplada
│   │       │   ├── useCrewSession.ts        # caso de uso: iniciar reto + consumir stream
│   │       │   └── agentReducer.ts          # estado de animación de la oficina
│   │       ├── infrastructure/              # ADAPTADORES hacia el backend
│   │       │   ├── sseClient.ts             # se suscribe al stream SSE
│   │       │   └── apiClient.ts             # POST /sessions
│   │       └── ui/                          # COMPONENTES (presentacional)
│   │           ├── Office.tsx               # canvas 2D
│   │           ├── AgentSprite.tsx          # personaje + estados
│   │           ├── ChallengeInput.tsx
│   │           └── PlanPanel.tsx            # plan final + justificaciones
│   ├── shared/                              # ui kit, lib, config, theme por estación
│   └── app/                                 # shell, providers, routing
└── tests/
```

> Mismo principio: la `ui` depende de `application`, que depende de `domain`. El `sseClient`/`apiClient` (infraestructura) son intercambiables (p. ej., un mock para la demo offline) sin tocar los componentes.

---

## 10. Estrategia de pruebas (TDD estricto)

Orden recomendado (test primero, en rojo):

1. **Reglas de agente (domain):** dado un `CrewState` y un `KnowledgeSource` fake, cada agente devuelve un `Proposal` válido (con justificación y alternativas).
2. **Caso de uso (application):** `run_crew_session` con `LLMProvider` y repo fakes produce un `final_plan` no vacío.
3. **Grafo (integration):** un reto simple recorre `triage → fan-out → review → consolidate`.
4. **Eventos (integration):** se emite la secuencia esperada de `AgentEvent` por SSE.
5. **E2E (frontend):** el usuario escribe un reto y la oficina renderiza ≥1 debate y el plan final.

Los puertos hacen el testing barato: nunca se llama a un LLM real en los tests de dominio/aplicación. Cobertura objetivo **≥ 80%** en la lógica de la crew.

---

## 11. Cómo arrancar (orden sugerido de construcción)

1. **Dominio + puertos** (sin IO): modelos, reglas de agentes, interfaces. Con sus tests.
2. **Adaptadores fake** (`InMemoryRepo`, `FakeLLM`, `CuratedCatalog`): para correr el flujo sin red.
3. **Caso de uso + grafo LangGraph**: cableado real del flujo con fakes.
4. **Adaptador LLM real** (uno primero, p. ej. Anthropic o Bedrock) detrás del puerto.
5. **SSE + frontend**: stream de eventos y oficina 2D consumiéndolo.
6. **Persistencia PostgreSQL** y **RAG**: se enchufan a sus puertos cuando el MVP ya corre.

> El catálogo curado de servicios AWS (la fuente de verdad inicial) es contenido a redactar con cuidado: es lo que evita que la app mienta. Conviene tratarlo como un artefacto de primera clase, no como un detalle.

---

*Cloud Crew AI — Arquitectura técnica · v2.0*
