# Android capture checklist  (MANUAL — Android not present on this PC)

Support varies by OS/ROM; do not assume identical behavior everywhere.

## 0. Prerequisite — Obsidian Sync
Install Obsidian on Android, open the **SecondBrain** vault via Obsidian Sync.
Sync folder rules: see `docs/REMOTE_ACCESS.md`.

## A. Share → Obsidian
1. In a browser/app: **Share → Obsidian**.
2. Choose vault SecondBrain, create a new note in `raw/inbox/` (attach the URL,
   title, optional comment/tags).
3. Confirm it appears in `raw/inbox/` and syncs.

## B. Web Clipper (compatible browsers)
Install the **Obsidian Web Clipper** extension in a Chromium-based Android browser
that supports extensions (e.g. Kiwi/Edge-class), vault = SecondBrain, folder
`raw/inbox/`. Fallback: plain **Share URL → Obsidian new note**.

## C. Quick note from the phone
Create a note with: title, URL, date, optional tags, origin, comment. The PC
enriches and processes it on the next `process-inbox`.

## Verify end-to-end
```powershell
.\.venv\Scripts\secondbrain process-inbox
```

Status: **MANUAL_PENDING** — run on the Android device and tick each box. Note any
ROM-specific share limitations here.
