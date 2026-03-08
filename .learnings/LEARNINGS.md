# LEARNINGS

## [LRN-20260309-001] correction

**Logged**: 2026-03-09T01:47:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs

### Summary
For concrete location answers in China, never infer district/street from raw coordinates; always reverse geocode first.

### Details
I initially eyeballed the Find My coordinates and said the device was around West Lake District / Jiangcun / Wenxin. The user then asked for an AMap reverse lookup, which showed the correct location was Xiaoshan District, Yingfeng Subdistrict, Airport City Avenue. The manual estimate was wrong and sounded overconfident.

### Suggested Action
Use AMap reverse geocoding by default for China location answers before naming a district, street, compound, or landmark.

### Metadata
- Source: user_feedback
- Related Files: TOOLS.md, memory/2026-03-09.md
- Tags: correction, location, amap, reverse-geocode
- Pattern-Key: location.no-eyeballing-admin-areas

---

## [LRN-20260309-002] best_practice

**Logged**: 2026-03-09T01:47:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs

### Summary
For camera capture, explicitly distinguish the source that actually succeeded instead of implying the built-in Mac camera was used.

### Details
The first successful captures came from iPhone Continuity Camera and Desk View, but my wording made it sound like I had already captured from the Mac camera. Later I isolated device 0 and successfully captured from the built-in FaceTime camera. The user noticed the mismatch immediately.

### Suggested Action
Enumerate AVFoundation devices first, then report the exact source that succeeded: built-in camera, Continuity Camera, or Desk View. If fallback is used, say so before presenting the image.

### Metadata
- Source: user_feedback
- Related Files: TOOLS.md, memory/2026-03-09.md
- Tags: camera, avfoundation, correction, continuity-camera
- Pattern-Key: camera.report-actual-source

---

## [LRN-20260309-003] correction

**Logged**: 2026-03-09T01:47:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs

### Summary
Do not reply with bare NO_REPLY after the user acknowledges receipt; send a short explicit confirmation.

### Details
After the user replied "ok" to the image handoff, I returned NO_REPLY. This looked broken and the user immediately responded with a question mark. There was already a prior preference note about not using bare NO_REPLY in this kind of situation, and I still missed it.

### Suggested Action
When the user acknowledges delivered content, send one brief natural confirmation or next-step offer instead of NO_REPLY.

### Metadata
- Source: user_feedback
- Related Files: memory/2026-03-07.md, TOOLS.md, memory/2026-03-09.md
- Tags: messaging, correction, no-reply, acknowledgment
- See Also: 2026-03-07 preference note
- Pattern-Key: messaging.no-no_reply-after-ack

---

## [LRN-20260309-004] best_practice

**Logged**: 2026-03-09T01:47:00+08:00
**Priority**: medium
**Status**: promoted
**Area**: docs

### Summary
When explaining macOS camera permission attribution, treat host-app attribution as a hypothesis unless process evidence is checked.

### Details
The user asked why macOS showed Cursor accessing the camera. I gave a plausible explanation, but later process inspection showed the active execution chain was openclaw-gateway -> zsh -> command process, while Cursor still had related helper processes alive. The likely explanation is host attribution in macOS privacy UI, but that should be framed carefully instead of as a certainty.

### Suggested Action
Use cautious wording for macOS privacy attribution and verify process ancestry before making strong claims.

### Metadata
- Source: user_feedback
- Related Files: TOOLS.md, memory/2026-03-09.md
- Tags: macos, privacy, cursor, camera, attribution
- Pattern-Key: macos.permission-attribution-be-careful

---
## [LRN-20260309-005] best_practice

**Logged**: 2026-03-09T02:04:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs

### Summary
When multi-agent collaboration starts, send an immediate kickoff status update instead of silently running in the background.

### Details
The user explicitly said that when multiple models/agents are working, they want timely visibility into what is happening. Silent background orchestration makes it unclear whether work actually started, how it was split, and when to expect the next update.

### Suggested Action
For any multi-agent workflow, send a startup update that includes: started status, participating models/roles, task goal, and expected next report time. Continue with periodic progress reports and a final summary.

### Metadata
- Source: user_feedback
- Related Files: USER.md, memory/2026-03-09.md
- Tags: multi-agent, reporting, workflow, transparency
- Pattern-Key: multiagent.report-on-start

---
## [LRN-20260309-006] best_practice

**Logged**: 2026-03-09T02:17:00+08:00
**Priority**: high
**Status**: promoted
**Area**: docs

### Summary
Frame the multi-model system as a proper studio, not casual AI collaboration, and run it with small-company standards.

### Details
The user explicitly wants the system renamed and re-framed as a "工作室". That means formal roles, process discipline, reporting cadence, quality control, review, acceptance, and delivery standards. Casual ad-hoc orchestration is not acceptable.

### Suggested Action
Use "工作室" as the default term. For studio-mode work, enforce clear role assignments, kickoff updates, stage reports, risk escalation, review, acceptance, and delivery-quality expectations.

### Metadata
- Source: user_feedback
- Related Files: USER.md, memory/2026-03-09.md
- Tags: studio, workflow, organization, reporting, quality
- Pattern-Key: studio.not-multi-ai-collab

---
