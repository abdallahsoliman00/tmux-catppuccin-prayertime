# tmux-prayer-plugin

Adds a countdown to the next daily prayer to the [Catppuccin/tmux](https://github.com/catppuccin/tmux) status line. Prayer times come from the [Aladhan API](https://aladhan.com/prayer-times-api) and are cached locally. Sunrise is excluded; after Isha, tomorrow's Fajr uses today's time as an estimate.

## Requirements

- tmux 3.2+
- Python 3.9+
- Catppuccin/tmux v2
- Internet access to `api.aladhan.com` for the daily refresh

## Install with TPM

Add these lines to `~/.tmux.conf`, replacing the example coordinates with your location's decimal latitude and longitude:

```tmux
set -g @plugin 'catppuccin/tmux#v2.3.0'
set -g @plugin 'abdallahsoliman00/tmux-prayer-plugin'
set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'
set -ag status-right '#{E:@catppuccin_status_prayer}'

run '~/.tmux/plugins/tpm/tpm'
```

Reload tmux, then press your TPM install key (default: `prefix` + `I`). Keep the prayer plugin after Catppuccin and before TPM's `run` line. To combine it with other segments, include `#{E:@catppuccin_status_prayer}` in your existing `status-right` setting.

## Manual install

Clone the repository:

```sh
git clone https://github.com/abdallahsoliman00/tmux-prayer-plugin.git ~/.tmux/plugins/tmux-prayer-plugin
```

After Catppuccin is configured, add the coordinate settings and source the plugin in `~/.tmux.conf`:

```tmux
set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'
run '~/.tmux/plugins/tmux-prayer-plugin/prayer.tmux'
set -ag status-right '#{E:@catppuccin_status_prayer}'
```

Reload tmux. The segment displays `--:--` until its first successful refresh. The plugin uses Python's standard library and stores its cache in `${XDG_CACHE_HOME:-~/.cache}/tmux-prayer-plugin/`.
