# Charter Templates — `/gvm-explore-test`

Pick a starting template that matches the project under test, copy the YAML
block into your charter buffer, and edit. Templates are starting points,
not mandates — change the mission, timebox, or tour freely. The validator
(`_charter.load`) enforces the schema (ADR-202); these templates exist to
shorten ramp-up, not to constrain the session.

Each block omits two fields you fill in for every session:

- `target` — list of URLs, file paths, or invocations the session probes.
- `runner` — your handle (e.g. `gerard`). Use `unassigned` only if you
  intend the ET-7 deferred-runner branch.

The skill assigns `session_id` automatically (next free `explore-NNN`).

Allowed `tour` values: `feature`, `data`, `money`, `interruption`,
`configuration`. Allowed `timebox_minutes`: `30`, `60`, `90`.

---

## data-analysis skill

Use when the system under test ingests, transforms, and renders datasets —
the path from raw input to a final report or dashboard. The `data` tour
focuses on the pipeline's behaviour against realistic input.

```yaml
mission: Run the skill against a real dataset; verify every stage from ingestion through rendering surfaces honestly.
timebox_minutes: 60
tour: data
```

## CRUD app

Use when the product is a forms-and-records application. The `feature`
tour walks each primary user journey end to end.

```yaml
mission: Walk every primary user journey; verify each form's create / read / update / delete reaches expected output.
timebox_minutes: 60
tour: feature
```

## agent-based system

Use when the product orchestrates multiple agents or LLM-driven steps.
The `data` tour with a longer timebox accommodates inspecting handoffs.

```yaml
mission: Inspect each agent's behaviour under realistic input; verify the orchestration handoffs preserve context.
timebox_minutes: 90
tour: data
```

## content pipeline

Use when the product transforms documents through staged steps (parse,
normalise, render). The `data` tour focuses on each stage's output.

```yaml
mission: Run a sample document end-to-end; verify each transform stage's output integrity.
timebox_minutes: 60
tour: data
```

## billing/payment surface

Use when the code path under test touches money — pricing, refunds,
currency conversion, partial-success paths. The `money` tour names this
explicitly.

```yaml
mission: Probe price-sensitive code paths; verify rounding, currency, refund, partial-success.
timebox_minutes: 60
tour: money
```

## network-degraded scenario

Use when the product must behave defensibly under offline / slow / retry
conditions. The `interruption` tour with a 30-minute timebox suits a
focused fault-injection session.

```yaml
mission: Inject realistic interruptions (offline, slow, retry); verify the product degrades visibly, not silently.
timebox_minutes: 30
tour: interruption
```

---

Add new templates by editing this file. Keep the same block structure
(one fenced YAML block per project type, with `mission`, `timebox_minutes`,
`tour`) so the skill's library reader continues to work.
