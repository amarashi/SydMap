---
name: SydMap
description: Sydney's buildings as one pale model on a white gallery wall, coloured by age, in The Third Script's colours.
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
  cypress-teal: "#345a60"
  terracotta-sun: "#b04f3e"
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
  layer-1: "#c0594e"
  layer-2: "#2a7f93"
  layer-3: "#d9a22c"
  layer-4: "#5e8f4a"
  layer-5: "#6b4a8c"
  layer-6: "#c4687f"
  layer-7: "#8a5a32"
  layer-8: "#34548a"
typography:
  display:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "clamp(44px, 4.8vw, 68px)"
    fontWeight: 400
    lineHeight: 0.86
  dialog-title:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "36px"
    fontWeight: 400
    lineHeight: 1.05
  card-title:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "25px"
    fontWeight: 400
    lineHeight: 1.08
  card-year:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "40px"
    fontWeight: 400
    lineHeight: 1
  panel-title:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "22px"
    fontWeight: 400
  riddle:
    fontFamily: "Cormorant Garamond, Georgia, serif"
    fontSize: "19px"
    fontWeight: 400
    lineHeight: 1.35
  body:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 400
    lineHeight: 1.5
  reading:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "14px"
    fontWeight: 400
    lineHeight: 1.65
  control:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "13.5px"
    fontWeight: 450
  small:
    fontFamily: "Inter, system-ui, sans-serif"
    fontSize: "12px"
    fontWeight: 400
rounded:
  pill: "999px"
  sheet: "10px"
  dialog: "12px"
  row: "6px"
  sun: "50%"
spacing:
  gutter: "clamp(16px, 2.4vw, 32px)"
  sheet-padding: "16px 18px"
  card-padding: "12px 18px"
components:
  mode-button:
    textColor: "{colors.ink}"
    typography: "{typography.control}"
    rounded: "{rounded.pill}"
    padding: "8px 16px"
  mode-button-active:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
  sheet:
    backgroundColor: "{colors.paper}"
    rounded: "{rounded.sheet}"
    padding: "{spacing.sheet-padding}"
  play-button:
    backgroundColor: "{colors.terracotta-sun}"
    textColor: "{colors.paper}"
    rounded: "{rounded.sun}"
    size: "48px"
  primary-button:
    backgroundColor: "{colors.ink}"
    textColor: "{colors.paper}"
    rounded: "{rounded.pill}"
    padding: "7px 14px"
  swatch:
    rounded: "{rounded.sun}"
    size: "11px"
  quest-mark:
    backgroundColor: "{colors.terracotta-sun}"
    rounded: "{rounded.sun}"
    size: "0.5em"
---

# Design System: SydMap

## Overview

**North star: the model in the white gallery.** SydMap is a sister piece to [thethirdscript.com](https://thethirdscript.com)
and wears its colours. The city is the one artwork: every building of the City of Sydney and North Sydney as a pale
architectural model standing on warm stone, its harbour in the cypress teal of The Third Script's logo, against a white
wall it fades into at the horizon. The interface is the label beside it: small, exact, and never louder than the city.

SydMap began as a rebuild of LAYRS: Amsterdam and kept its working shape (the mode bar, the legend, the building card,
the timeline). Its look is now The Third Script's, so it is no longer mistaken for a LAYRS project and it sits with
the studio's other work.

**The sun is the signature.** The terracotta sun of the logo, with its own grain (`web/img/sun.webp`), is SydMap's
mark and its sense of time: it sits behind the last letter of "Sydney" as the logo's sun sits behind the cypress, it
is the play button that runs the film, it rides the timeline as the year's marker (ringed in paper), it draws the
quests' search circle, and every mark a quest awards is a small sun, on the result line too. Every colour in the legend is a small disc too.

## Colors

The neutrals and the two accents come from the logo package (`The_Third_Script_Logo_Package/README.md` in the
thethirdscript repository): charcoal `#2C2F2A`, cypress teal `#345A60`, terracotta sun `#B04F3E`.

- **Wall** (`wall`): the sky, white, and the page behind every sheet. Distant buildings fade into it (the fog colour).
- **Stone** (`stone`), **context** (`context`): the land of the two councils, and the shores around them, a shade darker.
- **Harbour** (`harbour`): a pale wash of the cypress teal.
- **Ink** (`ink`), **muted** (`muted`), **faint** (`faint`): text, secondary text (6:1 on white) and hints (4.7:1).
- **Cypress teal** (`cypress-teal`): focus rings, link underlines, the italic notices, the floors ramp.
- **Terracotta sun** (`terracotta-sun`): the sun and everything the sun does (above), and nothing else. Never a fill for
  panels or text blocks, and never a data colour: the data's terracotta family (rust, a lighter coral terracotta) stays
  clear of it, and the timeline's sun wears a paper ring so it reads over any bar.

**Data colours.** The ten periods run from wine and rust (the convict and colonial town) through a coral terracotta
(the boom years), clay, sandstone (the Bridge years), lichen and eucalypt, a harbour teal and the logo's cypress teal to
a dusk violet for the newest city; the sandstone, lichen and harbour teal are kept soft so the pale model leads. Every
neighbouring pair was checked with the dataviz validator (OKLab ΔE under protanopia and deuteranopia, Machado 2009):
worst pair 12.1 for colour-blind readers and 13.2 for full colour vision, under the 15 target, so the legend (dates and
names), the timeline's position and the card's period label carry the period too. The heritage colours (wine, coral
terracotta, sandstone, grey-teal, slate) and the eight layer colours pass both checks. The floors ramp is the cypress
teal, from a pale wash to the darkest shade of the logo's trees.

## Typography

**Cormorant Garamond** (400, roman and italic) carries the voice: "Sydney" and the year, panel and dialog titles, a
building's name and year on its card, the quests' riddles and results, the harbour's names on the map (italic, as on
an old chart), the loading line. **Inter** (variable, 400 to 500) carries the information: controls, lists, counts,
paragraphs, street names. Both are self-hosted from `web/fonts/` (latin subset, SIL Open Font License), the same files
as thethirdscript.com, so no visitor's address goes to a font service.

