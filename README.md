# Cloud Crew AI

> Una oficina 2D de agentes de IA que diseña arquitecturas en AWS, en vivo y con criterio.

Una persona plantea un problema de negocio y un equipo de agentes especializados
—coordinados por **Leslie**, la orquestadora— analiza, debate y produce una
arquitectura de AWS justificada decisión por decisión, dentro de una oficina
virtual estilo pixel-art.

Los agentes **no personifican servicios de AWS**: representan roles de
especialistas humanos (cómputo, datos, seguridad, costos, redes) que eligen las
herramientas óptimas y explican *por qué*.

## La crew

| Rol | Nombre | Dominio |
|---|---|---|
| Orquestadora | **Leslie** | Triage, coordinación y consolidación |
| Cómputo | **Alan** | Backend, APIs, escalabilidad |
| Datos | **Edgar** | Bases de datos, almacenamiento, caché |
| Seguridad | **Hedy** | Identidades, secretos, privilegios |
| Monitoreo y Costos | **Grace** | Observabilidad y optimización financiera |
| Redes | **Vint** | Conectividad, topología, eventos |

## Stack

React + Vite + Tailwind (frontend) · Python + FastAPI (backend) ·
LangGraph + LangChain (orquestación) · PostgreSQL · AWS.

## Documentación

- [Propuesta del proyecto](./docs/propuesta_cloud_crew_ai_v2.md)
- [Arquitectura técnica](./docs/arquitectura_tecnica.md)
