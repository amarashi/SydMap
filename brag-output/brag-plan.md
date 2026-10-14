# Brag Plan: SydMap

## What is this app?
Every building in the City of Sydney and North Sydney in 3D (29,844 of them), coloured by the age of the city it
belongs to, with a line through time you can play to watch Sydney grow from the convict town to Barangaroo.

## The angle
The product is the film. Open on the whole city as it stands today, let it fade back to the empty harbour of 1788,
and press play: the real site builds Sydney up age by age in its own colours while its own year flaps count the
years. Then two moments of use: open the Opera House and read how its year is known; fly to the Harbour Bridge,
modelled from its published figures, and pull back to the whole city. Almost no words. The site's own interface
(the flaps, the age's name, the line of ten ages) carries the story.

## Hook (first 2-3 seconds)
The 2026 city, slowly turning, with one line: "Every building in Sydney, by the year it was built."

## Key moments (the middle)
- The city fades away to the harbour of 1788, then grows back over nine seconds as the sun rides the line; the
  flaps flip from 1788 to 2026 and the age names change (The convict town ... Barangaroo and Green Square).
- A search for "Opera House": the camera flies in, the card opens with the photo, "1973", "The first towers" and
  "How we know the year: Documented: the year comes from Wikidata."
- A search for "Harbour Bridge": the golden arch mesh up close, then the camera pulls back to the whole harbour.

## Outro / punchline
Over the pull-back: "SydMap" and "sydmap.thethirdscript.com". Nothing else.

## User flow worth showing
Press play (the city grows) → find a building (the card and its evidence) → fly to a landmark and pull back.

## Tone
- Preset: polished
- Creative direction: a quiet city film in the site's own white-wall look; the interface is the label
- Interpretation: long holds, slow camera, crossfades and white dips, serif type, two short lines of text in total.

## Format: landscape — 1920x1080, 30 fps
## Duration: 25.0 s

## Visual identity (from the project)
- Background: #ffffff (wall), harbour #b9d0d2, stone #f3f0ea
- Accent: terracotta sun #b04f3e, cypress teal #345a60
- Text: ink #2c2f2a, muted #5f625c
- Display font: Cormorant Garamond (web/fonts/cormorant-garamond-latin.woff2)
- Body font: Inter (web/fonts/inter-latin.woff2)
- Strongest visual element: the 3D city in its ten age colours, with the line of ages and the sun as the year.

## Share copy (draft)
Every building in Sydney, by the year it was built. Press play and watch the city grow from 1788.

## Audio direction
- Role: trailer energy; the music rises as the city does
- Music: an instrumental generated locally with MiniMax Music 3 (ComfyUI, `work/take-d.mp3`, seed 1788) from a
  caption written for this film: a bold hybrid-orchestral trailer piece in D major at 108 BPM, a tense ticking
  start, a driving string ostinato with taiko-style drums piling up layer by layer, a huge brass-and-strings peak,
  a final hit and a ringing struck-metal note. No vocals. The caption is in `work/music-caption.md`; take C
  (seed 11) and the two quieter earlier takes (A, B) are kept beside it.
- Music treatment: used from 1.5 s so the build runs under the hook and the growing city, full force from about
  6.5 s, the peak under the Bridge; faded out over the last 2.5 s; loudness-normalised to -17 LUFS.
- What is deliberately avoided: imitation didgeridoo or clapsticks, and the bundled corporate tracks.
- SFX posture: none; the music carries it.

## Storyboard

### Scene 1 — Hook — 3.0s
The real site at its home view, 2026, slowly turning. Line fades up: "Every building in Sydney, by the year it was
built." (settled from 0.6 s to 2.6 s).
Sequential/interaction: none
Audio intent: a pad alone, breathing
Music: soft pad
Transition mood: soft crossfade (0.6 s) → Scene 2

### Scene 2 — The city grows — 9.4s
The same view at 1788: the harbour, no buildings. The cursor presses play; the city grows age by age to 2026 while
the camera turns a little. The site's own flaps and age names are the only text.
Sequential/interaction: yes, the play button is clicked; the growth is the site's own film (?film=9)
Audio intent: the pulse enters as play is pressed and carries the growth
Transition mood: dip through white (0.4 s) → Scene 3

### Scene 3 — Opera House — 4.2s
The cursor types "Opera" into "Find a building or street", picks Sydney Opera House, the camera flies in and the
card opens: photo, Sydney Opera House, 1973, The first towers, How we know the year.
Sequential/interaction: yes, typing and a click; the fly-in is the site's own
Audio intent: a bell as the card settles
Transition mood: dip through white (0.4 s) → Scene 4

### Scene 4 — The Bridge, and the whole city — 5.9s
The cursor types "Harbour Bridge", the camera flies to the golden arch, the card is closed, the camera turns around
the bridge and pulls back to the whole harbour. Over the pull-back: "SydMap" and "sydmap.thethirdscript.com".
Sequential/interaction: yes, typing, a click, a close, a pull-back
Audio intent: the last chord rings under the outro
Transition mood: hold; fade the music out at the end.

**Music mood for this video:** quiet, cinematic
**Audio summary:** a pad under the hook, a slow pulse through the growth, a bell on the card, a held chord to the end.

## How it is built
As for the FHA Data Atlas: the real site is recorded with Playwright (DevTools screencast at 3840x2160, a drawn
cursor), the shots are cut and framed with ffmpeg, the two text lines are an HTML overlay rendered frame by frame,
and the music is synthesised with numpy. The Hyperframes skills are not installed on this machine, so this pipeline
replaces that step; `work/build.py` holds all of it.
