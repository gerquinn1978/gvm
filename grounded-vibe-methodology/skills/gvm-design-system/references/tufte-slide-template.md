# Tufte Slide Template (Presentations)

Self-contained HTML slide deck for `/gvm-doc-write` presentations. Uses CSS-based slide separation with keyboard navigation and print support. Apply Tufte & Few principles (data-ink ratio, no chartjunk, right-aligned numbers, minimal decoration).

**Load this file only when writing a presentation.** It is self-contained — the slide deck does NOT require `tufte-html-reference.md` as well. Slides have their own layout optimised for projection.

## HTML Structure

```html
<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{Presentation Title}</title>
  <!-- Slide CSS below -->
</head>
<body>
  <div class="deck">

    <section class="slide title-slide">
      <div class="slide-content">
        <h1>{Presentation Title}</h1>
        <p class="subtitle">{Subtitle or Date}</p>
        <p class="author">{Author}</p>
      </div>
      <aside class="notes">Presenter notes here — hidden by default, toggle with N key.</aside>
    </section>

    <section class="slide">
      <div class="slide-content">
        <h2>{Headline as a Sentence}</h2>
        <p>{Supporting content — one idea per slide.}</p>
      </div>
      <aside class="notes">Notes for this slide.</aside>
    </section>

    <section class="slide">
      <div class="slide-content">
        <h2>{Data Slide Headline — States the "So What?"}</h2>
        <!-- Data visualisation, table, or chart here -->
      </div>
    </section>

    <section class="slide image-slide" style="background-image: url('path/to/image.jpg');">
      <div class="slide-content overlay">
        <h2>{Headline Over Image}</h2>
      </div>
    </section>

  </div>

  <div class="slide-counter">
    <span class="current-slide">1</span> / <span class="total-slides">4</span>
  </div>

  <!-- Navigation and counter script below -->
</body>
</html>
```

## Slide CSS

```css
/* === Reset & Base === */
*, *::before, *::after { box-sizing: border-box; margin: 0; padding: 0; }

body {
  font-family: "et-book", "Palatino Linotype", "Book Antiqua", Palatino, serif;
  font-size: 1.4rem;
  line-height: 1.5;
  color: #111;
  background: #fffff8;
  overflow: hidden;
}

/* === Deck Layout === */
.deck {
  width: 100vw;
  height: 100vh;
  position: relative;
}

.slide {
  width: 100vw;
  height: 100vh;
  display: none;
  align-items: center;
  justify-content: center;
  padding: 8vh 12vw;
  background: #fffff8;
  position: absolute;
  top: 0;
  left: 0;
}

.slide.active {
  display: flex;
}

.slide-content {
  max-width: 900px;
  width: 100%;
}

/* === Title Slide === */
.title-slide {
  text-align: center;
  flex-direction: column;
}

.title-slide h1 {
  font-size: 3rem;
  font-weight: 400;
  line-height: 1.2;
  margin-bottom: 1rem;
  color: #111;
}

.title-slide .subtitle {
  font-size: 1.4rem;
  font-style: italic;
  color: #555;
  margin-bottom: 0.5rem;
}

.title-slide .author {
  font-size: 1.1rem;
  color: #777;
}

/* === Content Slides === */
.slide h2 {
  font-size: 2rem;
  font-weight: 400;
  line-height: 1.3;
  margin-bottom: 1.5rem;
  color: #111;
}

.slide p {
  font-size: 1.4rem;
  line-height: 1.6;
  margin-bottom: 1rem;
  max-width: 38em;
}

.slide ul, .slide ol {
  font-size: 1.3rem;
  line-height: 1.6;
  margin-left: 1.5rem;
  margin-bottom: 1rem;
}

.slide li {
  margin-bottom: 0.5rem;
}

/* === Image Slides === */
.image-slide {
  background-size: cover;
  background-position: center;
  background-repeat: no-repeat;
}

.image-slide .overlay {
  background: rgba(0, 0, 0, 0.55);
  padding: 2rem 3rem;
  border-radius: 4px;
}

.image-slide .overlay h2 {
  color: #fff;
  text-shadow: 0 1px 3px rgba(0,0,0,0.3);
}

/* === Data/Table Slides === */
.slide table {
  border-collapse: collapse;
  width: 100%;
  font-size: 1.1rem;
  margin-top: 1rem;
}

.slide th {
  text-align: left;
  font-weight: 600;
  border-bottom: 2px solid #111;
  padding: 0.5rem 1rem 0.5rem 0;
}

.slide td {
  padding: 0.4rem 1rem 0.4rem 0;
  border-bottom: 1px solid #ddd;
}

.slide td.num, .slide th.num {
  text-align: right;
  font-variant-numeric: tabular-nums;
}

/* === Presenter Notes === */
.notes {
  display: none;
  position: fixed;
  bottom: 0;
  left: 0;
  right: 0;
  background: #333;
  color: #eee;
  padding: 1.5rem 12vw;
  font-size: 1rem;
  line-height: 1.5;
  max-height: 30vh;
  overflow-y: auto;
  z-index: 100;
}

body.show-notes .notes {
  display: block;
}

body.show-notes .slide {
  height: 70vh;
}

/* === Slide Counter === */
.slide-counter {
  position: fixed;
  bottom: 1rem;
  right: 2rem;
  font-size: 0.9rem;
  color: #999;
  z-index: 50;
}

/* === Print === */
@media print {
  body { overflow: visible; }
  .deck { width: auto; height: auto; position: static; }
  .slide {
    display: flex !important;
    position: static;
    width: 100%;
    height: auto;
    min-height: 100vh;
    page-break-after: always;
    page-break-inside: avoid;
  }
  .slide-counter, .notes { display: none !important; }
}

/* ── GVM Attribution (per shared rule 24) ── */
.gvm-attribution {
  font-size: 0.7rem;
  color: #bbb;
  font-style: italic;
  text-align: center;
  margin: 0;
  padding: 0.5rem 0;
}
```

