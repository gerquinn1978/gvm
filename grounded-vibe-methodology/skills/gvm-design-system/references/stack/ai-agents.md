# AI Agent Orchestration

### Harrison Chase / LangChain Team — LangGraph
**Sources:**
- Harrison Chase, LangGraph official documentation (langchain-ai.github.io/langgraph/)
- LangGraph conceptual guides: "Why LangGraph?", "Human-in-the-loop", "Persistence"
- LangChain blog: agent architecture patterns, state management, streaming

> **Expert Score — Harrison Chase**
> Authority=4 · Publication=3 · Breadth=4 · Adoption=5 · Currency=5 → **4.2 — Established**
>
> | Work | Specificity | Depth | Currency | Influence | Avg | Tier |
> |---|---|---|---|---|---|---|
> | LangGraph docs | 5 | 4 | 5 | 4 | **4.5** | Canonical |
>
> Evidence: Authority — created LangChain/LangGraph. Adoption — 90,000+ GitHub stars.


**Key principles to apply in specs:**
- **Graph as the orchestration primitive**: Define the agent workflow as a directed graph with nodes (agent steps) and edges (transitions). Each node is a function that receives and returns state. This replaces custom state machines and task queue orchestration.
- **State schema**: Define a typed state object (TypedDict or Pydantic model) that flows through the graph. Every node reads from and writes to this shared state. The state schema IS the run data model.
- **Checkpointing for persistence**: LangGraph checkpoints graph state after each node completion. Use a PostgreSQL-backed checkpointer for durability. This gives resume (load last checkpoint, re-enter graph), cancel (stop execution, checkpoint preserved), and incremental persistence for free.
- **`interrupt()` for human-in-the-loop**: Call `interrupt()` within a node to pause execution and surface a question to the user. The graph suspends at that node while other parallel branches continue. When the user responds, the node resumes with the response. This is the key primitive for agent clarifying questions.
- **Parallel branches**: Define parallel branches for independent agent domains. LangGraph executes them concurrently. Synthesis node has edges from all domain nodes — it waits for all to complete (or fail/skip).
- **Streaming**: LangGraph streams state updates, node entries/exits, and LLM token-by-token output via callbacks. Wire these to WebSocket for real-time frontend updates.
- **Subgraphs for modularity**: Each domain agent can be its own subgraph with internal nodes (e.g., real estate agent: search areas → fetch listings → evaluate market). The parent graph composes subgraphs.

**When specifying agent orchestration:**
- Define the graph topology: which nodes, which edges, which branches are parallel
- Define the state schema: what data flows through the graph
- Identify interrupt points: where the agent needs user input
- Specify the checkpointer: PostgreSQL for production, memory for testing
- Define streaming events: what the frontend receives in real-time

### LangSmith — Observability & Tracing
**Source:** LangSmith official documentation (docs.smith.langchain.com)

LangSmith is a commercial product, not an expert or standards body. Docs are scored as a work under the Harrison Chase / LangChain Team entry above.

**Key principles to apply in specs:**
- **Trace everything**: Every LLM call, tool invocation, retrieval, and agent decision is automatically traced. Define which traces map to user-facing transparency (PL-14) vs developer debugging.
- **Run evaluation**: Define evaluation criteria for agent outputs — are the gathered data points sourced correctly? Are rankings defensible? LangSmith enables systematic evaluation of agent quality.
- **Feedback collection**: Wire user interjections (PL-16) and question responses (PL-15) back to LangSmith as feedback for agent improvement.
- **Cost tracking**: LangSmith tracks token usage per run. Essential for the token cost management constraint.
