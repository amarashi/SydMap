# Design Language: LAYRS: Amsterdam

> Extracted from `https://stop-token.com/lab/amsterdam/` on October 13, 2026
> 166 elements analyzed

This document describes the complete design language of the website. It is structured for AI/LLM consumption — use it to faithfully recreate the visual design in any framework.

## Color Palette

### Primary Colors

| Role | Hex | RGB | HSL | Usage Count |
|------|-----|-----|-----|-------------|
| Primary | `#ec0000` | rgb(236, 0, 0) | hsl(0, 100%, 46%) | 1 |
| Secondary | `#d97a2b` | rgb(217, 122, 43) | hsl(27, 70%, 51%) | 1 |
| Accent | `#e5b13a` | rgb(229, 177, 58) | hsl(42, 77%, 56%) | 1 |

### Tonal Ramps

Generated in OKLCH from each role colour, so the steps are perceptually even. The site's own colour keeps its position in the ladder.

| Role | 50 | 100 | 200 | 300 | 400 | 500 | 600 | 700 | 800 | 900 | 950 |
|------|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|-----|
| primary | `#ffcfbc` | `#ffbeaa` | `#ffa691` | `#ff826d` | `#ff4f3e` | **`#ec0000`** | `#d10000` | `#af0000` | `#940000` | `#7c0000` | `#4c0000` |
| secondary | `#ffe7bd` | `#ffd9ab` | `#ffc692` | `#feaa6e` | **`#d97a2b`** | `#c26608` | `#a75100` | `#8a3d00` | `#743000` | `#602400` | `#391000` |
| accent | `#fff1b3` | `#ffe5a0` | `#fad485` | **`#e5b13a`** | `#c8971e` | `#aa7800` | `#916200` | `#774e00` | `#633e00` | `#513100` | `#301a00` |
| neutral | `#f2f6f9` | `#e6eaed` | `#d5dadd` | `#bcc1c5` | `#9ba0a5` | `#7d8387` | **`#5d6266`** | `#53575b` | `#43474a` | `#36393c` | `#1d1f21` |

### Semantic Pairs

| Role | Background | Foreground | Contrast | Level |
|------|------------|------------|----------|-------|
| `surface.page` | `#e4e8ea` | `#000000` | 17.03:1 | AAA |
| `surface.raised` | `#ffffff` | `#000000` | 21:1 | AAA |
| `action.primary` | `#ec0000` | `#ffffff` | 4.6:1 | AA |
| `action.secondary` | `#d97a2b` | `#000000` | 6.77:1 | AA |
| `action.accent` | `#e5b13a` | `#000000` | 10.68:1 | AAA |

### Dominance

Share of painted background area — what the page looks like, as opposed to what it declares most often.

- `#e4e8ea` — 93%
- `#ffffff` — 7%
- `#000000` — 0%
- `#ec0000` — 0%
- `#4a1410` — 0%
- `#8c1c13` — 0%

### Neutral Colors

| Hex | HSL | Usage Count |
|-----|-----|-------------|
| `#000000` | hsl(0, 0%, 0%) | 283 |
| `#5d6266` | hsl(207, 5%, 38%) | 40 |
| `#ffffff` | hsl(0, 0%, 100%) | 19 |

### Background Colors

Used on large-area elements: `#e4e8ea`, `#ffffff`

### Text Colors

Text color palette: `#000000`, `#ffffff`, `#5d6266`

### Gradients

```css
background-image: linear-gradient(rgb(228, 232, 234) 35%, rgba(228, 232, 234, 0));
```

```css
background-image: linear-gradient(rgba(228, 232, 234, 0), rgb(228, 232, 234) 55%);
```

### Full Color Inventory

| Hex | Contexts | Count |
|-----|----------|-------|
| `#000000` | text, border, background | 283 |
| `#5d6266` | text, border | 40 |
| `#ffffff` | text, border, background | 19 |
| `#e4e8ea` | background | 6 |
| `#ec0000` | background | 1 |
| `#4a1410` | background | 1 |
| `#8c1c13` | background | 1 |
| `#c0462b` | background | 1 |
| `#d97a2b` | background | 1 |
| `#e5b13a` | background | 1 |
| `#8e9f3c` | background | 1 |
| `#3f8f6b` | background | 1 |
| `#2c7391` | background | 1 |
| `#3a4f9a` | background | 1 |
| `#6a3f8f` | background | 1 |

## Typography

### Font Families

- **Schibsted Grotesk** — used for all (102 elements)

### Type System

- **Scale ratio** — irregular (9 distinct sizes, no modular ratio fits)
- **Measure** — ~49 characters per line (comfortable, medium confidence from 3 samples)
- **Fluid type** — 2 clamp/viewport font sizes, 34px → 64px

