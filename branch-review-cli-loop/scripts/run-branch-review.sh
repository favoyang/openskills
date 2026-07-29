#!/usr/bin/env bash
set -uo pipefail

base="${1:-main}"
if [[ $# -gt 0 ]]; then
  shift
fi

if ! git rev-parse --show-toplevel >/dev/null 2>&1; then
  echo "Run this command from inside a Git repository." >&2
  exit 2
fi
if ! git rev-parse --verify "${base}^{commit}" >/dev/null 2>&1; then
  echo "Unknown review base: ${base}" >&2
  exit 2
fi
if ! command -v codex >/dev/null 2>&1; then
  echo "Missing codex CLI." >&2
  exit 2
fi

untracked="$(git ls-files --others --exclude-standard)"
if [[ -n "${untracked}" ]]; then
  echo "Untracked files are invisible to codex review:" >&2
  printf '%s\n' "${untracked}" >&2
  echo "Use git add -N with exact intended paths, or ignore unrelated generated files, then retry." >&2
  exit 2
fi

models_csv="${BRANCH_REVIEW_MODELS:-gpt-5.6-sol,gpt-5.5,gpt-5.4}"
IFS=',' read -r -a models <<<"${models_csv}"
attempted=()
tmp_root="${TMPDIR:-/tmp}"

for raw_model in "${models[@]}"; do
  model="${raw_model#"${raw_model%%[![:space:]]*}"}"
  model="${model%"${model##*[![:space:]]}"}"
  [[ -n "${model}" ]] || continue
  attempted+=("${model}")
  if ! log="$(mktemp "${tmp_root%/}/branch-review.XXXXXX")"; then
    echo "Could not allocate a temporary review log." >&2
    exit 2
  fi
  echo "Starting fresh branch review with ${model} against ${base}..." >&2
  codex -m "${model}" review --base "${base}" "$@" 2>&1 | tee "${log}"
  status="${PIPESTATUS[0]}"
  if [[ "${status}" -eq 0 ]]; then
    rm -f "${log}"
    echo "Branch reviewer model: ${model}" >&2
    exit 0
  fi

  if grep -Eqi \
    "requires a newer version of Codex|model .* (is )?(unavailable|unsupported|not supported|not found)|unknown model|does not exist or you do not have access" \
    "${log}"; then
    echo "${model} is unavailable; trying the next configured model." >&2
    rm -f "${log}"
    continue
  fi

  echo "Review failed for a non-model reason; not falling back." >&2
  rm -f "${log}"
  exit "${status}"
done

echo "No configured branch review model could run. Attempted: ${attempted[*]}" >&2
exit 2
