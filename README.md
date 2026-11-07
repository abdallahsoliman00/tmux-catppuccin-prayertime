# tmux-catppuccin-prayertime

![image](./assets/demo.png)

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
set -g @plugin 'abdallahsoliman00/tmux-catppuccin-prayertime'
set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'
set -ag status-right '#{E:@catppuccin_status_prayer}'

run '~/.tmux/plugins/tpm/tpm'
```

Reload tmux, then press your TPM install key (default: `prefix` + `I`). Keep the prayer plugin after Catppuccin and before TPM's `run` line. To combine it with other segments, include `#{E:@catppuccin_status_prayer}` in your existing `status-right` setting.

## Manual install

Clone the repository:

```sh
git clone https://github.com/abdallahsoliman00/tmux-catppuccin-prayertime.git ~/.tmux/plugins/tmux-catppuccin-prayertime
```

After Catppuccin is configured, add the coordinate settings and source the plugin in `~/.tmux.conf`:

```tmux
set -g @prayer_latitude '40.7128'
set -g @prayer_longitude '-74.0060'
run '~/.tmux/plugins/tmux-catppuccin-prayertime/prayer.tmux'
set -ag status-right '#{E:@catppuccin_status_prayer}'
```

Reload tmux. The segment displays `--:--` until its first successful refresh. The plugin uses Python's standard library and stores its cache in `${XDG_CACHE_HOME:-~/.cache}/tmux-catppuccin-prayertime/`.

## Customising the calculation

By default, Aladhan picks the calculation method used by the authority closest to your coordinates. You can change this, and any other calculation setting, by passing your own query parameters to the [`GET /v1/timings/{date}`](https://aladhan.com/prayer-times-api#tag/daily-prayer-times/GET/timings/{date}) endpoint that the plugin calls.

To set a parameter, add a tmux option named `@prayer_` followed by the parameter's exact name. Names are case-sensitive. For example, this uses the Egyptian General Authority of Survey method and the Hanafi Asr:

```tmux
set -g @prayer_latitude '30.0444'
set -g @prayer_longitude '31.2357'
set -g @prayer_method '5'   # Egyptian General Authority of Survey
set -g @prayer_school '1'   # Hanafi
```

| Option | Values | Description |
| --- | --- | --- |
| `@prayer_method` | `0`–`23`, `99` | Calculation method, such as `2` ISNA, `3` Muslim World League, `4` Umm Al-Qura or `5` Egyptian. See [the full list](https://aladhan.com/calculation-methods). |
| `@prayer_methodSettings` | e.g. `18.5,null,17.5` | Custom Fajr angle, Maghrib angle or minutes, and Isha angle or minutes. Requires `@prayer_method '99'`. |
| `@prayer_school` | `0` Shafi (default), `1` Hanafi | Asr juristic school. |
| `@prayer_shafaq` | `general`, `ahmer`, `abyad` | Shafaq type. Only used with method `15` (Moonsighting Committee). |
| `@prayer_latitudeAdjustmentMethod` | `1` middle of the night, `2` one seventh, `3` angle based | Adjustment for high latitudes, such as the UK or Scandinavia. |
| `@prayer_tune` | e.g. `0,2,0,0,0,0,0,-1,0` | Minute offsets applied to Imsak, Fajr, Sunrise, Dhuhr, Asr, Maghrib, Sunset, Isha and Midnight, in that order. Use this to match your local mosque. |
| `@prayer_midnightMode` | `0` standard, `1` Jafari | How midnight is calculated. |
| `@prayer_timezonestring` | e.g. `Europe/London` | Overrides the timezone that Aladhan derives from your coordinates. |
| `@prayer_calendarMethod` | `HJCoSA`, `UAQ`, `DIYANET`, `MATHEMATICAL` | Hijri calendar method. |
| `@prayer_adjustment` | integer, e.g. `-1` | Hijri date adjustment in days. Only used with `MATHEMATICAL`. |

Leave an option unset, or set it to an empty string, to use the API default.

Changes take effect within a minute, with no restart needed: the updater re-reads the `@prayer_*` options on every check and refetches whenever they differ from the cached times. Aladhan quietly falls back to its defaults when it gets an invalid value, so the plugin checks values itself and refuses to fetch with a bad one. To apply your settings straight away and see any errors, run:

```sh
python3 ~/.tmux/plugins/tmux-catppuccin-prayertime/scripts/prayer.py refresh LATITUDE LONGITUDE
```

The command lists the settings it used and warns about any `@prayer_*` option it doesn't recognise, such as a misspelled name.
