# Cloud Crew AI

> Una oficina 2D de agentes de IA que diseña arquitecturas en AWS, en vivo y con criterio.

**Propuesta de proyecto — Evento de la Comunidad AWS y Club de IA**
**Versión:** 3.0 · **Estado:** Propuesta para construcción

---

## 1. Visión del proyecto

**Cloud Crew AI** es una experiencia interactiva donde una persona plantea un problema de negocio o una necesidad técnica compleja y, en lugar de recibir una lista teórica de servicios, observa a un equipo de agentes de IA especializados colaborar en tiempo real dentro de una oficina virtual 2D estilo pixel-art.

Los agentes analizan la solicitud, distribuyen las tareas de forma inteligente, **debaten alternativas técnicas** y producen una arquitectura de Amazon Web Services (AWS) justificada decisión por decisión.

### Idea central

Los agentes **no personifican servicios de AWS**. Representan **roles de especialistas humanos** —arquitectura de cómputo, datos, seguridad, costos y redes— que eligen de forma objetiva las herramientas óptimas según la necesidad del negocio. El usuario no ve "una caja llamada Lambda": ve a un ingeniero argumentar *por qué* Lambda y no Fargate para una carga variable.

### Por qué importa

El valor diferencial no es generar un diagrama. Es **mostrar el razonamiento**: el porqué de cada servicio, las alternativas descartadas y los trade-offs de costo, seguridad y rendimiento. Eso es lo que normalmente queda oculto en una consultoría y lo que más cuesta enseñar.

---

## 2. Objetivos principales

| Objetivo | Descripción |
|---|---|
| **Demostración práctica** | Mostrar de forma visual y entretenida cómo opera un sistema multiagente coordinado. |
| **Educación en la nube** | Explicar la interconexión de servicios AWS a través de decisiones de negocio, no de teoría. |
| **Innovación técnica** | Demostrar **LangGraph** como motor de coordinación, estado compartido y revisiones cruzadas. |
| **Impacto en portafolio** | Una demo de alta recordación, reutilizable para la comunidad y el Club de IA. |

### Pitch de 30 segundos

> *"Cloud Crew AI es una oficina 2D de agentes especializados que colaboran para diseñar soluciones sobre AWS. Cada personaje representa un área real de trabajo —backend, datos, seguridad, costos, redes— coordinada por Leslie, la orquestadora. No son servicios de AWS personificados: son expertos que deciden qué servicios convienen, por qué convienen y cómo se conectan para resolver el problema."*

---

## 3. El equipo de agentes (la "crew")

El equipo está nombrado en honor a pioneros de la computación. El nombre refuerza el dominio de cada especialista y aporta un gancho educativo para el público del evento.

### Leslie — Orquestadora (líder)
*En honor a Leslie Lamport, pionero de los sistemas distribuidos.*

Recibe el reto del usuario, hace el **triage** de requisitos y restricciones (costo, seguridad, latencia, escala), reparte subtareas a los especialistas, modera el debate y **consolida** la decisión final en un plan integral coherente.

### Alan — Cómputo
*En honor a Alan Turing.*

Define APIs, lógica de backend, modelo de ejecución y estrategia de escalabilidad.
**Servicios típicos:** AWS Lambda, ECS, Fargate, API Gateway, App Runner.

### Edgar — Datos
*En honor a Edgar F. Codd, creador del modelo relacional.*

Estructura bases de datos, almacenamiento de archivos, caché y modelado de información.
**Servicios típicos:** Amazon S3, RDS, Aurora, DynamoDB, ElastiCache.

### Hedy — Seguridad
*En honor a Hedy Lamarr, inventora del salto de frecuencia.*

Protege accesos, gestiona secretos, identidades y políticas de mínimo privilegio.
**Servicios típicos:** IAM, Cognito, KMS, Secrets Manager, WAF.

### Grace — Monitoreo y Costos
*En honor a Grace Hopper.*

Evalúa observabilidad, presupuestos y optimización financiera del diseño. Es la voz que cuestiona el gasto.
**Servicios típicos:** CloudWatch, AWS Budgets, Cost Explorer, X-Ray.

### Vint — Redes
*En honor a Vint Cerf, co-creador de TCP/IP.*

Diseña la conectividad, la topología de red privada, la mensajería y los eventos.
**Servicios típicos:** VPC, EventBridge, SQS, SNS, CloudFront.

> **Nota de diseño:** Los personajes tendrán una estética pixel-art minimalista y amigable, con un color distintivo por estación de trabajo. Cada nombre se muestra con un micro-tooltip "¿sabías que…?" sobre el pionero que lo inspira.

---

## 4. Experiencia y flujo de la demo

El flujo se divide en **5 etapas secuenciales**, todas visibles para el público:

1. **Entrada del reto.** El visitante introduce una necesidad real.
   *Ej.: "Subir documentos, procesarlos con IA y atender picos de usuarios sin gastar de más."*

2. **Triage de Leslie.** La orquestadora identifica requisitos y restricciones críticas (costo, seguridad, velocidad, escala) y arma el plan de trabajo.

