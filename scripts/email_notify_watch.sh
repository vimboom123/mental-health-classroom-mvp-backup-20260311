#!/bin/zsh
set -euo pipefail

export PATH="/usr/local/opt/node@22/bin:/Users/vimboom/.npm-global/bin:/usr/local/bin:/usr/bin:/bin:/usr/sbin:/sbin"

STATE_FILE="${HOME}/.openclaw/state/email-watch-state.json"
LEGACY_STATE_FILE="${HOME}/.local/state/openclaw-email-watch.json"
LOCK_DIR="/tmp/openclaw-email-watch.lock"
LOCK_PID_FILE="${LOCK_DIR}/pid"
LOG_FILE="${HOME}/.openclaw/state/email-watch.log"
TELEGRAM_TARGET="8783735951"

mkdir -p "$(dirname "$STATE_FILE")"
mkdir -p "$(dirname "$LOG_FILE")"

log_line() {
  local msg="$1"
  local line="[$(date '+%F %T')] $msg"
  print -r -- "$line" | tee -a "$LOG_FILE"
}

migrate_legacy_state_if_needed() {
  if [[ -f "$STATE_FILE" ]]; then
    return 0
  fi
  if [[ -f "$LEGACY_STATE_FILE" ]]; then
    cp "$LEGACY_STATE_FILE" "$STATE_FILE"
    log_line "migrated legacy state from $LEGACY_STATE_FILE to $STATE_FILE"
  fi
}

