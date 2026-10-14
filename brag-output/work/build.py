"""Build brag.mp4 for SydMap from the recorded shots.

    uv run --with playwright --with numpy --with scipy python build.py [shots|overlay|music|final|poster|all]
"""
import os, subprocess, sys
import numpy as np

HERE = os.path.dirname(os.path.abspath(__file__))
OUT = os.path.dirname(HERE)
FPS, W, H = 30, 1920, 1080

# id, source clip, source in, source out, output duration (the clip is retimed to fit)
SHOTS = [
    ("hook",   "shot-hook.mp4",   1.6, 4.8,  3.2),
    ("film",   "shot-film.mp4",   1.2, 11.0, 9.8),
    ("opera",  "shot-opera.mp4",  2.6, 14.6, 7.0),
    ("bridge", "shot-bridge.mp4", 13.5, 28.3, 6.6),
]
# transitions between consecutive shots: (ffmpeg xfade kind, seconds)
XF = [("fade", 0.6), ("fadewhite", 0.5), ("fadewhite", 0.5)]


def timeline():
    """Output start time of each shot and the total length."""
    t, starts = 0.0, []
    for i, (_, _, _, _, dur) in enumerate(SHOTS):
        starts.append(t)
        t += dur - (XF[i][1] if i < len(XF) else 0)
    return starts, t


STARTS, END = timeline()


def ff(*args):
    subprocess.run(["ffmpeg", "-v", "error", "-y", *args], check=True)


def shots():
    for sid, clip, a, b, dur in SHOTS:
        speed = (b - a) / dur
        n = int(round(dur * FPS))
        ff("-ss", f"{a}", "-to", f"{b}", "-i", os.path.join(HERE, clip), "-an",
           "-vf", f"setpts=(PTS-STARTPTS)/{speed:.6f},fps={FPS},scale={W}:{H}:flags=lanczos,format=yuv420p",
           "-frames:v", str(n), "-c:v", "libx264", "-crf", "14", "-preset", "medium", os.path.join(HERE, f"seg-{sid}.mp4"))
        print("segment", sid, f"{dur}s at {speed:.2f}x", flush=True)
    # chain the crossfades
    inputs, parts, prev, off = [], [], "[0:v]", 0.0
    for i, (sid, *_r) in enumerate(SHOTS):
        inputs += ["-i", os.path.join(HERE, f"seg-{sid}.mp4")]
    for i, (kind, d) in enumerate(XF):
        off += SHOTS[i][4] - d
        out = f"[v{i}]" if i < len(XF) - 1 else "[v]"
        parts.append(f"{prev}[{i + 1}:v]xfade=transition={kind}:duration={d}:offset={off:.3f}{out}")
        prev = out
    ff(*inputs, "-filter_complex", ";".join(parts), "-map", "[v]", "-c:v", "libx264", "-crf", "14", "-preset", "medium",
       "-pix_fmt", "yuv420p", os.path.join(HERE, "base.mp4"))
    print("base.mp4", f"{END:.2f}s", flush=True)


# ---------------------------------------------------------------- text overlay
HOOK = (0.0, 3.2)                       # the hook line lives in this window
OUTRO = (STARTS[3] + 2.4, END)          # the outro lives over the pull-back


def overlay():
    from playwright.sync_api import sync_playwright
    with sync_playwright() as pw:
        br = pw.chromium.launch(channel="chrome")
        pg = br.new_page(viewport={"width": W, "height": H})
        pg.goto("file:///" + os.path.join(HERE, "overlay.html").replace(os.sep, "/"))
        pg.evaluate(f"window.OUTRO_T0 = {OUTRO[0]:.4f}; document.fonts.ready")
        pg.wait_for_timeout(400)
        for name, (t0, t1) in (("hook", HOOK), ("outro", OUTRO)):
            d = os.path.join(HERE, f"ovl-{name}"); os.makedirs(d, exist_ok=True)
            n = int(round((t1 - t0) * FPS))
            for i in range(n):
                pg.evaluate("t => render(t)", t0 + i / FPS)
                pg.screenshot(path=os.path.join(d, f"{i:04d}.png"), omit_background=True)
            print(name, n, "overlay frames", flush=True)
        br.close()


# ---------------------------------------------------------------- music
SR = 48000


