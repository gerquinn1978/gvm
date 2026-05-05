## Performance Engineering

### Brendan Gregg

**Source:** Brendan Gregg, *Systems Performance: Enterprise and the Cloud* (2nd ed.), Addison-Wesley (2020)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 5 | 5 | 4 | 5 | 5 | **Canonical** |

Evidence: Authority — inventor of flame graphs and USE Method; senior performance architect at Netflix; USENIX LISA Award. Publication — three books from Addison-Wesley/Prentice Hall. Adoption — flame graphs integrated in Linux perf, Chrome DevTools, every major APM platform; USE Method in Google SRE Book.

**Work score — *Systems Performance* (2nd ed.):**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 5 | 5 | 5 | 5 | **Canonical** |

Evidence: Specificity — every chapter grounded in specific tool invocations (perf, bpftrace, vmstat). Depth — 800+ pages covering kernel internals through application layer. Influence — cited in Google SRE Book, Netflix engineering docs, AWS/GCP performance guides.


**Activation signals:** performance requirements, response time targets, throughput targets, scalability concerns, database query performance, caching strategy, N+1 query patterns, load testing, resource utilisation

**Key principles:**
- **USE method** (Utilisation, Saturation, Errors) — for every resource, check utilisation (how busy), saturation (how queued), and errors. Identifies bottlenecks systematically rather than by guessing.
- **Latency is not average** — always measure percentiles (p50, p95, p99). An average of 50ms hides the fact that 1% of requests take 2 seconds.
- **Start with the workload, not the tools** — understand what the system is supposed to do before measuring how fast it does it. Performance requirements come from user expectations, not from benchmarks.
- **Drill down, not out** — when a bottleneck is found, drill into it rather than looking at other metrics. The first bottleneck found is usually the one that matters.

---

### Ilya Grigorik

**Source:** Ilya Grigorik, *High Performance Browser Networking*, O'Reilly (2013)

**Expert score:**
| Authority | Publication | Breadth | Adoption | Currency | Classification |
|-----------|-------------|---------|----------|----------|----------------|
| 4 | 4 | 3 | 4 | 3 | **Established** |

Evidence: Authority — Google web performance engineer, W3C Web Performance Working Group co-chair. Adoption — HPBN was the standard web performance reference during HTTP/2 transition; cited in Google Web Fundamentals and Lighthouse docs.

**Work score — *High Performance Browser Networking*:**
| Specificity | Depth | Currency | Influence | Classification |
|-------------|-------|----------|-----------|----------------|
| 4 | 4 | 2 | 4 | **Established** |

Evidence: Specificity — protocol-specific optimisation guidance for TCP, TLS, HTTP/2, WebSocket. Depth — goes below API surface into protocol mechanics. Currency — 2013 publication predates HTTP/3, QUIC, TLS 1.3, Core Web Vitals. Influence — shaped web performance engineering during HTTP/2 era.


**Activation signals:** web application performance, frontend loading speed, network latency, HTTP/2, WebSocket, caching headers, CDN strategy, bundle size, critical rendering path

**Key principles:**
- **Latency is the bottleneck, not bandwidth** — for most web applications, reducing round trips matters more than increasing throughput. Every HTTP request adds latency; reducing the number of requests has more impact than making each one faster.
- **Eliminate unnecessary requests** — every resource (script, stylesheet, image, API call) that the browser fetches adds latency. Audit what is loaded and remove what is not needed.
- **Cache aggressively, invalidate precisely** — set long cache lifetimes for static assets, use content hashing for cache busting. The fastest request is the one that never leaves the client.
- **Optimise the critical rendering path** — identify what must load before the user sees anything. Defer everything else. First meaningful paint is the metric that determines perceived performance.