3. **Trabajo distribuido.** Se reparten las subtareas. En la interfaz 2D, cada agente se desplaza a su estación y muestra su progreso en vivo.

4. **Debate y revisión cruzada.** Los agentes cuestionan constructivamente las propuestas del resto.
   *Ej.: Alan propone ECS/Fargate; Grace sugiere Lambda para cargas variables y justifica el ahorro.*

5. **Consolidación.** Leslie unifica las respuestas en un plan integral, con diagrama de arquitectura y justificación servicio por servicio.

```
INPUT → [LESLIE: triage] → [ALAN | EDGAR | HEDY | GRACE | VINT] → [REVIEW cruzado] → [LESLIE: consolidación] → OUTPUT
```

---

## 5. Arquitectura técnica y MVP

Stack ágil con un alcance de MVP controlado para garantizar una demo sólida el día del evento.

| Capa | Tecnología | Razón |
|---|---|---|
| **Estilo** | Feature + Clean Architecture (back y front) | Dominio de la crew portable e independiente de frameworks. |
| **Frontend** | React + Vite + Tailwind CSS | Panel visual interactivo de las estaciones; arranque rápido. |
| **Tiempo real** | SSE (Server-Sent Events) | Empujar el progreso de cada agente al canvas en vivo, simple y reconectable. |
| **Backend** | Python + FastAPI | Ligero, asíncrono y nativo para integraciones de IA. |
| **Orquestación** | LangGraph + LangChain | Fan-out real, estado compartido y revisiones cruzadas. |
| **LLM** | Puerto `LLMProvider` + adaptadores | Anthropic, OpenAI, DeepSeek o Bedrock intercambiables por config. |
| **Conocimiento AWS** | Catálogo curado → RAG | Fuente de verdad para evitar alucinaciones; RAG enchufable después. |
| **Persistencia** | En memoria → PostgreSQL | Detrás de un puerto; historial de sesiones y arquitecturas. |
| **Despliegue** | AWS | Coherente con el tema del evento. |

> El detalle de arquitectura, contratos de agentes, esquema de estado y estructura de carpetas vive en **[`docs/arquitectura_tecnica.md`](./arquitectura_tecnica.md)**.

---

## 6. Plan de construcción

| Fase / Entregable clave | Prioridad |
|---|---|
| **1. Concepto visual** — Sprites de personajes, diseño de la oficina 2D y paleta por estación. | Alta |
| **2. Demo estática** — Flujo mockeado con respuestas e interfaz simulada (sin LLM). | Alta |
| **3. LangGraph real** — Integración de agentes con prompts y memoria de estado. | Alta |
| **4. Interacciones 2D** — Animaciones cortas, movimiento y estados de análisis. | Media |
| **5. Despliegue** — Persistencia en PostgreSQL y publicación en AWS. | Media |

### Definición de "listo" del MVP (Demo Day)

- [ ] El usuario escribe un reto y ve a Leslie hacer triage.
- [ ] Al menos 3 agentes producen propuestas reales con LLM.
- [ ] Ocurre al menos **un debate visible** con un trade-off explicado.
- [ ] Se genera un plan final con diagrama y justificación por servicio.
- [ ] La demo corre de punta a punta en menos de **2 minutos**.

---

## 7. Métricas de éxito

| Métrica | Meta en el evento |
|---|---|
| Retos completados de punta a punta sin error | ≥ 95% |
| Tiempo de respuesta del flujo completo | < 90 s |
| Debates con trade-off explícito por sesión | ≥ 1 |
| Costo por sesión (tokens LLM) | Controlado y medible |
| "Wow factor" / interés del público | Cualitativo, vía feedback |

---

## 8. Riesgos y mitigaciones

| Riesgo | Impacto | Mitigación |
|---|---|---|
| Latencia de los LLM rompe el ritmo de la demo | Alto | Streaming de tokens + estados intermedios animados; respuestas mockeadas como fallback en vivo. |
| Costo de tokens se dispara | Medio | Límite de tokens por sesión; modelo más barato para agentes secundarios; caché de retos comunes. |
| El debate suena artificial o forzado | Medio | Prompts con criterios objetivos y trade-offs reales; revisión cruzada estructurada, no decorativa. |
| Falla de red/AWS el día del evento | Alto | Modo offline con demo pregrabada/mockeada conmutable con un clic. |
| Alcance se infla antes del evento | Alto | Congelar el MVP en las fases de prioridad Alta; el resto es "nice to have". |

---

## 9. Glosario rápido

- **Agente:** Especialista de IA con un rol, prompt y herramientas propias.
- **Orquestador (Leslie):** Coordina el flujo y consolida la decisión final.
- **Revisión cruzada:** Un agente evalúa la propuesta de otro antes de consolidar.
- **Estado compartido:** Información común que todos los agentes leen y actualizan durante la sesión (gestionado por LangGraph).
- **Trade-off:** Compensación entre dos buenas opciones (p. ej., costo vs. rendimiento).

---

*Cloud Crew AI — Propuesta de proyecto · v3.0*