def lowpass(x, fc, order=2):
    from scipy.signal import butter, sosfilt
    return sosfilt(butter(order, fc, fs=SR, output="sos"), x)


def reverb(x, secs=2.6, mix=0.3, seed=3):
    from scipy.signal import fftconvolve
    rng = np.random.default_rng(seed); n = int(secs * SR)
    ir = rng.standard_normal((2, n)) * np.exp(-np.arange(n) / SR * 2.8)
    ir[:, : int(0.015 * SR)] = 0
    ir = np.stack([lowpass(ir[0], 4500), lowpass(ir[1], 4500)])
    wet = np.stack([fftconvolve(x[c], ir[c])[: x.shape[1]] for c in range(2)])
    wet *= np.sqrt(np.mean(x ** 2) / max(np.mean(wet ** 2), 1e-12))
    return (1 - mix) * x + mix * wet


def midi(m): return 440.0 * 2 ** ((m - 69) / 12)


def tone(f, dur, a=0.01, r=0.6, harm=(1.0, 0.35, 0.12), vib=0.0):
    n = int(dur * SR); t = np.arange(n) / SR
    env = np.minimum(1, t / max(a, 1e-4)) * np.exp(-t / r)
    ph = 2 * np.pi * f * t + (vib * np.sin(2 * np.pi * 5 * t) if vib else 0)
    return env * sum(g * np.sin(ph * (k + 1)) for k, g in enumerate(harm))


def pad(freqs, t0, t1, rise=1.6, fall=1.4, gain=0.05):
    n = int((t1 - t0) * SR); t = np.arange(n) / SR
    env = np.minimum(1, t / rise) * np.minimum(1, (t1 - t0 - t) / fall)
    out = np.zeros(n)
    for f in freqs:
        for det in (-0.25, 0.25):
            ff_ = f * 2 ** (det / 1200)
            out += np.sin(2 * np.pi * ff_ * t) + 0.3 * np.sin(2 * np.pi * 2 * ff_ * t + 0.3)
    return lowpass(out * env * gain / len(freqs), 1800), t0


def music():
    N = int((END + 0.5) * SR)
    dry = np.zeros((2, N)); send = np.zeros((2, N))

    def add(sig, t0, gain=1.0, pan=0.0, rev=0.35):
        i = int(t0 * SR); j = min(N, i + len(sig)); s = sig[: j - i] * gain
        l, r = np.sqrt(0.5 * (1 - pan)), np.sqrt(0.5 * (1 + pan))
        dry[0, i:j] += s * l * (1 - rev); dry[1, i:j] += s * r * (1 - rev)
        send[0, i:j] += s * l * rev; send[1, i:j] += s * r * rev

    # F major, one chord per four seconds: F  Dm  Bb  C  F  Bb  F(ring)
    F, Dm, Bb, C = [53, 57, 60, 65], [50, 53, 57, 62], [46, 50, 53, 58], [48, 52, 55, 60]
    chords = [(F, 0.0, 4.4), (Dm, 4.0, 8.4), (Bb, 8.0, 12.6), (C, 12.2, 16.8), (F, 16.4, 19.9), (Bb, 19.5, 21.6)]
    for notes, a, b in chords:
        sig, t0 = pad([midi(m) for m in notes], a, b)
        add(sig, t0, 1.0, 0.0, 0.5)
    # the last chord rings out
    sig, t0 = pad([midi(m) for m in [53, 57, 60, 65, 72]], 21.2, END + 0.4, rise=1.2, fall=2.6, gain=0.06)
    add(sig, t0, 1.0, 0.0, 0.55)

    # plucked notes: a slow arpeggio from the moment play is pressed, through the growth, then sparser
    rng = np.random.default_rng(7)
    step = 0.5
    t = STARTS[1] + 0.8
    while t < STARTS[3] + 2.0:
        for notes, a, b in chords:
            if a <= t < b: cur = notes
        octave = 12 if rng.random() < 0.6 else 24
        m = cur[int(rng.integers(0, 4))] + octave
        if t < STARTS[2] or rng.random() < 0.55:        # sparser after the growth
            add(tone(midi(m), 2.2, 0.004, 0.55, (1, 0.5, 0.2, 0.08)), t, 0.045 + 0.02 * rng.random(), rng.uniform(-0.5, 0.5), 0.45)
        t += step
    # a bell as the Opera House card settles
    card = STARTS[2] + 3.6
    add(tone(midi(77), 4.0, 0.003, 1.5, (1, 0.3, 0.15), vib=0.3), card, 0.05, 0.3, 0.6)
    add(tone(midi(84), 4.0, 0.003, 1.2, (1, 0.2)), card + 0.02, 0.025, -0.2, 0.6)
    # a quiet swell into each white dip
    for i in (1, 2):
        at = STARTS[i + 1] - 0.9
        n = int(1.4 * SR); tt = np.arange(n) / SR
        env = np.sin(np.pi * np.minimum(1, tt / 1.4)) ** 2 * (tt < 1.2)
        add(lowpass(rng.standard_normal(n), 900, 4) * env, at, 0.03, 0.0, 0.5)

    mix = dry + reverb(send, 2.6, 1.0)
    # master: fade in, fade out, soft limiter
    tt = np.arange(N) / SR
    mix *= np.minimum(1, tt / 0.8) * np.clip((END - tt) / 2.4, 0, 1)
    mix = np.tanh(mix / 0.35) * 0.35
    mix *= 0.55 / max(np.max(np.abs(mix)), 1e-9)
    from scipy.io import wavfile
    wavfile.write(os.path.join(HERE, "music.wav"), SR, (mix.T * 32767).astype(np.int16))
    print("music.wav", f"{N / SR:.1f}s", flush=True)


