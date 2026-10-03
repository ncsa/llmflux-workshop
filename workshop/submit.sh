#!/usr/bin/env bash
# Submit a prompts file to the GPU nodes with llmflux, using the workshop settings.
#
#     bash submit.sh prompts/all.jsonl
#
# This is a thin wrapper: it prints the exact `llmflux run` command before
# running it, so you can see (and later type yourself) every flag involved.
set -euo pipefail

if [[ $# -ne 1 ]]; then
    echo "Usage: bash submit.sh PROMPTS_FILE   (e.g. bash submit.sh prompts/all.jsonl)" >&2
    exit 2
fi
input="$1"
if [[ ! -f "$input" ]]; then
    echo "No such file: $input  (did you run make_prompts.py first?)" >&2
    exit 1
fi
if [[ -z "${WORKSHOP_ACCOUNT:-}" ]]; then
    echo "Workshop settings aren't loaded. Run:  source ~/llmflux-workshop/workshop.env" >&2
    exit 1
fi

# Refuse to continue on the wrong cluster: a job submitted from Delta with
# DeltaAI's partition (or the reverse) fails with an error that's hard to
# decode on your first day. Matches login and compute node names, so this also
# works from an Open OnDemand Jupyter or VS Code session; unknown hosts pass.
check_system() {
    local host="${WORKSHOP_HOSTNAME:-$(hostname)}" wrong=""
    case "$WORKSHOP_SYSTEM" in
        delta)   [[ "$host" == gh-* || "$host" == gh[0-9]* || "$host" == dtai-* ]] && wrong=DeltaAI ;;
        deltaai) [[ "$host" == dt-* || "$host" == gpu[a-z][0-9]* || "$host" == cn[0-9]* ]] && wrong=Delta ;;
    esac
    if [[ -n "$wrong" ]]; then
        local right="Delta (login.delta.ncsa.illinois.edu)"
        [[ "$WORKSHOP_SYSTEM" == deltaai ]] && right="DeltaAI (dtai-login.delta.ncsa.illinois.edu)"
        echo "This workshop runs on $right, but you're logged in to $wrong ($host)." >&2
        echo "Log out, log in to the right system, and run this again." >&2
        exit 1
    fi
}
check_system

name="$(basename "$input" .jsonl)"
# Anchor results to the workshop directory so they land in one place no matter
# which directory you submit from.
output="${LLMFLUX_WORKSPACE:-$PWD}/results/$name.json"
cmd=(llmflux run
     --model "$WORKSHOP_MODEL"
     --input "$input"
     --output "$output"
     --account "$WORKSHOP_ACCOUNT"
     --partition "$WORKSHOP_PARTITION"
     --time "$WORKSHOP_TIME")
if [[ -n "${WORKSHOP_RESERVATION:-}" ]]; then
    cmd+=(--sbatch-arg "reservation=$WORKSHOP_RESERVATION")
fi

echo "Running:"
printf ' '
printf ' %q' "${cmd[@]}"
echo
echo
exec "${cmd[@]}"
