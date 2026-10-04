# Hosting this for mobile testing

One thing matters more than which host you pick: **phone browsers only allow
camera/mic access (`getUserMedia`) over HTTPS** (or `localhost`, which a
phone can't reach on your laptop). So "just open my laptop's IP address on
my phone" won't work — the camera and mic permission prompts will silently
fail. Both options below give you HTTPS.

---

## Option A — Test on your phone today, no deploy (5 minutes)

Run the server as normal on your laptop, then tunnel it with
[ngrok](https://ngrok.com) (free account, no card needed) so your phone can
reach it over a real HTTPS URL, from anywhere — not just your home WiFi.

```bash
# Terminal 1 — your usual server
source venv/bin/activate
uvicorn src.web_server:app --reload --port 8003

# Terminal 2 — tunnel it
brew install ngrok        # first time only (macOS)
ngrok config add-authtoken <your-token-from-ngrok.com/dashboard>
ngrok http 8003
```

ngrok prints an HTTPS URL like `https://a1b2c3d4.ngrok-free.app`. Open that
on your phone. It only stays live while both terminals are running on your
laptop, and the free tier gives you a new random URL each time you restart
it — good enough for "let me test this on my phone right now," not for
sending a link to someone else to try later.

---

## Option B — A real hosted URL (survives your laptop being closed)

This is the one to use for actual MVP testing with other people. I've added
three files to the project for this: `Dockerfile`, `.dockerignore`, and
`requirements-server.txt` (same as `requirements.txt`, but swaps
`opencv-python` for `opencv-python-headless` — the GUI build of OpenCV
doesn't import on a server with no display attached).

**Railway** is the easiest of the common options — it builds straight from
your Dockerfile and gives you a free HTTPS domain automatically.

1. Push this project to a GitHub repo (if it isn't already). Make sure
   `models/bsl_fingerspelling_mlp.joblib`, `models/label_encoder.joblib`,
   and everything under `web_ui/sign_clips/` and `web_ui/sign_animations/`
   are actually committed — those are what the live site needs; the
   `data/raw/` training images are not (and `.dockerignore` already leaves
   them out of the build).
2. Go to [railway.app](https://railway.app) → New Project → Deploy from
   GitHub repo → pick this repo. Railway detects the `Dockerfile`
   automatically and builds it.
3. Once it deploys, Railway gives you a URL like
   `https://bsl-starter-project-production.up.railway.app` — that's your
   HTTPS link, open it directly on your phone.
4. Free tier note: Railway's free trial credit covers light testing use
   fine; check their current pricing page before leaving it running
   long-term.

**Fly.io** is a close alternative if you'd rather not connect GitHub —
deploys straight from your laptop:

```bash
curl -L https://fly.io/install.sh | sh
fly auth login
fly launch        # detects the Dockerfile, asks a few questions, deploys
fly open           # opens your new HTTPS URL
```

Either way, once it's deployed: open the HTTPS URL on your phone, allow
camera/mic when prompted, and it behaves exactly like your local version —
same model, same UI, same mobile layout.

### A note on size/cost
`web_ui/sign_clips/` is your real recorded video data (~24MB) and ships in
the image since the "type or speak to sign" feature reads from it live —
that's expected and fine for either host's free tier. If the image build
feels slow, it's almost always mediapipe's own wheel downloading (~30-50MB),
not your project.
