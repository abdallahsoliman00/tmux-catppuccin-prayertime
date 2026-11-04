#!/usr/bin/env bash

CURRENT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Use Catppuccin's standard icon/text module layout. Keep the command
# substitution unexpanded so the cache is read whenever the status refreshes.
tmux set-option -ogq @catppuccin_prayer_icon " "
tmux set-option -gqF @catppuccin_prayer_color "#{E:@thm_peach}"
tmux set-option -gqF @catppuccin_status_prayer_icon_bg "#{@catppuccin_prayer_color}"
tmux set-option -gqF @catppuccin_status_prayer_icon_fg "#{E:@thm_crust}"
tmux set-option -ogq @catppuccin_prayer_text \
  " #(python3 '${CURRENT_DIR}/scripts/prayer.py' status '#{@prayer_latitude}' '#{@prayer_longitude}')"

tmux set-option -gqF @_ctp_connect_style \
  "#{?#{==:#{@catppuccin_status_connect_separator},yes},,#[bg=default]}"
tmux set-option -gqF @_ctp_module_text_bg "#{E:@catppuccin_status_module_text_bg}"
tmux set-option -gF @catppuccin_status_prayer \
  "#[fg=#{@catppuccin_status_prayer_icon_bg}]#{@_ctp_connect_style}#{@catppuccin_status_left_separator}#[fg=#{@catppuccin_status_prayer_icon_fg},bg=#{@catppuccin_status_prayer_icon_bg}]#{@catppuccin_prayer_icon}#{@catppuccin_status_middle_separator}#[fg=#{@thm_fg},bg=#{@_ctp_module_text_bg}]"
tmux set-option -ag @catppuccin_status_prayer "#{E:@catppuccin_prayer_text}"
tmux set-option -agF @catppuccin_status_prayer \
  "#[fg=#{@_ctp_module_text_bg}]#{@_ctp_connect_style}#{@catppuccin_status_right_separator}"
tmux set-option -u @_ctp_connect_style
tmux set-option -u @_ctp_module_text_bg

# The updater refreshes immediately when the cache is missing or stale, then
# sleeps until the next midnight in the API-provided location timezone.
tmux run-shell -b \
  "python3 '${CURRENT_DIR}/scripts/prayer.py' daemon '#{@prayer_latitude}' '#{@prayer_longitude}'"