Cormorant's figures are old-style by default; every year, score and count set in it uses `lining-nums tabular-nums`,
so "1918" stands even and does not jump while the film plays. The serif is only ever 400: there is no bold file, so
never ask it for weight. Inter's counts use tabular figures.

## Layout

The 3D map fills the window. Around it, fixed to the edges: the masthead top left, the mode bar top centre, the year
and its count top right with About and 2D GIS under them, the legend sheet on the left under the masthead, the
timeline across the bottom with the sun to play it. White veils at the top and bottom let the labels read over the
model. On phones (720px and under) the modes become a strip above the timeline, the legend a folded sheet above them,
the card a sheet from the bottom, and Quests a pill under the name.

## Elevation & Depth

Sheets (the legend, the mode bar, the tools, cards, dialogs, the open quest) are paper white with a soft, offset
shadow in ink, never a border: `0 6px 16px -8px` ink at 14% and `0 16px 36px -20px` ink at 22% for sheets on the map;
`0 24px 48px -20px` ink at 28% and `0 6px 16px -8px` ink at 12% for cards and dialogs. A dialog's backdrop is the
white wall at 72%. The model itself is lit by a low north-west afternoon sun and fades into the white with distance.

## Shapes

Pills for controls, 10px sheets, 12px dialogs, 6px rows, and circles for everything the sun does (the play button,
the legend's swatches, the quests' marks, the timeline's marker). Hairlines (`rule`) only separate sections inside a
sheet.

## Components

- **Masthead:** "Sydney" in the display serif with the textured sun behind the top of its "y"; under it, one line:
  "**SydMap**: every building standing today, by age and historical context." (hidden on phones).
- **Mode bar:** four colourings and Quests in one pill; the chosen colouring filled ink. Quests opens under the arch
  of the Harbour Bridge, drawn in terracotta.
- **Year:** "Today" or the year in the display serif with lining figures; the count of buildings under it.
- **Legend sheet:** a serif title ("Built in", "Storeys", "Heritage"), then rows of a small sun, a label and a count.
  Context layers list their sections with line icons and open a layer's story, groups and sources.
- **Building card:** photo, the name and year in the serif, the period with its sun, then sections divided by
  hairlines: the article's lead, the layers, the facts (right-aligned, tabular), how the year was found, sources.
- **Timeline:** the buildings of each year as bars in the period colours; the year a charcoal hairline with the sun
  riding on top; the play button is the sun with a white triangle.
- **Quests:** tiles with a serif title and the level as one to three small suns; the open quest is a paper slip with
  a serif riddle, hints marked by small suns, pill buttons (the main one ink), a terracotta search ring on the map,
  and a stamp of earned suns that settles onto the answer.
- **About:** a reading page: serif headings, the maker's line, the non-commercial notice in teal italic, the
  Acknowledgement of Country on a stone panel, the method and the data.

## Do's and Don'ts

### Do:
- **Do** take every colour from the tokens above; the neutrals and accents are the logo's.
- **Do** let the sun do one job at a time: the mark, the film, the year, the search, the marks.
- **Do** set years and scores in the serif with lining, tabular figures.
- **Do** run `node scripts/validate_palette.js` (dataviz skill) on any new data colours, neighbours first.

### Don't:
- **Don't** bring back the LAYRS look: no cool grey sky, heavy black grotesk, red vertical tag or waratah red.
- **Don't** use terracotta for panels, banners or body text, or teal for fills.
- **Don't** set the serif in bold, or put old-style figures in a number that changes.
- **Don't** add borders or coloured left rules to sheets and notes; a sheet is separated by its shadow.
