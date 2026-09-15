from __future__ import annotations

import math
import struct
import wave
from pathlib import Path


class AudioService:
    """Dialogue-free deterministic fallback audio. A dedicated ASMR provider can replace this later."""

    def create_track(self, output: Path, duration: float = 90.0) -> Path:
        output.parent.mkdir(parents=True, exist_ok=True)
        rate = 16000
        frames = int(rate * duration)
        with wave.open(str(output), "wb") as wav:
            wav.setnchannels(1)
            wav.setsampwidth(2)
            wav.setframerate(rate)
            block = bytearray()
            for i in range(frames):
                t = i / rate
                # Very low-level layered tones/noise: intentionally no speech.
                hum = 700 * math.sin(2 * math.pi * 0.18 * t)
                ripple = 350 * math.sin(2 * math.pi * 2.1 * t)
                sample = int(max(-3000, min(3000, hum + ripple)))
                block.extend(struct.pack("<h", sample))
                if len(block) >= rate * 2:
                    wav.writeframes(block)
                    block.clear()
            if block:
                wav.writeframes(block)
        return output
