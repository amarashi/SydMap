---
name: SydMap
description: Sydney read along one line through time; its buildings a pale model on a white wall, in The Third Script's colours.
colors:
  wall: "#ffffff"
  paper: "#ffffff"
  stone: "#f3f0ea"
  context: "#e9e6df"
  harbour: "#b9d0d2"
  maquette: "#f1eee8"
  ink: "#2c2f2a"
  muted: "#5f625c"
  faint: "#737470"
  rule: "#e4e1da"
  hover: "#f5f3ee"
  selection: "#cfe0e2"
  cypress-teal: "#345a60"
  terracotta-sun: "#b04f3e"
  warm-feedback: "#8f5418"
  neutral-rail: "#a9a59c"
  period-1-convict-town: "#491321"
  period-2-free-colony: "#7c2d18"
  period-3-boom-years: "#c0594e"
  period-4-federation: "#e38752"
  period-5-interwar: "#e0ca78"
  period-6-post-war: "#859f55"
  period-7-first-towers: "#35816a"
  period-8-darling-harbour: "#77b0b7"
  period-9-apartment-city: "#4a798d"
  period-10-barangaroo: "#5b4087"
  heritage-shr: "#6e2418"
  heritage-local: "#c0594e"
  heritage-contributing: "#dfbd6c"
  heritage-neutral: "#8fa8b0"
  heritage-detracting: "#4f5a5c"
  story-1: "#c0594e"
  story-2: "#2a7f93"
  story-3: "#d9a22c"
  story-4: "#5e8f4a"
  story-5: "#6b4a8c"
  story-6: "#c4687f"
  story-7: "#8a5a32"
  story-8: "#34548a"
typography:
  name:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "clamp(44px, 4.2vw, 60px)"
    fontWeight: 400
    lineHeight: 0.86
  flap:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "48px"
    fontWeight: 400
    lineHeight: 1
  building-year:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "44px"
    fontWeight: 400
    lineHeight: 1
  dock-title:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "32px"
    fontWeight: 400
    lineHeight: 1.05
  building-name:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "27px"
    fontWeight: 400
    lineHeight: 1.08
  era:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "25px"
    fontWeight: 400
    lineHeight: 1.1
  section:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "22px"
    fontWeight: 400
    lineHeight: 1.15
  riddle:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "20px"
    fontWeight: 400
    lineHeight: 1.35
  list-title:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "18px"
    fontWeight: 400
    lineHeight: 1.15
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.5
  control:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 450
  small:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
  micro:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "11px"
    fontWeight: 400
rounded:
  pill: "999px"
  dialog: "12px"
  dock: "10px"
  row: "8px"
  flap: "6px"
  chip-inner: "4px"
  sheet: "16px"
  round: "50%"
spacing:
  gutter: "clamp(16px, 2.4vw, 32px)"
  dock-width: "384px"
  dock-padding: "22px 24px 26px"
  time-band: "214px"
  bar-gap: "26px"
components:
  lens-tab:
    textColor: "{colors.muted}"
    typography: "{typography.control}"
    padding: "8px 0"
  lens-tab-active:
    textColor: "{colors.ink}"
  find-field:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "40px"
    width: "260px"
  dock:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.dock}"
    width: "{spacing.dock-width}"
    padding: "{spacing.dock-padding}"
  flap:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    typography: "{typography.flap}"
    rounded: "{rounded.flap}"
    width: "42px"
    height: "58px"
  station:
    rounded: "{rounded.round}"
    size: "12px"
  year-sun:
    backgroundColor: "{colors.terracotta-sun}"
    rounded: "{rounded.round}"
    size: "24px"
  play:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.round}"
    size: "46px"
  chip:
    backgroundColor: "{colors.paper}"
    textColor: "{colors.ink}"
    rounded: "{rounded.pill}"
    height: "30px"
  pill-primary:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "7px 14px"
  sun-mark:
    backgroundColor: "{colors.terracotta-sun}"
    rounded: "{rounded.round}"
    size: "0.5em"
