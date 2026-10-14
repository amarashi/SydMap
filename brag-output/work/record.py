"""Record the SydMap shots from the local site (python scripts/serve.py, http://localhost:8642).

    uv run --with playwright python record.py [hook|film|opera|bridge ...]

Each shot is captured with the DevTools screencast at twice the CSS resolution (3840x2160 for a 1920x1080 page), so
the edit can reframe without blur. A drawn cursor is injected, in the site's ink, because a scripted mouse has none.
Writes work/shot-<name>.mp4 at 30 fps.
"""
import asyncio, base64, os, shutil, subprocess, sys, tempfile, time

from playwright.async_api import async_playwright

BASE = "http://localhost:8642/"
HERE = os.path.dirname(os.path.abspath(__file__))
W, H, DSF = 1920, 1080, 2

CURSOR_JS = r"""
addEventListener('DOMContentLoaded', () => {
  const c = document.createElement('div');
  c.style.cssText = 'position:fixed;left:0;top:0;z-index:2147483647;pointer-events:none;transform:translate(-200px,-200px)';
  c.innerHTML = '<svg width="28" height="28" viewBox="0 0 24 24"><path d="M4 2.5l6.8 18.2 2.6-7.4 7.4-2.6z" fill="#fff" stroke="#2c2f2a" stroke-width="1.5" stroke-linejoin="round"/></svg>';
  document.body.appendChild(c);
  addEventListener('mousemove', e => { c.style.transform = `translate(${e.clientX - 4}px,${e.clientY - 2}px)`; }, true);
});
"""


class Shot:
    def __init__(self, page):
        self.page, self.x, self.y = page, W * 0.5, H * 0.6

    async def wait(self, s):
        await asyncio.sleep(s)

    async def move(self, x, y, dur=0.7):
        steps = max(8, int(dur * 60))
        x0, y0 = self.x, self.y
        for i in range(1, steps + 1):
            u = i / steps; e = u * u * (3 - 2 * u)
            await self.page.mouse.move(x0 + (x - x0) * e, y0 + (y - y0) * e)
            await asyncio.sleep(dur / steps)
        self.x, self.y = x, y

    async def drag(self, x0, y0, x1, y1, dur=3.0, button="left"):
        """A left drag turns the city (MapControls rotate)."""
        await self.move(x0, y0, 0.5)
        await self.page.mouse.down(button=button)
        await self.move(x1, y1, dur)
        await self.page.mouse.up(button=button)

    async def box(self, loc):
        b = await loc.bounding_box()
        return b["x"] + b["width"] / 2, b["y"] + b["height"] / 2, b

    async def click(self, loc, dur=0.8, pause=0.3):
        x, y, _ = await self.box(loc)
        await self.move(x, y, dur)
        await asyncio.sleep(pause)
        await self.page.mouse.down(); await asyncio.sleep(0.08); await self.page.mouse.up()

    async def type(self, loc, text):
        await self.click(loc)
        await self.page.keyboard.type(text, delay=95)

    async def wheel(self, dy, dur=2.0):
        steps = max(1, int(dur * 30))
        for _ in range(steps):
            await self.page.mouse.wheel(0, dy / steps); await asyncio.sleep(dur / steps)


async def loaded(page):
    await page.wait_for_function("getComputedStyle(document.getElementById('loading')).display==='none' || document.getElementById('loading').hidden", timeout=90000)
    await asyncio.sleep(2.0)


# --- shots: (url query, setup before recording, recorded action) --------------------------------------

async def hook(s):
    await s.wait(0.3)
    await s.drag(1200, 620, 1120, 640, 5.0)        # a slow turn
    await s.wait(0.5)


async def film_setup(p):
    await p.focus("#hist"); await p.keyboard.press("Home")          # the year to 1788
    await p.evaluate("document.activeElement && document.activeElement.blur()")
    await asyncio.sleep(0.8)


async def film(s):
    await s.click(s.page.locator("#play"), 0.9, 0.3)
    await s.move(1200, 640, 0.6)
    await s.drag(1200, 640, 1070, 660, 9.4)        # turn through the whole film (?film=9)
    await s.wait(1.2)


async def opera(s):
    await s.wait(0.3)
    await s.type(s.page.locator("#find"), "Opera")
    await s.wait(0.5)
    await s.click(s.page.locator("#find-results [role=option]").filter(has_text="Sydney Opera House").first, 0.6, 0.2)
    await s.wait(1.8)                              # the flight
    await s.move(700, 760, 0.8)                    # the cursor out of the card
    await s.wheel(6500, 2.6)                       # back, so the shells sit in Circular Quay
    await s.wait(3.0)


