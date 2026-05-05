## Gregor Hohpe & Bobby Woolf — Integration Patterns

**Sources:**
- Gregor Hohpe & Bobby Woolf, *Enterprise Integration Patterns*, Addison-Wesley (2003)
- Gregor Hohpe, *The Software Architect Elevator*, O'Reilly (2020)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Gregor Hohpe | 5 | 5 | 4 | 5 | 4 | **4.6** | **Canonical** |
| Bobby Woolf | 4 | 3 | 2 | 4 | 2 | **3.0** | **Recognised** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Hohpe & Woolf, *Enterprise Integration Patterns* | 5 | 5 | 3 | 5 | **4.5** | **Canonical** |
| Hohpe, *The Software Architect Elevator* | 3 | 3 | 5 | 3 | **3.5** | **Established** |

**Evidence (Hohpe):** Authority — co-created enterprise integration pattern vocabulary. Adoption — patterns in Apache Camel, Spring Integration, MuleSoft. *EIP* Depth — 65 patterns at implementation level.

**Evidence (Woolf):** Authority — co-author of EIP. Woolf Publication=3 reflects that his sole major credit is *Enterprise Integration Patterns* as co-author — no independent body of published work. Hohpe Publication=5 reflects EIP plus conference talks, blog posts, and *The Software Architect Elevator*.

**Activation signals:** Service integration, message passing, agent orchestration, multiple systems communicating, event-driven architecture

**Key techniques to apply:**

- **Message channel** (Ch. 3): How do components communicate? Point-to-point, publish-subscribe, or request-reply?
- **Message router** (Ch. 7): How are messages directed to the right handler? Content-based routing, recipient list, splitter/aggregator.
- **Orchestration vs choreography**: Orchestration — a central controller directs the workflow (easier to reason about, single point of failure). Choreography — each component reacts to events independently (more resilient, harder to debug).
- **Idempotent receiver** (Ch. 10): In async systems, messages may be delivered more than once. Handlers must be safe to re-execute.
- **Process manager** (Ch. 7): For long-running processes (like a 15-20 minute analysis run), a process manager tracks state and handles failures.

**When specifying agent/service communication:**
- Define the communication pattern (sync HTTP, async queue, WebSocket, SSE)
- Specify message formats and contracts
- Define the orchestration model: who decides what happens next?
- Specify failure handling: what happens when a component is slow or unresponsive?
- Define idempotency requirements for operations that may be retried
