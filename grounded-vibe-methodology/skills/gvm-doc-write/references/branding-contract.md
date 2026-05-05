# Branding File Contract

## Purpose

The branding file lets projects apply organisational identity to documents produced by `/gvm-doc-write` without overriding the design system's typographic and layout foundations. Branding controls the header; Tufte and Few control the body.

## File Location

```
{project-root}/branding/branding.md
```

This file is optional. If it does not exist, all documents use the default design system styling. The skill never asks the user to create it and never fails if it is missing.

## File Format

```markdown
# Branding

## Logo
- **path:** `branding/logo.png` (or .svg)
- **placement:** title-slide (presentations), document header (other types)
- **max-width:** 120px

## Colours
- **header-background:** `#1a3c5e`
- **header-text:** `#ffffff`
- **accent:** `#2980b9` (links, emphasis borders, highlights)

## Fonts
- **heading-font:** `"Helvetica Neue", "Arial", sans-serif`

## Organisation
- **name:** Acme Corp
- **tagline:** (optional)
```

## What Branding Controls

| Element | Branding | Default (no branding file) |
|---|---|---|
| Logo on title slides / headers | From branding file | None |
| Header / title slide background colour | `header-background` | `#fffff8` |
| Header / title slide text colour | `header-text` | `#111` |
| Heading font family | `heading-font` | `et-book` (design system default) |
| Link and accent colour | `accent` | `#a00000` |
| Organisation name in footers | `name` | None |

## What Branding Does NOT Control

These remain under design system authority (Tufte/Few principles):

| Element | Governed By | Rationale |
|---|---|---|
| Body text font | Design system (`et-book` or system serif) | Tufte: readability over brand consistency for body text |
| Body text colour | Design system (`#111`) | Contrast ratio for readability |
| Line height, measure, margins | Design system | Bringhurst: typographic scale and readable line length |
| Table design | Design system | Few: data-ink ratio, right-aligned numbers |
| Chart/data visualisation colours | Design system | Tufte/Few: colour encodes data, not brand |
| Grid and layout | Design system | Muller-Brockmann: modular grid |
| Font sizes and scale | Design system | Bringhurst: harmonic typographic scale |

## CSS Variable Mapping

When the branding file is loaded, its values are emitted as CSS custom properties on the `<html>` element:

```css
:root {
  --brand-header-bg: #1a3c5e;
  --brand-header-color: #ffffff;
  --brand-accent: #2980b9;
  --brand-heading-font: "Helvetica Neue", "Arial", sans-serif;
}
```

These variables are referenced by the slide template and document templates with fallback defaults:

```css
.title-slide { background: var(--brand-header-bg, #fffff8); }
.title-slide h1 { color: var(--brand-header-color, #111); }
h1, h2 { font-family: var(--brand-heading-font, inherit); }
a { color: var(--brand-accent, #a00000); }
```

## Validation

When loading the branding file, the skill checks:

1. Logo path exists (if specified) — warn if missing, continue without logo
2. Colour values are valid CSS colours — warn if invalid, use defaults
3. Font family is a valid CSS font-family string — warn if invalid, use defaults

No validation failure prevents document creation. Branding is additive; its absence or invalidity is not an error.