def score(src, offset=0.0, gain_db=0.0):
    """Use a generated track as the score: cut from offset, fade in 0.3 s, fade out over the last 2.5 s, loudness-normalise."""
    ff("-ss", f"{offset}", "-i", src, "-t", f"{END}",
       "-af", f"afade=t=in:st=0:d=0.3,afade=t=out:st={END - 2.5:.3f}:d=2.5,loudnorm=I=-17:TP=-1.5:LRA=11,volume={gain_db}dB",
       "-ar", str(SR), "-ac", "2", os.path.join(HERE, "music.wav"))
    print("music.wav from", src, "at", offset, flush=True)


def final():
    ff("-i", os.path.join(HERE, "base.mp4"),
       "-framerate", str(FPS), "-i", os.path.join(HERE, "ovl-hook", "%04d.png"),
       "-framerate", str(FPS), "-i", os.path.join(HERE, "ovl-outro", "%04d.png"),
       "-i", os.path.join(HERE, "music.wav"),
       "-filter_complex",
       f"[2:v]setpts=PTS+{OUTRO[0]:.4f}/TB[o];[0:v][1:v]overlay=0:0:eof_action=pass[a];[a][o]overlay=0:0:eof_action=pass[v]",
       "-map", "[v]", "-map", "3:a", "-t", f"{END:.3f}", "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p",
       "-c:a", "aac", "-b:a", "192k", "-movflags", "+faststart", os.path.join(OUT, "brag.mp4"))
    print("brag.mp4", f"{END:.2f}s", flush=True)


def poster(t=None):
    t = 1.7 if t is None else t
    ff("-ss", f"{t:.3f}", "-i", os.path.join(OUT, "brag.mp4"), "-frames:v", "1", "-q:v", "2", os.path.join(OUT, "brag.jpg"))
    ff("-i", os.path.join(OUT, "brag.mp4"), "-i", os.path.join(OUT, "brag.jpg"),
       "-filter_complex", "[0:v][1:v]overlay=0:0:enable='eq(n,0)'[v]", "-map", "[v]", "-map", "0:a?",
       "-c:v", "libx264", "-crf", "17", "-preset", "slow", "-pix_fmt", "yuv420p", "-c:a", "copy", "-movflags", "+faststart",
       os.path.join(OUT, "brag.poster.mp4"))
    os.replace(os.path.join(OUT, "brag.poster.mp4"), os.path.join(OUT, "brag.mp4"))
    print("poster at", t, flush=True)


if __name__ == "__main__":
    steps = sys.argv[1:] or ["all"]
    for s in steps:
        if s in ("shots", "all"): shots()
        if s in ("overlay", "all"): overlay()
        if s in ("music", "all"): music()
        if s.startswith("score="):
            src, _, off = s[6:].partition("@"); score(src, float(off or 0))
        if s in ("final", "all"): final()
        if s in ("poster", "all"): poster()
        if s == "times": print(STARTS, END)
