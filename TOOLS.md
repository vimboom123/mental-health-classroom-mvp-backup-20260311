# TOOLS.md - Local Notes

## Search Provider Routing Rules (critical)

- Default search = `web_search` (Brave). Use for quick link lookup, broad discovery, and low-latency checks.
- Use Tavily skill (`~/.openclaw/skills/tavily-search/scripts/search.mjs`) when task needs synthesis quality:
  - user asks for deep summary/research/report
  - user asks for "with sources" / multi-source comparison
  - user asks news analysis instead of just links
- Prefer Brave first, then escalate to Tavily if:
  - Brave results are noisy/duplicated
  - answer needs cleaner AI-ready extraction
  - user asks follow-up "deeper" or "analyze"
- For time-sensitive news, add freshness constraints (Brave freshness or Tavily `--topic news`).
- Keep response transparent: mention provider used only when it affects output quality.

## Weather Runtime Rules (critical)

- For weather questions, always run a live tool call (`exec` or `web_fetch`).
- Never answer weather from memory or with "cannot access real-time weather" unless tool calls actually fail.
- Preferred provider: Open-Meteo (stable on this network).
- Fallback provider: `http://wttr.in` (HTTP only). `https://wttr.in` frequently times out here.
- Primary command to run first:

```bash
~/.openclaw/workspace/scripts/weather_openmeteo.sh <city>
```

## Open-Meteo Commands

1. Geocode city:

```bash
curl -s "https://geocoding-api.open-meteo.com/v1/search?name=Hangzhou&count=1&language=en&format=json"
```

2. Current + forecast:

```bash
curl -s "https://api.open-meteo.com/v1/forecast?latitude=30.29365&longitude=120.16142&current=temperature_2m,apparent_temperature,weather_code,wind_speed_10m&daily=temperature_2m_max,temperature_2m_min,precipitation_probability_max&timezone=Asia%2FShanghai&forecast_days=3"
```

## Media Delivery Rules (critical)

- For chat delivery of local images/files, always use the exact workspace path returned by tools.
- Do not rewrite a tool-returned absolute path to `./outbox/...`.
- Preferred inline form: `MEDIA:~/.openclaw/workspace/outbox/file.png` or the exact absolute `/Users/.../.openclaw/workspace/...` path.
- If a tool already printed a valid `MEDIA:` line or absolute file path, reuse it verbatim.

## Notion Project Snapshot Rules (critical)

- Preferred local helper for studio project base state: `scripts/notion_project_snapshot.sh <project-name>`.
- Current studio projects data source id: `478ee9d7-d1db-4dc7-85d8-7663db95d6ca` (`工作室项目总表`).
- Use this helper before progress reports that need Notion project base state.

## X Trends Runtime Rules (critical)

- Preferred X trends source: `scripts/x_trends_apify.sh` with `APIFY_TOKEN` set.
- Current working actor: `karamelo/twitter-trends-scraper` via Apify sync dataset API.
- Use for X/Twitter trend snapshots in scheduled news reports.
- If Apify actor fails or token is unavailable, fall back to weaker third-party web aggregation and clearly label it as fallback.

## Reviewer CLI Runtime Rules (critical)

- On this machine, do **not** call bare `gemini` or bare `oracle` for reviewer/background multi-agent runs.
- Always use wrappers:
  - `scripts/gemini22.sh`
  - `scripts/oracle22.sh`
  - `scripts/oracle-browser-auto.sh`
- Preferred unified entrypoint:

```bash
scripts/reviewer_dispatch.sh gemini ...
scripts/reviewer_dispatch.sh oracle ...
scripts/reviewer_dispatch.sh oracle-browser ...
```

- Oracle browser reviewer policy:
  - default Oracle reviewer path = `scripts/oracle-browser-auto.sh`
  - wait up to 2 minutes for a first result when useful
  - if still running after 2 minutes, continue main work without blocking
  - if Oracle returns later, still ingest its review and apply relevant fixes
  - when rerunning a similar prompt, use `--force` plus a unique `--slug` to avoid duplicate-prompt blocking

Why:
- bare CLI runs may inherit a PATH without `/usr/sbin`
- then both Gemini and Oracle can fail at startup with `spawnSync sysctl ENOENT`
- Gemini also requires a compatible `~/.gemini/settings.json`

## iCloud Find My

- Apple ID: `leevimboom@gmail.com`
- For user requests about “我的手机地址 / 位置 / 当前位置”, default to querying device `leeee (iPhone 15 Pro)` via the existing `icloud` / Find My workflow.
- Do not ask again for the Apple ID unless the Find My session has actually expired or Apple re-auth is required.
- Do not infer districts/streets from raw coordinates by eyeballing. For any location answer that needs a concrete place name, run reverse geocoding first (prefer AMap for China), then answer from the returned address.

## Camera Capture Runtime Rules (critical)

- When the user asks to “拍一张 / 用摄像头拍”, do not imply the Mac built-in camera was used until capture is confirmed.
- First enumerate available AVFoundation devices, then state clearly which source actually succeeded: built-in Mac camera, iPhone Continuity Camera, or Desk View.
- If the first capture fails and a fallback source is used, explicitly tell the user before presenting the image.
- If replying with attachments/paths and the user acknowledges with “ok/嗯/看到”, do not send `NO_REPLY`; send a short explicit confirmation instead.
- Camera privacy attribution on macOS may surface the host app (for example Cursor) rather than the final CLI binary; avoid overconfident claims about which app macOS will show in permission UI unless process evidence is checked.

## wttr Fallback

```bash
curl -s "http://wttr.in/Hangzhou?format=3"
```