ensure_state_shape() {
  if [[ ! -f "$STATE_FILE" ]]; then
    printf '{"initialized":false,"gmail":[],"sorbonne":[],"meta":{"lastScanAt":null,"lastNoticeAt":null,"lastNewCount":0}}\n' > "$STATE_FILE"
    return 0
  fi
  local tmp
  tmp="$(mktemp)"
  jq '
    .initialized = (.initialized // false)
    | .gmail = (.gmail // [])
    | .sorbonne = (.sorbonne // [])
    | .meta = (.meta // {})
    | .meta.lastScanAt = (.meta.lastScanAt // null)
    | .meta.lastNoticeAt = (.meta.lastNoticeAt // null)
    | .meta.lastNewCount = (.meta.lastNewCount // 0)
  ' "$STATE_FILE" > "$tmp"
  mv "$tmp" "$STATE_FILE"
}

acquire_lock() {
  if mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$${}" > "$LOCK_PID_FILE"
    return 0
  fi

  local existing_pid=""
  if [[ -f "$LOCK_PID_FILE" ]]; then
    existing_pid="$(cat "$LOCK_PID_FILE" 2>/dev/null || true)"
  fi

  if [[ -n "$existing_pid" ]] && kill -0 "$existing_pid" 2>/dev/null; then
    log_line "another watcher instance is active (pid=$existing_pid); skip"
    return 1
  fi

  rm -f "$LOCK_PID_FILE" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true

  if mkdir "$LOCK_DIR" 2>/dev/null; then
    printf '%s\n' "$${}" > "$LOCK_PID_FILE"
    return 0
  fi

  return 1
}

cleanup() {
  rm -f "$LOCK_PID_FILE" "$sorbonne_json" "$sorbonne_ids_tmp" "$saved_sorbonne_ids_tmp" "$sorbonne_all_rows_tmp" "$sorbonne_rows_tmp" 2>/dev/null || true
  rmdir "$LOCK_DIR" 2>/dev/null || true
}

load_ids() {
  local source="$1"
  jq -r --arg source "$source" '.[$source][]? // empty' "$STATE_FILE"
}

save_ids() {
  local source="$1"
  local ids_file="$2"
  local tmp
  tmp="$(mktemp)"
  jq --arg source "$source" --rawfile ids_raw "$ids_file" --arg now "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" '
    .initialized = true
    | .[$source] = (($ids_raw | split("\n") | map(select(length > 0)) | unique)[-1000:])
    | .meta.lastScanAt = $now
  ' "$STATE_FILE" > "$tmp"
  mv "$tmp" "$STATE_FILE"
}

update_notice_meta() {
  local new_count="$1"
  local tmp
  tmp="$(mktemp)"
  jq --arg now "$(date -u '+%Y-%m-%dT%H:%M:%SZ')" --argjson count "$new_count" '
    .meta.lastNoticeAt = $now
    | .meta.lastNewCount = $count
  ' "$STATE_FILE" > "$tmp"
  mv "$tmp" "$STATE_FILE"
}

send_notice() {
  local text="$1"
  /Users/vimboom/.npm-global/bin/openclaw message send \
    --channel telegram \
    --target "$TELEGRAM_TARGET" \
    --message "$text" >/dev/null
}

migrate_legacy_state_if_needed
ensure_state_shape

if ! acquire_lock; then
  exit 0
fi

sorbonne_json="$(mktemp)"
sorbonne_ids_tmp="$(mktemp)"
saved_sorbonne_ids_tmp="$(mktemp)"
sorbonne_all_rows_tmp="$(mktemp)"
sorbonne_rows_tmp="$(mktemp)"
trap cleanup EXIT

if ! himalaya -o json envelope list -f INBOX -s 50 'order by date desc' >"$sorbonne_json" 2>/dev/null; then
  printf '[]\n' > "$sorbonne_json"
  log_line "himalaya envelope list failed; using empty result"
fi

jq -r '.[].id' "$sorbonne_json" | awk 'NF' > "$sorbonne_ids_tmp"
jq -c '.[]?' "$sorbonne_json" > "$sorbonne_all_rows_tmp"

initialized="$(jq -r '.initialized // false' "$STATE_FILE")"

if [[ "$initialized" != "true" ]]; then
  save_ids "sorbonne" "$sorbonne_ids_tmp"
  log_line "initialized baseline with current mailbox snapshot"
  send_notice "学校邮箱主动提醒已启动。当前邮件已作为基线记录；接下来只提醒新邮件。"
  update_notice_meta 0
  exit 0
fi

load_ids "sorbonne" > "$saved_sorbonne_ids_tmp"

while IFS= read -r row; do
  [[ -z "$row" ]] && continue
  id="$(printf '%s' "$row" | jq -r '.id')"
  if [[ -s "$saved_sorbonne_ids_tmp" ]] && grep -Fxq -- "$id" "$saved_sorbonne_ids_tmp"; then
    continue
  fi
  printf '%s\n' "$row" >> "$sorbonne_rows_tmp"
done < "$sorbonne_all_rows_tmp"

sorbonne_total="$(wc -l < "$sorbonne_ids_tmp" | tr -d ' ')"
sorbonne_new="$(wc -l < "$sorbonne_rows_tmp" | tr -d ' ')"
log_line "email-watch scan sorbonne_total=$sorbonne_total sorbonne_new=$sorbonne_new state=$STATE_FILE"

save_ids "sorbonne" "$sorbonne_ids_tmp"

if [[ "$sorbonne_new" == "0" ]]; then
  update_notice_meta 0
  exit 0
fi

while IFS= read -r row; do
  [[ -z "$row" ]] && continue
  from_name="$(printf '%s' "$row" | jq -r '.from.name // empty')"
  from_addr="$(printf '%s' "$row" | jq -r '.from.addr // empty')"
  if [[ -n "$from_name" && -n "$from_addr" ]]; then
    from="${from_name} <${from_addr}>"
  elif [[ -n "$from_addr" ]]; then
    from="$from_addr"
  else
    from="${from_name:-未知发件人}"
  fi
  subject="$(printf '%s' "$row" | jq -r '.subject // "(无主题)"')"
  date="$(printf '%s' "$row" | jq -r '.date // ""')"
  send_notice "$(printf '新邮件提醒（Sorbonne）\n发件人: %s\n主题: %s\n时间: %s' "$from" "$subject" "$date")"
done < "$sorbonne_rows_tmp"

update_notice_meta "$sorbonne_new"
log_line "sent $sorbonne_new Sorbonne notices"
