# Where to put new sign videos

This project reads video clips from **two different folders**, for two
different purposes. Getting the right one right matters — a video in the
wrong place, or named the wrong way, gets silently ignored rather than
causing an obvious error.

## 1. `web_ui/sign_clips/` — the ONE example used for the "type/speak to sign" feature and skeleton animation

This is your canonical, representative clip per letter/number — the one
actually used when someone types or speaks a word and sees it signed back.

**Two accepted layouts — use whichever is easiest:**

```
web_ui/sign_clips/A.mp4              <- a flat file, named exactly after the label
```
or
```
web_ui/sign_clips/A/take1.mp4        <- a folder named after the label, containing one file
```

If a folder contains more than one file, only the first one (alphabetically)
is used as the canonical clip — the rest are simply ignored for this
feature (though see below, they're NOT ignored for training).

**What NOT to do** (this was the mistake found and fixed just now):
```
web_ui/sign_clips/D__Wisdom__2026-09-20.mp4    <- WRONG: not a recognised label
```
A raw filename straight out of the data collector tool (like
`D__Wisdom__timestamp.mp4`) won't be recognised on its own — it needs to
either be renamed to `D.mp4`, or placed inside a `D/` folder.

## 2. `data/raw_videos/<LABEL>/` — as MANY takes as you want, for training

This is where extra recordings genuinely improve the recognition model —
different attempts, different lighting, different signers. Any number of
files, any names you like:

```
data/raw_videos/A/take1.mp4
data/raw_videos/A/take2.mp4
data/raw_videos/A/attempt_from_friend.mp4
```

## How to actually add a new letter/number going forward

1. Record it with the data collector tool (or any camera)
2. Rename it to `<LABEL>.mp4` (e.g. `D.mp4`), or put it in a `<LABEL>/`
   folder inside `web_ui/sign_clips/`
3. **Optional but recommended:** also copy it (or additional takes) into
   `data/raw_videos/<LABEL>/` for extra training data
4. Run, in order:
   ```bash
   python src/extract_sign_animations.py     # updates the animation feature
   python src/extract_frames_from_clips.py   # pulls training frame(s) from your clips
   python src/extract_landmarks.py           # rebuilds the full landmark dataset
   python src/train_classifier.py            # retrains the model
   ```

## Known quirk with older `.webm` recordings

Some earlier clips (recorded as `.webm`) report a nonsense frame rate to
the video-processing tools (`1000fps` instead of a real value). This is
already handled automatically — the scripts detect this and fall back to
a sensible 24fps — but it's why you might see a "reported an implausible
fps" note in the output for older clips specifically. Newer `.mp4`
recordings from the data collector don't have this issue.

## A mistake made and fixed while preparing this update

While testing the fix described above, an early version of this session
ran a cleanup command that deleted this project's existing `data/raw/`
photos in a temporary working copy, before realising it was unnecessary
and re-doing the work from your original, untouched upload. Your actual
files were never at risk — this is noted here only for transparency about
what happened during the fix, not because anything in your project was lost.