### Named Scale

| Role | Size | Weight | Line Height | Tracking |
|------|------|--------|-------------|----------|
| `display` | 64px / 4rem | 800 | 54.4px | -2.56px |
| `h1` | 56px / 3.5rem | 800 | 50.4px | -1.96px |
| `h2` | 26px / 1.625rem | 800 | 39px | -0.52px |
| `title-1` | 18px / 1.125rem | 400 | 27px | normal |
| `h3` | 15px / 0.9375rem | 700 | 22.5px | normal |
| `body` | 14px / 0.875rem | 400 | 21px | normal |
| `body-sm` | 13px / 0.8125rem | 700 | 19.5px | normal |
| `micro` | 12px / 0.75rem | 600 | 18px | normal |
| `sm-3` | 8.69565px / 0.5435rem | 800 | 8.69565px | 1.21739px |

### Fluid Declarations

```css
.tally-year { font-size: clamp(40px, 5vw, 64px); }
h1 { font-size: clamp(34px, 4.4vw, 56px); }
```

### Type Scale

| Size (px) | Size (rem) | Weight | Line Height | Letter Spacing | Used On |
|-----------|------------|--------|-------------|----------------|---------|
| 64px | 4rem | 800 | 54.4px | -2.56px | span |
| 56px | 3.5rem | 800 | 50.4px | -1.96px | h1, i |
| 26px | 1.625rem | 800 | 39px | -0.52px | h2 |
| 18px | 1.125rem | 400 | 27px | normal | button |
| 15px | 0.9375rem | 700 | 22.5px | normal | h3 |
| 14px | 0.875rem | 400 | 21px | normal | html, head, meta, title |
| 13px | 0.8125rem | 700 | 19.5px | normal | h2, div, section |
| 12px | 0.75rem | 600 | 18px | normal | button, span, p |
| 8.69565px | 0.5435rem | 800 | 8.69565px | 1.21739px | span |

### Heading Scale

```css
h1 { font-size: 56px; font-weight: 800; line-height: 50.4px; }
h2 { font-size: 26px; font-weight: 800; line-height: 39px; }
h3 { font-size: 15px; font-weight: 700; line-height: 22.5px; }
h2 { font-size: 13px; font-weight: 700; line-height: 19.5px; }
```

### Body Text

```css
body { font-size: 14px; font-weight: 400; line-height: 21px; }
```

### Font Weights in Use

`400` (134x), `500` (10x), `700` (9x), `600` (7x), `800` (6x)

## Spacing

**Base unit:** 2px

| Token | Value | Rem |
|-------|-------|-----|
| spacing-1 | 1px | 0.0625rem |
| spacing-6 | 6px | 0.375rem |
| spacing-12 | 12px | 0.75rem |
| spacing-14 | 14px | 0.875rem |
| spacing-16 | 16px | 1rem |
| spacing-18 | 18px | 1.125rem |
| spacing-22 | 22px | 1.375rem |
| spacing-26 | 26px | 1.625rem |
| spacing-28 | 28px | 1.75rem |
| spacing-31 | 31px | 1.9375rem |

## Border Radii

| Label | Value | Count |
|-------|-------|-------|
| xs | 2px | 11 |
| md | 10px | 2 |
| full | 50px | 3 |
| full | 999px | 10 |

## Elevation

3 levels from 4 raw shadows · colored tint

**xs** — blur 0px, y 1px, used 1×
```css
box-shadow: rgb(207, 213, 216) 0px 1px 0px 0px;
```

**sm** — blur 28px, y 8px, used 1× · tinted (hue 210°)
```css
box-shadow: rgba(30, 40, 50, 0.16) 0px 8px 28px 0px;
```

**md** — blur 60px, y 20px, used 2× · tinted (hue 210°)
```css
box-shadow: rgba(30, 40, 50, 0.25) 0px 20px 60px 0px;
```

## CSS Custom Properties

### Colors

```css
--muted: #5d6266;
```

### Other

```css
--sky: #e4e8ea;
--paper: #ffffff;
--ink: #000000;
--rule: #cfd5d8;
--red: #ec0000;
--gutter: clamp(16px, 2.4vw, 32px);
```

### Semantic

```css
--red: #ec0000;
```

## Breakpoints

| Name | Value | Type |
|------|-------|------|
| md | 720px | max-width |

## Transitions & Animations

### Common Transitions

```css
transition: all;
```

### Keyframe Animations

**q-stamp**
```css
@keyframes q-stamp {
  0% { transform: rotate(-20deg) scale(2); opacity: 0; }
  100% { transform: none; opacity: 1; }
}
```

