#!/usr/bin/env bash
# Open, comment, or close the single keepalive issue.
# Usage: keepalive_issue.sh open|comment|close [markdown body]
set -euo pipefail

TITLE="Keepalive: dss-clustering is down"
LABEL="keepalive"
BODY="${2:-}"

find_open() {
  gh issue list --label "$LABEL" --state open --limit 20 \
    --json number,title \
    --jq ".[] | select(.title==\"$TITLE\") | .number" \
    | head -n 1
}

ensure_label() {
  gh label create "$LABEL" --description "Keepalive worker" --color "B60205" 2>/dev/null || true
}

case "${1:-}" in
  find)
    find_open
    ;;
  open)
    ensure_label
    num="$(find_open)"
    if [ -n "$num" ]; then
      gh issue comment "$num" --body "$BODY"
      echo "$num"
    else
      gh issue create --title "$TITLE" --label "$LABEL" --body "$BODY" \
        --json number --jq .number
    fi
    ;;
  comment)
    num="$(find_open)"
    if [ -z "$num" ]; then
      echo "No open keepalive issue" >&2
      exit 1
    fi
    gh issue comment "$num" --body "$BODY"
    echo "$num"
    ;;
  close)
    num="$(find_open)"
    if [ -z "$num" ]; then
      echo "No open keepalive issue" >&2
      exit 0
    fi
    gh issue comment "$num" --body "$BODY"
    gh issue close "$num" --reason completed
    echo "$num"
    ;;
  *)
    echo "Usage: $0 open|comment|close|find [body]" >&2
    exit 2
    ;;
esac
