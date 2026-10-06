#!/usr/bin/env python3
"""Turn a brief script (plain text) into an MP3 using Kokoro (offline TTS).

Usage: tts.py SCRIPT.txt OUT.mp3 [--models DIR] [--voice bm_george]
Models (kokoro.onnx, voices.bin) are fetched from GitHub releases if missing.
"""
import argparse, os, subprocess, sys, tempfile, urllib.request
import numpy as np
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import pronounce
import soundfile as sf

REL = "https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0/"
FILES = {"kokoro.onnx": REL + "kokoro-v1.0.int8.onnx", "voices.bin": REL + "voices-v1.0.bin"}


def ensure_models(d):
    os.makedirs(d, exist_ok=True)
    for name, url in FILES.items():
        p = os.path.join(d, name)
        if not os.path.exists(p) or os.path.getsize(p) < 1_000_000:
            subprocess.run(["curl", "-sSL", "--fail", "-o", p, url], check=True)
    return os.path.join(d, "kokoro.onnx"), os.path.join(d, "voices.bin")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("script")
    ap.add_argument("out")
    ap.add_argument("--models", default=os.path.expanduser("~/.cache/kokoro"))
    ap.add_argument("--voice", default="af_heart")
    ap.add_argument("--speed", type=float, default=1.0)
    a = ap.parse_args()

    from kokoro_onnx import Kokoro
    k = Kokoro(*ensure_models(a.models))

    text = open(a.script, encoding="utf-8").read()
    paras = [pronounce.fix(p.strip()) for p in text.split("\n") if p.strip()]
    chunks, sr = [], 24000
    for p in paras:
        samples, sr = k.create(p, voice=a.voice, speed=a.speed, lang=("en-gb" if a.voice.startswith("b") else "en-us"))
        chunks.append(samples)
        gap = 0.9 if len(p) < 60 else 0.6  # longer pause after short transition lines
        chunks.append(np.zeros(int(sr * gap), dtype=samples.dtype))
    audio = np.concatenate(chunks)

    with tempfile.TemporaryDirectory() as td:
        wav = os.path.join(td, "out.wav")
        sf.write(wav, audio, sr)
        subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-i", wav, "-ac", "1",
                        "-af", "loudnorm=I=-16:TP=-1.5:LRA=11", "-ar", "24000",
                        "-codec:a", "libmp3lame", "-b:a", "64k", a.out], check=True)
    print(f"{a.out}: {len(audio)/sr:.0f}s")


if __name__ == "__main__":
    sys.exit(main())
