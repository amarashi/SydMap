# Design

SydMap wears the colours of [The Third Script](https://thethirdscript.com), the studio that made it. The full system
(tokens, components, rules) is in [`../DESIGN.md`](../DESIGN.md); the tokens are the `:root` variables at the top of
`web/styles.css` and the scene colours at the top of `web/app.js`.

## Where it came from

SydMap began as a rebuild of [LAYRS: Amsterdam](https://stop-token.com/lab/amsterdam/), and its first look was that
page's design system, read off the live page by [designlang](https://github.com/Manavarya09/design-extract)
(design-extract v13.3.2) with `scripts/extract-design.sh`. `amsterdam-extract/` keeps that extraction, and the page
itself is in `amsterdam-extract/screenshots/full-page.png`. The working shape stays (the mode bar, the legend, the
building card, the timeline); the look is now The Third Script's:

| | First version (from Amsterdam) | Now (The Third Script) |
|---|---|---|
| Page | sky `#e4e8ea`, paper `#ffffff`, ink `#000000`, muted `#5d6266`, rule `#cfd5d8` | white wall `#ffffff`, stone land `#f3f0ea`, harbour `#b9d0d2`, charcoal ink `#2c2f2a`, stone grey `#5f625c`, rule `#e4e1da` |
| Type | Schibsted Grotesk only, display 800 | Cormorant Garamond 400 for the voice (name, years, titles, riddles), Inter for the information; self-hosted |
| Accent | waratah red `#d21f2b` | the logo's terracotta sun `#b04f3e` (the mark, the film, the quests, and no data) and cypress teal `#345a60` (focus, links) |
| Brand | a vertical SYDMAP tag on a block of red, LAYRS's device | the logo's textured sun behind the "y" of "Sydney" |
| Data colours | Amsterdam's ramp, oxblood to violet | the sun's colours, wine to dusk violet, checked for colour-blind separation |
| Elevation | `0 8px 28px` and `0 20px 60px` cool shadows | the thethirdscript.com cards' soft offset shadows, in charcoal |

## Checking colours

The period, heritage and layer colours were checked with the dataviz skill's validator, neighbour against neighbour:

```bash
node scripts/validate_palette.js "#491321,#7c2d18,#c0594e,#e38752,#e0ca78,#859f55,#35816a,#77b0b7,#4a798d,#5b4087" --mode light --surface "#f3f0ea"
```

Worst neighbours: periods ΔE 12.1 colour-blind, 13.2 normal vision (rust and coral terracotta; the legend's labels, the
timeline's position and the card's period also tell them apart); heritage 14.0 and 16.1; layers 10.4 and 15.3. None of them uses the sun's own terracotta, which is kept for the sun. The
original ramp's worst pair was 2.6 and 8.3.