**Attribution footer (shared rule 24):** include the attribution on the final slide OR as a persistent element in the slide footer. For the final slide approach, add as the last element of the closing slide's content:

```html
<p class="gvm-attribution">Developed using the Grounded Vibe Methodology</p>
```

Do not mention the GVM source repository URL.

## Branding Override (Optional)

When a `branding/branding.md` file exists, apply its identity elements as CSS overrides. The branding file controls headers and accent colours only — body typography and layout remain under design system control.

```css
.title-slide h1 { color: var(--brand-header-color, #111); }
.title-slide { background: var(--brand-header-bg, #fffff8); }
.slide h2 { color: var(--brand-header-color, #111); }
a { color: var(--brand-accent, #a00000); }

h1, h2 { font-family: var(--brand-heading-font, inherit); }

.title-slide::before {
  content: '';
  display: block;
  width: 120px;
  height: 60px;
  background-size: contain;
  background-repeat: no-repeat;
  margin: 0 auto 2rem;
}
```

## Navigation Script

```javascript
(function() {
  const slides = document.querySelectorAll('.slide');
  const currentEl = document.querySelector('.current-slide');
  const totalEl = document.querySelector('.total-slides');
  let current = 0;

  if (totalEl) totalEl.textContent = slides.length;

  function show(n) {
    slides.forEach(s => s.classList.remove('active'));
    current = Math.max(0, Math.min(n, slides.length - 1));
    slides[current].classList.add('active');
    if (currentEl) currentEl.textContent = current + 1;
  }

  show(0);

  document.addEventListener('keydown', function(e) {
    if (e.key === 'ArrowRight' || e.key === ' ' || e.key === 'ArrowDown') {
      e.preventDefault();
      show(current + 1);
    } else if (e.key === 'ArrowLeft' || e.key === 'ArrowUp') {
      e.preventDefault();
      show(current - 1);
    } else if (e.key === 'n' || e.key === 'N') {
      document.body.classList.toggle('show-notes');
    } else if (e.key === 'Home') {
      show(0);
    } else if (e.key === 'End') {
      show(slides.length - 1);
    }
  });

  let touchStartX = 0;
  document.addEventListener('touchstart', function(e) {
    touchStartX = e.changedTouches[0].screenX;
  });
  document.addEventListener('touchend', function(e) {
    const diff = e.changedTouches[0].screenX - touchStartX;
    if (Math.abs(diff) > 50) {
      diff < 0 ? show(current + 1) : show(current - 1);
    }
  });
})();
```

## Keyboard Shortcuts

| Key | Action |
|---|---|
| `→` / `↓` / `Space` | Next slide |
| `←` / `↑` | Previous slide |
| `N` | Toggle presenter notes |
| `Home` | First slide |
| `End` | Last slide |

Swipe left/right on touch devices.
