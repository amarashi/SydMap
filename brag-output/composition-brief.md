# Composition Brief: SydMap

## Objective
A 25 s launch film for SydMap, in the site's own look, with two lines of text.

## Output
- Work: `brag-output/work/` (shots, overlay, music, build script)
- Rendered video: `brag-output/brag.mp4`, poster `brag-output/brag.jpg`
- Format: landscape, 1920x1080, 30 fps

## Source Material
- Project root: `C:\dev\web\SydMap`
- Files read: `web/index.html`, `DESIGN.md`, `PRODUCT.md`, `README.md`, `web/app.js` (play, find, fly), `docs/screenshots/*`
- Product name: SydMap
- Tagline: "Sydney, year by year"
- Footage: the real site recorded at 3840x2160 (`work/record.py`): the home view turning; the city growing from 1788
  with `?film=9`; the Opera House card; the Harbour Bridge and the pull-back.
- Copy that appears verbatim: "SydMap", "sydmap.thethirdscript.com"
- Copy written for the film: "Every building in Sydney, by the year it was built."

## Creative Direction
- Tone: polished. A quiet city film; the interface is the label.
- Hook: the 2026 city turning, one line.
- Outro: "SydMap" and the address over the pull-back.
- Avoid: any more text, hits, UI click sounds, anything that is not the site.

## Visual Identity
- Wall #ffffff, harbour #b9d0d2, ink #2c2f2a, muted #5f625c, sun #b04f3e
- Cormorant Garamond for the two lines, Inter for the address (the site's own woff2 files)
- Transitions: a 0.6 s crossfade from today's city to the empty harbour; 0.4 s dips through white between the
  other shots, as the site itself fades into its white wall.

## Storyboard (22.5 s)
| # | Time | Footage | Text |
|---|---|---|---|
| 1 Hook | 0.0–3.0 | shot-hook: the 2026 city turning | "Every building in Sydney, by the year it was built." |
| 2 Grows | 3.0–12.4 | shot-film: play pressed, 1788 → 2026 | none (the site's flaps and ages) |
| 3 Opera | 12.4–16.6 | shot-opera: find, fly, card | none |
| 4 Bridge | 16.6–22.5 | shot-bridge: fly, turn, pull back | "SydMap" / "sydmap.thethirdscript.com" from 19.5 |

## Audio
- Score: `work/take-d.mp3`, generated locally with MiniMax Music 3 in ComfyUI from the trailer caption in
  `work/music-caption.md`. Used from 1.5 s, faded out over the last 2.5 s, normalised to -17 LUFS
  (`build.py score=take-d.mp3@1.5`).
- No SFX library sounds; no audio-reactive visuals.

## Build
`work/build.py`: shots (ffmpeg cut, retime, reframe) → overlay (HTML rendered frame by frame with Playwright) →
music → final mux; then the poster frame is picked and baked as frame 0.