**q-shake**
```css
@keyframes q-shake {
  25% { transform: translateX(-4px); }
  75% { transform: translateX(4px); }
}
```

## Component Patterns

Detected UI component patterns and their most common styles:

### Buttons (22 instances)

```css
.buttons {
  background-color: rgb(0, 0, 0);
  color: rgb(0, 0, 0);
  font-size: 14px;
  font-weight: 400;
  padding-top: 4px;
  padding-right: 0px;
  border-radius: 0px;
}
```

### Cards (1 instances)

```css
.cards {
  background-color: rgb(255, 255, 255);
  border-radius: 10px;
  box-shadow: rgba(30, 40, 50, 0.16) 0px 8px 28px 0px;
  padding-top: 0px;
  padding-right: 0px;
}
```

### Links (14 instances)

```css
.links {
  color: rgb(0, 0, 0);
  font-size: 14px;
  font-weight: 400;
}
```

### Navigation (1 instances)

```css
.navigation {
  background-color: rgb(255, 255, 255);
  color: rgb(0, 0, 0);
  padding-top: 3px;
  padding-bottom: 3px;
  padding-left: 3px;
  padding-right: 3px;
  position: fixed;
  box-shadow: rgb(207, 213, 216) 0px 1px 0px 0px;
}
```

### Footer (1 instances)

```css
.footer {
  color: rgb(0, 0, 0);
  padding-top: 0px;
  padding-bottom: 14px;
  font-size: 14px;
}
```

### Modals (2 instances)

```css
.modals {
  background-color: rgb(255, 255, 255);
  border-radius: 12px;
  box-shadow: rgba(30, 40, 50, 0.25) 0px 20px 60px 0px;
  padding-top: 0px;
  padding-right: 0px;
}
```

## Component Clusters

Reusable component instances grouped by DOM structure and style similarity:

### Button — 7 instances, 2 variants

**Variant 1** (3 instances)

```css
  background: rgb(0, 0, 0);
  color: rgb(255, 255, 255);
  padding: 7px 16px 7px 16px;
  border-radius: 999px;
  border: 0px none rgb(255, 255, 255);
  font-size: 14px;
  font-weight: 500;
```

