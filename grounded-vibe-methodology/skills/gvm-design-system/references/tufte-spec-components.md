# Tufte Spec Components

CSS for tech-spec-specific HTML components: ADR (Architecture Decision Record) blocks and component detail disclosures. Used by `/gvm-tech-spec`.

**Load together with `tufte-html-reference.md`** — the core file provides base layout and typography; this file adds spec-specific components. Append these rules to the `<style>` block in your HTML after the core CSS.

## CSS

```css
/* ── ADR (Architecture Decision Record) ── */
details.adr {
  background: #f7f7f0;
  border-left: 3px solid #669;
  padding: 0;
  margin: 1rem 0 1.2rem;
  max-width: 860px;
}

details.adr summary {
  padding: 0.8rem 1rem;
  cursor: pointer;
  list-style: none;
}

details.adr summary::-webkit-details-marker { display: none; }

details.adr summary::before {
  content: '\25B8 ';
  font-size: 0.85rem;
  color: #999;
}

details.adr[open] summary::before {
  content: '\25BE ';
}

.adr-id {
  font-size: 0.75rem;
  font-weight: 600;
  color: #888;
  text-transform: uppercase;
  letter-spacing: 0.05em;
  margin-right: 0.5rem;
}

.adr-title {
  font-weight: 600;
  color: #333;
}

.adr-status {
  font-size: 0.75rem;
  color: #999;
  font-style: italic;
  margin-left: 0.5rem;
}

.adr-body {
  padding: 0 1rem 0.8rem;
  border-top: 1px solid #e0e0e0;
}

.adr-body h4 {
  font-size: 0.85rem;
  font-weight: 600;
  color: #666;
  margin: 0.6rem 0 0.3rem;
}

/* ── Component Detail Disclosure ── */
details.component-detail {
  background: #fafaf4;
  border-left: 3px solid #999;
  padding: 0;
  margin: 1rem 0 1.2rem;
  max-width: 860px;
}

details.component-detail summary {
  padding: 0.6rem 1rem;
  cursor: pointer;
  font-weight: 600;
  color: #333;
  list-style: none;
}

details.component-detail summary::-webkit-details-marker { display: none; }

details.component-detail summary::before {
  content: '\25B8 ';
  font-size: 0.85rem;
  color: #999;
}

details.component-detail[open] summary::before {
  content: '\25BE ';
}
```

## ADR HTML

```html
<details class="adr" id="adr-003">
  <summary>
    <span class="adr-id">ADR-003</span>
    <span class="adr-title">Use event sourcing for audit log</span>
    <span class="adr-status">Accepted</span>
  </summary>
  <div class="adr-body">
    <h4>Context</h4>
    <p>Regulatory requirement REQ-017 mandates immutable audit records...</p>
    <h4>Decision</h4>
    <p>Store all state-changing operations as events in an append-only log...</p>
    <h4>Consequences</h4>
    <p>Replay-based debugging possible. Higher write volume. Reconciliation complexity increases.</p>
  </div>
</details>
```

## Component Detail HTML

```html
<details class="component-detail" id="comp-auth-service">
  <summary>Auth Service</summary>
  <div>
    <p>Handles authentication via OAuth2 against the identity provider...</p>
    <p><strong>Interfaces:</strong> POST /auth/token, POST /auth/refresh</p>
  </div>
</details>
```