---

# Design System: SydMap

## Overview

**North star: Sydney read along one line through time.** SydMap shows every building of the City of Sydney and North
Sydney as a pale model standing on a white wall, and lets the visitor move along time. Time is the spine of the page:
along the bottom runs one line of ten ages, each a coloured stretch with a station at its start, and the logo's sun
rides it as the year. The legend and the timeline are the same thing.

The page reads in three bands. **Across the top**, what to look at: the city's name, then the lenses (Ages, Stories,
Heights, Heritage) as underlined text tabs, Walks, Notes and a search field. **In the middle**, the city, its ground
fading into the white wall beyond the outermost buildings so it reads as a model rather than a rectangle of map.
**Along the bottom**, time: the year on four paper flaps, the age's name and the count beside it, the key for the lens
in hand, and the line. Anything to read opens in **one dock on the right**: a building, the stories, a story, the walks,
the walk in hand, or the notes. On a phone the dock is a sheet from the bottom edge.

SydMap began as a rebuild of LAYRS: Amsterdam, whose page had a centred mode pill, a big year top right, a legend
sheet on the left and an About dialog. None of that arrangement is left. Its colours and type are The Third Script's,
the studio that made it, and the studio's mark sits under the name.

**The sun is the signature.** The terracotta sun of the logo, with its own grain (`web/img/sun.webp`), sits behind the
"y" of "Sydney", rides the line as the year (ringed in paper), draws the walks' search circle, and is every sun a
walk awards, stamped onto the stop's ticket.

## Colors

The neutrals and the two accents come from the logo package: charcoal `#2C2F2A`, cypress teal `#345A60`, terracotta sun
`#B04F3E`.

- **Wall** (`wall`): the sky and the page. Distant buildings and the ground's edges fade into it.
- **Stone** (`stone`), **context** (`context`): the land of the two councils and the shores around them.
- **Harbour** (`harbour`): a pale wash of the cypress teal.
- **Ink**, **muted**, **faint**: text, secondary text (6:1 on white) and hints (4.7:1).
- **Cypress teal**: focus rings, link underlines, the age's name beside the year, the notes' lede, the verdict.
- **Terracotta sun**: the sun and what the sun does, never a data colour, never a fill for panels or text.
- **Selection** and **warm feedback**: the text selection tint, and the "very warm" hint colour on a walk.
- **Neutral rail**: the line's stations and stretches on the Heights, Heritage and Stories lenses, where the ages are
  not the colour in use.

**Data colours.** The ten ages run from wine and rust (the convict and colonial town) through a coral terracotta, clay,
sandstone (the Bridge years), lichen and eucalypt, a harbour teal and the logo's cypress teal to a dusk violet. Every
neighbouring pair was checked with the dataviz validator (worst 12.1 colour-blind, 13.2 full colour vision), and the
line names each age too. Heritage and story colours pass both checks. Heights use a cypress-teal ramp.

## Typography

**Cormorant Garamond** 400 (roman and italic) carries the voice: "Sydney", the year on its flaps, the age's name, dock
titles, building names and years, list titles, the walks' riddles and results, the harbour's names on the map.
**Inter** (variable) carries the information: tabs, controls, lists, counts, paragraphs, street names. Both are
self-hosted from `web/fonts/`. Every year, score and count set in Cormorant uses lining, tabular figures; the serif is
never bold. The name's 0.86 line height is deliberate: it is one word set as a display.

## Layout

- **Desktop:** the name top left with the studio's mark under it; the bar top right (tabs, a hairline, Walks, Notes,
  the find field). The dock on the right, 384px wide, from under the bar to above the time band. The time band
  across the bottom: the year's flaps and words with the key to their right, then the play button and the line.
- **1000px and under:** the bar drops under the name, the dock under the bar.
- **Phones (720px and under):** the name and a round find button at the top, the tabs and Walks and Notes as one
  scrolling row under the name (fading out at its right edge); the key becomes a scrolling row above the year; the line keeps its stations without
  labels; the dock is a sheet from the bottom edge, and during a walk the phone shows the map and the walk only.

