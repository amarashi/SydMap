# Design

`amsterdam-extract/` is the design system of [LAYRS: Amsterdam](https://stop-token.com/lab/amsterdam/), read off the
live page by [designlang](https://github.com/Manavarya09/design-extract) (design-extract v13.3.2) with
`scripts/extract-design.sh`. The page itself is shown in `amsterdam-extract/screenshots/full-page.png`.

What it found, and what SydMap keeps:

| | Amsterdam (extracted) | SydMap |
|---|---|---|
| Page | sky `#e4e8ea` (93% of the painted area), paper `#ffffff`, ink `#000000`, muted `#5d6266`, rule `#cfd5d8` | the same |
| Type | Schibsted Grotesk only: display 64/800, h1 56/800, h2 26/800, body 14/400, micro 12/600 | the same |
| Shape | pills (`999px`) for controls, `10px` cards, `2px` swatches | the same |
| Elevation | `0 8px 28px rgba(30,40,50,.16)`, `0 20px 60px rgba(30,40,50,.25)`, a 1 px `#cfd5d8` rule | the same |
| Accent | `#ec0000`, the red of Amsterdam's flag and its three St Andrew's crosses | `#d21f2b`, waratah red (the NSW floral emblem); the quests' crosses become arches of the Harbour Bridge |
| Data colours | period ramp oxblood → ochre → green → slate → violet | the same ramp over Sydney's own periods |
| Brand | the vertical red LAYRS tag beside the city name | a vertical SYDMAP tag, so the page is not mistaken for a LAYRS project |

The extracted tokens are the `:root` variables at the top of `web/styles.css`.
