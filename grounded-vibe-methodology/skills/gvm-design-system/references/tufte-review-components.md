# Tufte Review Components

CSS for review-specific HTML components: verdict box, score card, issue blocks, criterion rows. Used by `/gvm-code-review`, `/gvm-doc-review`, `/gvm-design-review`, and `/gvm-test`.

**Load together with `tufte-html-reference.md`** — the core file provides base layout and typography; this file adds review-specific components. Append these rules to the `<style>` block in your HTML after the core CSS.

## CSS

```css
/* ── Verdict Box (all review skills) ── */
.verdict {
  border: 2px solid #333;
  padding: 1.2rem 1.5rem;
  margin: 2rem 0;
  max-width: 640px;
}

.verdict-label {
  font-size: 0.75rem;
  font-weight: 600;
  text-transform: uppercase;
  letter-spacing: 0.08em;
  color: #888;
  margin-bottom: 0.3rem;
}

.verdict-text {
  font-size: 1.3rem;
  font-weight: 400;
  color: #111;
  margin-bottom: 0.4rem;
}

.verdict-basis {
  font-size: 0.88rem;
  color: #555;
  max-width: 640px;
}

.verdict.ready { border-color: #27ae60; background: #f0faf4; }
.verdict.ready .verdict-text { color: #27ae60; }

.verdict.caveats { border-color: #e67e22; background: #fef8f0; }
.verdict.caveats .verdict-text { color: #e67e22; }

.verdict.not-ready { border-color: #c0392b; background: #fdf0ef; }
.verdict.not-ready .verdict-text { color: #c0392b; }

/* ── Review Components (score card, issues, criteria) ── */
.score-card {
  background: #f7f7f0;
  border: 2px solid #333;
  padding: 1.5rem 2rem;
  margin: 2rem 0;
  max-width: 640px;
  text-align: center;
}

.overall-score {
  font-size: 2.4rem;
  font-weight: 400;
  color: #111;
  margin-bottom: 0.8rem;
}

.score-breakdown {
  display: flex;
  justify-content: space-around;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.score-item {
  font-size: 0.88rem;
  color: #555;
}

.issue {
  border-left: 3px solid;
  padding: 0.8rem 1rem;
  margin: 0.8rem 0;
  max-width: 640px;
}

.issue.critical {
  border-left-color: #c0392b;
  background: #fdf0ef;
}

.issue.important {
  border-left-color: #e67e22;
  background: #fef8f0;
}

.issue.minor {
  border-left-color: #7f8c8d;
  background: #f7f7f4;
}

.issue-title {
  font-weight: 600;
  color: #333;
  margin-bottom: 0.3rem;
}

.issue-detail {
  font-size: 0.92rem;
  color: #555;
  margin-bottom: 0.3rem;
}

.issue-location {
  font-size: 0.78rem;
  color: #999;
  font-style: italic;
}

.criterion {
  display: flex;
  align-items: baseline;
  gap: 0.8rem;
  margin: 0.6rem 0;
  max-width: 640px;
}

.criterion-name {
  font-weight: 600;
  color: #333;
  min-width: 160px;
}

.criterion-score {
  font-size: 0.85rem;
  font-weight: 600;
  min-width: 40px;
}

.criterion-score.high { color: #27ae60; }
.criterion-score.mid { color: #e67e22; }
.criterion-score.low { color: #c0392b; }

.criterion-note {
  font-size: 0.88rem;
  color: #666;
}
```

## Verdict Box HTML

Place the verdict before the score card:

```html
<div class="verdict ready">
  <div class="verdict-label">Verdict</div>
  <div class="verdict-text">Ready to proceed to /gvm-tech-spec</div>
  <p class="verdict-basis">No critical issues. Three important findings should be addressed but do not block progression.</p>
</div>
```

The verdict class (`ready`, `caveats`, `not-ready`) controls colour. Use the type-specific verdict language defined in `review-reference.md` for the verdict text.

## Score Card HTML

```html
<div class="score-card">
  <div class="overall-score">7.2 / 10</div>
  <div class="score-breakdown">
    <div class="score-item">Requirements: 8/10</div>
    <div class="score-item">Test Cases: 7/10</div>
    <div class="score-item">Specs: 6/10</div>
    <div class="score-item">Consistency: 8/10</div>
  </div>
</div>
```

## Issue Block HTML

```html
<div class="issue critical">
  <div class="issue-title">Missing acceptance criteria for REQ-042</div>
  <p class="issue-detail">The requirement states the goal but does not define observable success conditions. A tester cannot write a test case against this requirement as written.</p>
  <div class="issue-location">requirements/requirements.html §4.2</div>
</div>
```
