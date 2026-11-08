# iOS capture checklist  (MANUAL - iPhone not present on this PC)

Goal: a share/clip on the iPhone lands in `raw/inbox/` and syncs to the PC, where
the pipeline processes it.

## 0. Prerequisite - Obsidian Sync
Install Obsidian on iOS, open the **SecondBrain** vault via Obsidian Sync (same
remote vault as the PC). See `docs/REMOTE_ACCESS.md` for the sync folder rules
(do not sync `state/`, `logs/`, `backups/`, `.venv/`, `.git/`, `.env`, `.claude/`).

## A. Share Sheet → Obsidian  (iOS 18+, Obsidian 1.13+)
1. Obsidian iOS → **Settings → Share** (or **Files & Links**): add a capture
   location pointing at `raw/inbox/`, template = the captured-link template.
2. In Safari/any app: **Share → Obsidian → (SecondBrain / raw/inbox)**.
3. Confirm the new note appears in `raw/inbox/` and syncs.

## B. Obsidian Web Clipper (Safari) - full articles
1. Install the **Obsidian Web Clipper** Safari extension
   (https://obsidian.md/help/web-clipper).
2. Set vault = SecondBrain, default folder = `raw/inbox/`, assets = `raw/assets/`.
3. Clip an article → verify it lands in `raw/inbox/`.

## C. Quick Capture / Voice (iOS 26+, Obsidian 1.14+, when available)
Configure the **Quick Capture** / **Voice Capture** widget to save note/transcript
into `raw/inbox/`. See https://obsidian.md/help/ios .

## D. Shortcuts (only if A-C don't fit)
Build an iOS Shortcut that writes a Markdown file into the synced `raw/inbox/`
folder. Do NOT create a public webhook.

## Verify end-to-end
After a capture syncs to the PC:
```powershell
.\.venv\Scripts\secondbrain process-inbox
```
Expect: Scout summary, Jev dedupe/route, Librarian pages, index updated, `wiki/`
syncs back to the phone.

Status: **MANUAL_PENDING** - run the above on the iPhone and tick each box.
