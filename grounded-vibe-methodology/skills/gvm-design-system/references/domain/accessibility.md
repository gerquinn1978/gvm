## Heydon Pickering — Accessibility

**Sources:**
- Heydon Pickering, *Inclusive Design Patterns*, Smashing Magazine (2016)
- Heydon Pickering, *Inclusive Components*, Smashing Magazine (2019)
- W3C Web Content Accessibility Guidelines (WCAG) 2.1 (w3.org/TR/WCAG21/)
- Deque University, axe-core documentation (dequeuniversity.com)

**Expert scores:**

| Expert | A | P | B | Ad | C | Avg | Tier |
|---|---|---|---|---|---|---|---|
| Heydon Pickering | 4 | 3 | 3 | 4 | 4 | **3.6** | **Established** |
| W3C WCAG 2.1 | 5 | 5 | 4 | 5 | 4 | **4.6** | **Canonical** |
| Deque/axe-core | 4 | 3 | 3 | 5 | 5 | **4.0** | **Established** |

| Work | S | De | C | I | Avg | Tier |
|---|---|---|---|---|---|---|
| Pickering, *Inclusive Design Patterns* | 4 | 4 | 3 | 3 | **3.5** | **Established** |
| Pickering, *Inclusive Components* | 5 | 4 | 4 | 3 | **4.0** | **Established** |
| W3C, *WCAG 2.1* | 5 | 4 | 4 | 5 | **4.5** | **Canonical** |
| Deque, axe-core docs | 5 | 3 | 5 | 4 | **4.25** | **Established** |

**Evidence (Pickering):** Authority — leading accessible component design practitioner. Adoption — recommended reading in Google web.dev accessibility resources and UK Government Digital Service accessibility community; *Inclusive Components* widely referenced in accessible component design. *Inclusive Components* Specificity — complete implementation per component.

**Evidence (W3C WCAG 2.1):** Authority — normative legal standard. Adoption — mandatory in dozens of countries. Work Specificity — 78 testable success criteria.

**Evidence (Deque/axe-core):** Adoption — embedded in Chrome Lighthouse, Edge DevTools. Currency — actively maintained.

**Activation signals:** Frontend UI, user-facing forms, interactive components, dynamic content updates, navigation, any visual status indicators

**Key principles to apply:**

- **Semantic HTML is the foundation** (Pickering, Ch. 1): Use `<button>` not `<div onClick>`. Use `<nav>`, `<main>`, `<section>`, `<h1>` — not divs with ARIA roles. Semantic elements provide keyboard handling, screen reader support, and focus management for free. ARIA is a repair mechanism for when semantics are impossible.
- **Every interactive element has an accessible name** (Pickering, *Inclusive Components*, Ch. 2): Buttons with only icons need `aria-label`. Inputs need `<label>` elements or `aria-label`. Toggle switches need `aria-checked` and an associated label. The accessible name is what screen readers announce.
- **Colour is never the sole indicator** (WCAG SC 1.4.1): Status communicated by colour must also be communicated by text, icon, or pattern. A red error border needs an error message. A green success dot needs a "Complete" label.
- **Dynamic content needs `aria-live`** (Pickering, *Inclusive Components*, Ch. 7): When content updates without a page reload (WebSocket events, AJAX, SPA route changes), screen readers don't know unless told. Use `aria-live="polite"` for status updates, `aria-live="assertive"` for urgent interruptions (agent questions needing answers).
- **Focus management on state changes** (WCAG SC 2.4.3): When a dialog opens, focus moves into it. When it closes, focus returns to the trigger. When a SPA navigates, focus moves to the new page content. When a form submits and shows errors, focus moves to the first error.
- **Skip navigation** (WCAG SC 2.4.1): Provide a "Skip to main content" link as the first focusable element. Keyboard users should not have to tab through the full navigation on every page.
- **Contrast ratios** (WCAG SC 1.4.3, 1.4.11): Normal text requires 4.5:1 against its background. Large text (18pt+) requires 3:1. Graphical elements and UI components require 3:1.
- **Form errors must be programmatically associated** (WCAG SC 1.3.1, 3.3.1): Use `aria-invalid="true"` on the input and `aria-describedby` pointing to the error message's `id`. Screen readers then announce the error when the user focuses the field.

**When specifying UI:**
- Require semantic HTML elements for all interactive controls
- Specify accessible names for icon-only buttons and unlabelled inputs
- Define `aria-live` regions for dynamic content
- Specify focus management for dialogs, route changes, and form errors
- Define colour contrast requirements (reference specific WCAG levels)
- Require skip navigation on pages with repeated navigation blocks

**When reviewing code:**
- Check every `<button>`, `<input>`, and interactive element has an accessible name
- Check every colour-only indicator has a text/icon alternative
- Check dynamic content regions have `aria-live`
- Check form errors use `aria-invalid` and `aria-describedby`
- Check focus management on route changes, dialog open/close, error display
- Verify contrast ratios for status colours against their backgrounds
- Check for `:focus-visible` styles when `outline-none` is used
