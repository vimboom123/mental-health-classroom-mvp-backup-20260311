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

Why:
- bare CLI runs may inherit a PATH without `/usr/sbin`
- then both Gemini and Oracle can fail at startup with `spawnSync sysctl ENOENT`
- Gemini also requires a compatible `~/.gemini/settings.json`

## wttr Fallback

```bash
curl -s "http://wttr.in/Hangzhou?format=3"
```
