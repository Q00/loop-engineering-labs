#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -lt 4 ]; then
  echo "usage: run_logged.sh LOG TOOL PURPOSE COMMAND" >&2
  exit 2
fi

log_path="$1"
tool="$2"
purpose="$3"
command_text="$4"
script_dir="$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)"

python3 "$script_dir/record_tool_call.py" "$log_path" "$tool" "$purpose" "$command_text"
bash -lc "$command_text"