## Elevation & Depth

Sheets (the dock, the find field, flaps, chips, the hover label) are paper with a soft offset shadow in ink, never a
border: `0 6px 16px -8px` at 14% and `0 16px 36px -20px` at 22% for small sheets, `0 24px 48px -20px` at 28% for the
dock and dialogs. The wall comes forward over the model at the top and bottom (veils) and in a soft patch behind the
name. The ground fades into the wall with distance from the nearest building (a smoothed 50 m distance field, from
260 m out to 1,150 m; `EDGE` and `edgeFade` in `app.js`), so its edge follows the councils' outline and the harbour
between them, never a box. The camera stops at 22 km so the far shores stay out of view.

## Shapes

Circles for everything the sun does and for stations and swatches; pills for the find field, chips and buttons;
paper flaps with a hairline across the middle; ticket stubs (4px corners, dotted perforations) for a walk's stops;
10px for the dock, 16px for the phone sheet.

## Components

- **Bar:** lenses as text tabs, the chosen one in ink with a 2px underline; Walks with the Harbour Bridge's arch in
  terracotta; Notes; the find field.
- **Find:** buildings by name (Wikipedia, Wikidata, OpenStreetMap) and streets and water by the map's labels; whole-word
  matches first, then buildings with an article. Choosing one flies there and opens it.
- **Hover label:** a small paper label at the pointer: the building's name in the serif, then its year and age.
- **Dock:** a sticky close button, and a back pill when there is somewhere to go back to (a story, the stories, the
  walk). A building: photo and credit, name, year (44px serif) and age, then "How we know the year" and the facts first,
  then "From Wikipedia" held to five lines with "Read on", "In the stories", sources. Stories: an index by section with line icons; a story: its icon and title, era and
  count, its text, places and their stories, caveat and source. Notes: lede in teal italic, sections in the serif, getting around (how to move the city), the
  evidence list, the 2D GIS, sources, how to add to it, the original idea, the Acknowledgement of Country on stone, and
  the studio's colophon.
- **Time band:** four paper flaps that turn over when a digit changes; the age's name in teal italic and the count;
  the key (Ages: "Each station on the line is an age: choose one to see its buildings" or "Only the boom
  years ×", and the "Estimated years" switch; Heights: a storeys ramp; Heritage: five chips; Stories: the story's groups as switches); the play button (a paper disc with an ink triangle); the
  line: bars of each year's buildings in stone, the ten stretches and stations, the sun as the year, a hollow marker for the
  start of a range once it is moved. The line is a slider for the keyboard (arrows, Shift, Home, End).
- **Walks:** a list of routes (title, intro, level as a word, stops, progress, Start/Carry on/Walk again); a walk: title
  and its level as a word, ticket stubs for its stops, the riddle in the serif, hints marked by small suns, pill buttons (the main one
  ink), "Worth" and the suns at stake beside the buttons, a terracotta search ring on the map, and a stamp of earned suns (in
  the logo's grain) on the answer; the result with its line of suns.

## Do's and Don'ts

### Do:
- **Do** keep time on the line: a new way to filter by date belongs on it, not in a panel.
- **Do** open anything to read in the dock, one thing at a time, with a way back when there is one.
- **Do** take every colour from the tokens above, and validate new data colours (dataviz `validate_palette.js`).
- **Do** set years, scores and counts in lining, tabular figures.

### Don't:
- **Don't** bring back the LAYRS arrangement: a centred mode pill, a big year top right, a legend sheet on the left, an
  About modal, the cool grey sky, the black grotesk, the red tag.
- **Don't** use the sun's terracotta as a data colour, or teal as a fill.
- **Don't** add borders or coloured left rules to sheets; a sheet is separated by its shadow.
- **Don't** float hints over the city; how to use it belongs in Notes.
- **Don't** let a scrolling row or the dock end in a hard cut; fade it out.
- **Don't** set the serif in bold.
