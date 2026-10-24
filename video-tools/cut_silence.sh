#!/usr/bin/env bash
# Вырезает паузы и «мёртвые» места (jump-cut). margin — сколько тишины оставить вокруг фраз.
# Использование: cut_silence.sh input.mp4 output.mp4 [порог, по умолчанию 4%] [margin, по умолчанию 0.15s]
set -euo pipefail
IN="$1"; OUT="$2"; THR="${3:-4%}"; MARGIN="${4:-0.15s}"
"${VENV:-$HOME/venv-video}/bin/auto-editor" "$IN" -o "$OUT" \
  --edit "audio:threshold=$THR" --margin "$MARGIN" --no-open
