#!/usr/bin/env bash
# Re-run the design extraction of the Amsterdam map with designlang (github.com/Manavarya09/design-extract).
# The output lands in design/amsterdam-extract/. Needs Node 20+ and a Chromium for Playwright
# (`npx designlang install-browser`, or PLAYWRIGHT_BROWSERS_PATH pointing at one).
#
# --full (responsive, interactions, deep interaction) also works but takes a long time on this page:
# every pass reloads 192,000 buildings in a software-rendered WebGL canvas.
set -euo pipefail
cd "$(dirname "$0")/.."
npx --yes designlang@13.3.2 https://stop-token.com/lab/amsterdam/ \
  -o design/amsterdam-extract -n layrs-amsterdam --wait 6000 --screenshots --no-history
