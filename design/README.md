# Design

SydMap wears the colours of [The Third Script](https://thethirdscript.com), the studio that made it, in a layout of
its own. The full system (tokens, components, rules) is in [`../DESIGN.md`](../DESIGN.md); the tokens are the `:root`
variables at the top of `web/styles.css` and the scene colours at the top of `web/app.js`.

## Where it came from

SydMap began as a rebuild of [LAYRS: Amsterdam](https://stop-token.com/lab/amsterdam/), and its first version kept
that page's design system and layout, read off the live page by
[designlang](https://github.com/Manavarya09/design-extract) (design-extract v13.3.2) with `scripts/extract-design.sh`.
`amsterdam-extract/` keeps that extraction, and the page itself is in `amsterdam-extract/screenshots/full-page.png`.
SydMap now has its own look, layout and words:

| | First version (from Amsterdam) | Now |
|---|---|---|
| Layout | a centred pill of modes, a big year top right, a legend sheet on the left, a card at the pointer, About in a dialog | lenses as tabs top right; time along the bottom as one line of ten ages (the legend and the timeline in one) with the year on paper flaps; one dock on the right for anything to read |
| Words | Period, Context layers, Floors, Energy/Heritage, Quests, About, "Built in" | Ages, Stories, Heights, Heritage, Walks, Notes; every sentence rewritten |
| Page | sky `#e4e8ea`, paper `#ffffff`, ink `#000000`, muted `#5d6266`, rule `#cfd5d8` | white wall `#ffffff`, stone land `#f3f0ea`, harbour `#b9d0d2`, charcoal ink `#2c2f2a`, stone grey `#5f625c`, rule `#e4e1da`; the ground fades into the wall beyond the buildings |
| Type | Schibsted Grotesk only, display 800 | Cormorant Garamond 400 for the voice (name, years, ages, titles, riddles), Inter for the information; self-hosted |
| Accent | waratah red `#d21f2b` | the logo's terracotta sun `#b04f3e` (the mark, the year, the walks' suns, and no data) and cypress teal `#345a60` (focus, links, the age's name) |
| Brand | a vertical SYDMAP tag on a block of red | the logo's textured sun behind the "y" of "Sydney", and the studio's mark under it |
| Data colours | Amsterdam's ramp, oxblood to violet | the sun's colours, wine to dusk violet, checked for colour-blind separation |
| Search | none | find a building or street |

The structure was chosen by the owner from three prototypes ("the line through time", "the catalogue", "the field
guide") on 2026-10-14.

## Checking colours

The period, heritage and layer colours were checked with the dataviz skill's validator, neighbour against neighbour:

```bash
node scripts/validate_palette.js "#491321,#7c2d18,#c0594e,#e38752,#e0ca78,#859f55,#35816a,#77b0b7,#4a798d,#5b4087" --mode light --surface "#f3f0ea"
```

Worst neighbours: ages ΔE 12.1 colour-blind, 13.2 normal vision (rust and coral terracotta; the line names each age,
and the card and the hover label name it too); heritage 14.0 and 16.1; stories 10.4 and 15.3. None of them uses the
sun's own terracotta, which is kept for the sun. The original ramp's worst pair was 2.6 and 8.3.
