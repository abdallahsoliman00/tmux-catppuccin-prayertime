# tmux-prayer-plugin

A small tmux plugin that adds the time remaining until the next prayer to a
Catppuccin tmux status line. It retrieves the five daily prayer times from the
[Aladhan Prayer Times API](https://aladhan.com/prayer-times-api), caches them
for the location's current day, and refreshes the cache at local midnight.

The status segment looks like `P Fajr 02:14` (the `P` is the segment icon;
the time is hours and minutes remaining). Sunrise is not treated as a prayer.
After Isha, the next Fajr countdown uses today's Fajr clock time as an estimate,
because the plugin only requests that day's schedule.

## Requirements

- tmux 3.2 or newer
- Python 3.9 or newer (including `zoneinfo`)
- Catppuccin/tmux v2
- Network access to `api.aladhan.com` when the daily cache is refreshed

## Configuration

Set decimal coordinates and add the component to the Catppuccin status line.
Load this plugin after Catppuccin/tmux so its `@thm_mauve` theme color is
available:

```tmux
set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'

# Add after Catppuccin/tmux has been loaded:
set -ag status-right '#{E:@catppuccin_status_prayer}'
```

The status option is named `@catppuccin_status_prayer`. The segment uses the
Catppuccin mauve foreground and displays `P` followed by the next prayer name
and remaining time. If coordinates are missing, invalid, or the cache is not
ready yet, it displays `P --:--` (an invalid/missing location prevents the
background updater from making requests).

## Install with TPM

Add the plugin after Catppuccin and before TPM's initialization in
`~/.tmux.conf`:

```tmux
set -g @plugin 'catppuccin/tmux#v2.3.0'
set -g @plugin 'YOUR_GITHUB_USER/tmux-prayer-plugin'

set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'
set -ag status-right '#{E:@catppuccin_status_prayer}'

run '~/.tmux/plugins/tpm/tpm'
```

Replace `YOUR_GITHUB_USER` with the account that hosts this repository. Install
the plugin with `prefix` + <kbd>I</kbd>, then reload tmux or restart the tmux
server. If you already have a Catppuccin status line, append the prayer
component wherever you want it to appear, for example:

```tmux
set -g status-right "#{E:@catppuccin_status_directory} #{E:@catppuccin_status_prayer} #{E:@catppuccin_status_date_time}"
```

## Manual installation

Clone the repository and source its tmux entry point. Keep the coordinate
options and status-line append after Catppuccin is configured:

```sh
git clone https://github.com/YOUR_GITHUB_USER/tmux-prayer-plugin.git \
  ~/.tmux/plugins/tmux-prayer-plugin
```

```tmux
set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'
run '~/.tmux/plugins/tmux-prayer-plugin/prayer.tmux'
set -ag status-right '#{E:@catppuccin_status_prayer}'
```

Reload the tmux configuration or restart the tmux server to start the updater.
The plugin uses Python's standard library and stores location-specific cache
files under `${XDG_CACHE_HOME:-~/.cache}/tmux-prayer-plugin/`.
