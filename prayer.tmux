#!/usr/bin/env bash

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# The expanded option value is a tmux format, so status is read from the
# location-specific cache whenever tmux refreshes the status line.
tmux set-option -g @catppuccin_status_prayer \
  "#[fg=#{@thm_mauve}]  #(python3 '${CURRENT_DIR}/scripts/prayer.py' status '#{@prayer_latitude}' '#{@prayer_longitude}') "

# The updater refreshes immediately when the cache is missing or stale, then
# sleeps until the next midnight in the API-provided location timezone.
tmux run-shell -b \
  "python3 '${CURRENT_DIR}/scripts/prayer.py' daemon '#{@prayer_latitude}' '#{@prayer_longitude}'"