**Variant 2** (4 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(0, 0, 0);
  padding: 7px 16px 7px 16px;
  border-radius: 999px;
  border: 0px none rgb(0, 0, 0);
  font-size: 14px;
  font-weight: 500;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(0, 0, 0);
  padding: 7px 16px 7px 16px;
  border-radius: 0px;
  border: 0px 0px 0px 1px none none none solid rgb(0, 0, 0) rgb(0, 0, 0) rgb(0, 0, 0) rgb(207, 213, 216);
  font-size: 14px;
  font-weight: 500;
```

### Button — 10 instances, 1 variant

**Variant 1** (10 instances)

```css
  background: rgba(0, 0, 0, 0);
  color: rgb(0, 0, 0);
  padding: 4px 0px 4px 0px;
  border-radius: 0px;
  border: 0px none rgb(0, 0, 0);
  font-size: 14px;
  font-weight: 400;
```

### Button — 1 instance, 1 variant

**Variant 1** (1 instance)

```css
  background: rgb(0, 0, 0);
  color: rgb(255, 255, 255);
  padding: 1px 6px 1px 6px;
  border-radius: 50%;
  border: 0px none rgb(255, 255, 255);
  font-size: 14px;
  font-weight: 400;
```

## Layout System

**11 grid containers** and **7 flex containers** detected.

### The System

- **Column system** — 3 columns
- **Gap scale** — 7px · 10px · 14px
- **Fluid layout** — 3 clamp/viewport declarations

```css
.panel { width: min(340px, calc(100vw - 2 * var(--gutter))); }
.about { width: min(640px, -32px + 100vw); }
.quests { width: min(980px, -32px + 100vw); }
```

### Grid Column Patterns

| Columns | Usage Count |
|---------|-------------|
| 3-column | 10x |
| 1-column | 1x |

### Grid Templates

```css
grid-template-columns: 12px 260.766px 15.2344px;
gap: 10px;
grid-template-columns: 12px 237.906px 38.0938px;
gap: 10px;
grid-template-columns: 12px 237.906px 38.0938px;
gap: 10px;
grid-template-columns: 12px 237.906px 38.0938px;
gap: 10px;
grid-template-columns: 12px 230.297px 45.7031px;
gap: 10px;
```

### Flex Patterns

| Direction/Wrap | Count |
|----------------|-------|
| row/nowrap | 6x |
| column/nowrap | 1x |

**Gap values:** `7px`, `10px`, `14px`

## Accessibility (WCAG 2.1)

**Overall Score: 100%** — 6 passing, 0 failing color pairs

### Passing Color Pairs

| Foreground | Background | Ratio | Level |
|------------|------------|-------|-------|
| `#ffffff` | `#000000` | 21:1 | AAA |
| `#000000` | `#e4e8ea` | 17.03:1 | AAA |
| `#ffffff` | `#ec0000` | 4.6:1 | AA |
| `#000000` | `#efefef` | 18.26:1 | AAA |

## Design System Score

**Overall: 91/100 (Grade: A)**

| Category | Score |
|----------|-------|
| Color Discipline | 92/100 |
| Typography Consistency | 90/100 |
| Spacing System | 100/100 |
| Shadow Consistency | 100/100 |
| Border Radius Consistency | 100/100 |
| Accessibility | 100/100 |
| CSS Tokenization | 75/100 |

**Strengths:** Tight, disciplined color palette, Consistent typography system, Well-defined spacing scale, Clean elevation system, Consistent border radii, Strong accessibility compliance, Good CSS variable tokenization

**Issues:**
- 6 !important rules — prefer specificity over overrides
- 82% of CSS is unused — consider purging
- 611 duplicate CSS declarations

## Gradients

**2 unique gradients** detected.

| Type | Direction | Stops | Classification |
|------|-----------|-------|----------------|
| linear | — | 2 | brand |
| linear | — | 2 | brand |

```css
background: linear-gradient(rgb(228, 232, 234) 35%, rgba(228, 232, 234, 0));
background: linear-gradient(rgba(228, 232, 234, 0), rgb(228, 232, 234) 55%);
```

## Z-Index Map

**2 unique z-index values** across 1 layers.

| Layer | Range | Elements |
|-------|-------|----------|
| sticky | 10,11 | div.c.a.r.d, section.q.u.e.s.t |

## SVG Icons

**2 unique SVG icons** detected. Dominant style: **filled**.

| Size Class | Count |
|------------|-------|
| sm | 2 |

**Icon colors:** `rgb(236, 0, 0)`, `rgb(255, 255, 255)`

## Font Files

| Family | Source | Weights | Styles |
|--------|--------|---------|--------|
| Schibsted Grotesk | google-fonts | 400, 500, 700, 800 | normal |

**Google Fonts URL:** `https://fonts.googleapis.com/`

## Motion Language

**Feel:** mixed · **Scroll-linked:** yes

## Component Anatomy

### button — 19 instances

**Slots:** label

## Brand Voice

**Tone:** neutral · **Pronoun:** third-person · **Headings:** Sentence case (tight)

### Top CTA Verbs

- **period** (1)
- **context** (1)
- **floors** (1)
- **energy** (1)
- **quests** (1)
- **about** (1)
- **en** (1)
- **nl** (1)

### Button Copy Patterns

- "period" (1×)
- "context layers" (1×)
- "floors" (1×)
- "energy" (1×)
- "quests" (1×)
- "about" (1×)
- "en" (1×)
- "nl" (1×)
- "before 1600
89" (1×)
- "1600–1665 canal ring
1,301" (1×)

### Sample Headings

> LAYRS
Amsterdam
> Built in

## Page Intent

**Type:** `blog-post` (confidence 0.35)

## Section Roles

Reading order (top→bottom): content → nav → nav → hero → footer

| # | Role | Heading | Confidence |
|---|------|---------|------------|
| 0 | nav | LAYRS
Amsterdam | 0.4 |
| 1 | nav | — | 0.9 |
| 2 | hero | Built in | 0.85 |
| 3 | content | — | 0.3 |
| 4 | footer | — | 0.95 |

## Material Language

**Label:** `material-you` (confidence 0.45)

| Metric | Value |
|--------|-------|
| Avg saturation | 0.543 |
| Shadow profile | soft |
| Avg shadow blur | 0px |
| Max radius | 999px |
| backdrop-filter in use | no |
| Gradients | 2 |

## Component Screenshots

1 retina crops written to `screenshots/`. Index: `*-screenshots.json`.

| Cluster | Variant | Size (px) | File |
|---------|---------|-----------|------|
| button--default | 0 | 75 × 35 | `screenshots/button-default-0.png` |

Full-page: `screenshots/full-page.png`

## Quick Start

To recreate this design in a new project:

1. **Install fonts:** Add `Schibsted Grotesk` from Google Fonts or your font provider
2. **Import CSS variables:** Copy `variables.css` into your project
3. **Tailwind users:** Use the generated `tailwind.config.js` to extend your theme
4. **Design tokens:** Import `design-tokens.json` for tooling integration
