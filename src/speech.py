"""
speech.py
---------
Minimal text-to-speech helper: speaks a word aloud WITHOUT blocking the
caller, so the webcam loop keeps running (capturing frames, staying
responsive) while the word is being spoken — otherwise the video would
visibly freeze for a moment every time it talks.

Current implementation: macOS only, using the built-in `say` command via
a background process. This was chosen deliberately over a Python TTS
library (e.g. pyttsx3) for reliability: pyttsx3 has known, somewhat fiddly
issues combining background threads with macOS's speech synthesis engine,
whereas `say` is a simple, dependency-free, reliably non-blocking command
already built into every Mac.

TODO before deploying to Windows/Linux users (e.g. a pilot school on
Windows machines): this will currently just print a message instead of
speaking. Swap in a cross-platform library (pyttsx3, or a per-OS command
like PowerShell's System.Speech on Windows) at that point.
"""

import subprocess
import sys


def speak(text):
    """
    Speak `text` aloud asynchronously (returns immediately, doesn't wait
    for speech to finish).
    """
    if not text:
        return

    if sys.platform == "darwin":
        # Popen (not run/call) is what makes this non-blocking — the
        # webcam loop continues immediately instead of freezing until
        # the word finishes being spoken.
        subprocess.Popen(["say", text])
    else:
        print(f"[speech not yet configured for this OS — would say]: {text}")