async def bridge(s):
    await s.wait(0.3)
    await s.type(s.page.locator("#find"), "Harbour Bridge")
    await s.wait(0.5)
    await s.click(s.page.locator("#find-results [role=option]").filter(has_text="Sydney Harbour Bridge").first, 0.6, 0.2)
    await s.wait(1.8)                              # the flight
    await s.click(s.page.locator("#dock .dock-close"), 0.6, 0.2)
    await s.move(900, 640, 0.6)
    await s.drag(900, 640, 760, 660, 3.0)          # around the arch
    await s.move(960, 560, 0.3)
    await s.wheel(5200, 4.0)                       # pull back to the whole harbour
    await s.wait(1.5)


SHOTS = {
    "hook":   ("", None, hook),
    "film":   ("?film=9", film_setup, film),
    "opera":  ("", None, opera),
    "bridge": ("", None, bridge),
}


async def record(page, action, out):
    cdp = await page.context.new_cdp_session(page)
    frames, tmp = [], tempfile.mkdtemp(prefix="sydmap-rec-")

    async def on_frame(p):
        path = os.path.join(tmp, f"{len(frames):05d}.jpg")
        with open(path, "wb") as f:
            f.write(base64.b64decode(p["data"]))
        frames.append((p["metadata"]["timestamp"], path, time.time()))
        try:
            await cdp.send("Page.screencastFrameAck", {"sessionId": p["sessionId"]})
        except Exception:
            pass

    cdp.on("Page.screencastFrame", lambda p: asyncio.ensure_future(on_frame(p)))
    await cdp.send("Page.startScreencast", {"format": "jpeg", "quality": 92, "maxWidth": W * DSF, "maxHeight": H * DSF, "everyNthFrame": 1})
    await page.mouse.move(W * 0.5, 95)
    await asyncio.sleep(0.8)
    await action()
    await asyncio.sleep(0.6)
    t_end = time.time()
    await cdp.send("Page.stopScreencast")
    await asyncio.sleep(0.3)
    lst = os.path.join(tmp, "list.txt")
    t = [0.0] + [frames[i][0] - frames[1][0] + (frames[1][2] - frames[0][2]) for i in range(1, len(frames))]
    total = t[-1] + max(0.04, t_end - frames[-1][2])
    with open(lst, "w") as f:
        j = 0
        for k in range(int(total * 30)):
            while j + 1 < len(frames) and t[j + 1] <= k / 30:
                j += 1
            f.write(f"file '{frames[j][1].replace(os.sep, '/')}'\nduration 0.0333333\n")
    subprocess.run(["ffmpeg", "-v", "error", "-y", "-f", "concat", "-safe", "0", "-i", lst, "-r", "30",
                    "-vf", f"scale={W * DSF}:{H * DSF}:flags=lanczos,format=yuv420p",
                    "-c:v", "libx264", "-crf", "16", "-preset", "medium", out], check=True)
    gaps = sorted(b[0] - a[0] for a, b in zip(frames, frames[1:]) if b[0] - a[0] < 0.25)
    if gaps:
        print(f"  frame gap: median {gaps[len(gaps) // 2] * 1000:.0f} ms, 90th {gaps[int(len(gaps) * 0.9)] * 1000:.0f} ms", flush=True)
    shutil.rmtree(tmp, ignore_errors=True)
    return len(frames), total


async def main():
    names = [a for a in sys.argv[1:]] or list(SHOTS)
    async with async_playwright() as pw:
        browser = await pw.chromium.launch(channel="chrome", headless=True,
                                           args=["--use-gl=angle", "--use-angle=default", "--ignore-gpu-blocklist", "--hide-scrollbars"])
        for name in names:
            query, setup, action = SHOTS[name]
            ctx = await browser.new_context(viewport={"width": W, "height": H}, device_scale_factor=DSF)
            await ctx.add_init_script(CURSOR_JS)
            page = await ctx.new_page()
            await page.goto(BASE + query)
            await loaded(page)
            if setup:
                await setup(page)
            n, d = await record(page, lambda: action(Shot(page)), os.path.join(HERE, f"shot-{name}.mp4"))
            print(f"{name}: {n} frames, {d:.1f}s", flush=True)
            await ctx.close()
        await browser.close()


asyncio.run(main())
