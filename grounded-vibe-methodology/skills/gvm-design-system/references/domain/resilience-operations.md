## Michael Nygard — Resilience & Operations

**Source:** Michael Nygard, *Release It! Design and Deploy Production-Ready Software* (2nd ed.), Pragmatic Bookshelf (2018)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Michael Nygard | 4 | 4 | 3 | 4 | 4 | **3.8** | **Established** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Nygard, *Release It!* 2nd ed | 5 | 4 | 4 | 4 | **4.25** | **Established** |

**Evidence:** Authority — originated circuit breaker, bulkhead, timeout as named patterns. Adoption — patterns in Netflix Hystrix, Resilience4j, Polly.

**Activation signals:** External API dependencies, long-running processes, graceful degradation requirements, deployment spec

**Key techniques to apply:**

- **Circuit breaker** (Ch. 5): When an external service fails repeatedly, stop calling it temporarily. Prevents cascade failures. Define thresholds (how many failures before opening?) and recovery (how long before trying again?).
- **Timeout** (Ch. 5): Every external call must have a timeout. "How long are we willing to wait?" is an architectural decision, not an implementation detail.
- **Bulkhead** (Ch. 5): Isolate failure domains. If the school data API is down, the real estate agent should not be affected.
- **Steady state** (Ch. 6): The system must clean up after itself. Logs rotate, caches expire, old data is purged. Define the steady-state strategy.
- **Handshaking** (Ch. 5): Services should be able to signal "I'm overloaded, slow down." Back-pressure mechanisms for rate-limited external APIs.

**When specifying resilient systems:**
- Define timeout values for each external dependency
- Specify circuit breaker thresholds and recovery strategies
- Define bulkhead boundaries: what can fail independently?
- Specify graceful degradation: what does the user see when a data source is down?
- Define health check and monitoring strategy
