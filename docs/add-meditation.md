# Adding a new meditation (audio + transcript)

Step-by-step recipe for adding a guided-meditation recording to the app
and generating the time-aligned transcript that shows up as the "words"
band in the Playground sequence editor. Written for a future session
with zero context — follow it literally.

## 1. Add the audio

1. Drop the recording into the repo's `media/` folder (gitignored, but
   `rpi/scripts/deploy.sh` rsyncs it to the Pi's `/opt/here/media/`).
   WAV preferred; name it `meditation<N>.wav`.
2. Register it in `software/orchestrator/config.py` →
   `DEFAULT_CONFIG["audio"]["meditation"]["items"]`:

   ```python
   {"id": "med3", "label": "Meditation 3 [Name]",
    "file": "meditation3.wav", "enabled": False, "sequence": None},
   ```

3. **GOTCHA — the Pi won't see a DEFAULT_CONFIG list change.**
   Config saves diffs since 2026-07 (untouched settings track shipped
   defaults), but lists merge WHOLESALE — and toggling any meditation in
   the UI persists the whole `items` list as an override. Once that has
   happened (it has), a new default item never shows up on the Pi. Add
   the item to the live list by editing the saved file with the service
   stopped (there is no append API):

   ```bash
   ssh here@here.local
   sudo systemctl stop here-orchestrator
   python3 - <<'EOF'
   import json
   p = "/opt/here/config.json"
   cfg = json.load(open(p))
   items = cfg["audio"]["meditation"]["items"]
   if not any(i["id"] == "med3" for i in items):
       items.append({"id": "med3", "label": "Meditation 3 [Name]",
                     "file": "meditation3.wav", "enabled": False,
                     "sequence": None})
   json.dump(cfg, open(p, "w"), indent=2)
   EOF
   sudo systemctl start here-orchestrator
   ```

   (Scalar defaults now propagate fine thanks to diff-saving; the trap
   is specifically LISTS the UI has ever written — `items`, `targets`,
   palettes. If a new default "doesn't take" on the Pi, look for that
   key in `/opt/here/config.json` and fix it with the service stopped.)

## 2. Transcribe it (whisper.cpp on the Mac)

Tooling: `brew install whisper-cpp ffmpeg`, plus two model files
(~470 MB total — cache them somewhere persistent):

```bash
curl -L -o ggml-small.bin \
  https://huggingface.co/ggerganov/whisper.cpp/resolve/main/ggml-small.bin
curl -L -o silero-vad.bin \
  https://huggingface.co/ggml-org/whisper-vad/resolve/main/ggml-silero-v5.1.2.bin
```

Then:

```bash
# whisper wants 16 kHz mono
ffmpeg -i media/meditation3.wav -ar 16000 -ac 1 /tmp/med3-16k.wav

whisper-cli -m ggml-small.bin -f /tmp/med3-16k.wav \
    -oj -of /tmp/med3 -ml 30 -sow \
    --vad --vad-model silero-vad.bin
```

Flag notes (all matter):
- `--vad` + `--vad-model` — **essential**. Without VAD the first segment
  absorbs the leading silence (a 0→21 s "hello"), and quiet openings get
  dropped entirely.
- `-ml 30 -sow` — split segments at ~30 chars on word boundaries, so
  phrases are short enough to render along the timeline.
- `-oj` — JSON output with per-segment ms offsets.
- Language auto-detects; add `-l en` to pin it.

## 3. Convert to the sidecar schema

The app serves `media/<audiofile>.transcript.json` (exact name: the
audio filename + `.transcript.json`) with this shape:

```json
{"language": "en", "source": "whisper.cpp small + silero-vad",
 "segments": [{"start": 6.21, "end": 10.25, "text": "Hello friend"}]}
```

Converter (whisper JSON → sidecar):

```bash
python3 - <<'EOF'
import json
d = json.load(open("/tmp/med3.json"))
out = {
    "language": (d.get("result") or {}).get("language") or "en",
    "source": "whisper.cpp small + silero-vad",
    "segments": [
        {"start": round(s["offsets"]["from"] / 1000.0, 2),
         "end": round(s["offsets"]["to"] / 1000.0, 2),
         "text": s["text"].strip()}
        for s in d.get("transcription", []) if s.get("text", "").strip()
    ],
}
with open("media/meditation3.wav.transcript.json", "w") as f:
    json.dump(out, f, indent=1, ensure_ascii=False)
print(len(out["segments"]), "segments")
EOF
```

Sanity-read the output — whisper slips occasionally ("fixing your
shoulders" for "relaxing your shoulders"); fix typos directly in the
sidecar JSON, timestamps don't need to change.

## 4. Deploy + verify

```bash
./rpi/scripts/deploy.sh          # rsyncs media/ + code, restarts service
curl -s http://here.local:8000/api/playground/transcript/med3 | head -c 300
```

A 200 with segments means done. In the admin Playground tab, pick the
meditation in "Score this meditation" — the waveform fills the editor
and the words band appears under the ruler (clicking a phrase cues the
playhead there). 404 "no transcript" = sidecar filename doesn't match
the audio filename; 404 "no audio" = the item isn't in the live config
(see the GOTCHA in step 1).

## Where the moving parts live

- Serving: `GET /api/playground/transcript/{med_id}` in
  `software/orchestrator/admin/routes/playground.py` (reads the sidecar
  next to the audio; no caching, edits show up on refresh).
- Words band UI: `admin/static/admin.js` (`fetchTranscript`, the
  `transH()` band in `drawTimeline`).
- Meditation playback state machine: `software/orchestrator/meditation.py`.
- Tests: `tests/test_admin_routes.py` (`test_transcript_*`).
