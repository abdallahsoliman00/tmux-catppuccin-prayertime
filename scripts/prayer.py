#!/usr/bin/env python3

"""Fetch and display the next prayer time for a configured location."""

from __future__ import annotations

import fcntl
import hashlib
import json
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from datetime import date, datetime, timedelta
from datetime import time as datetime_time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode
from urllib.request import Request, urlopen
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

API_URL = "https://api.aladhan.com/v1/timings/{date}"
PRAYERS = (("Fajr", "Fajr"), ("Dhuhr", "Dhuhr"), ("Asr", "Asr"), ("Maghrib", "Maghrib"), ("Isha", "Isha"))
COORDINATE = re.compile(r"^-?\d+(?:\.\d+)?$")

# Query parameters of GET /v1/timings/{date} that can be set with a tmux option
# named @prayer_<parameter>. See https://aladhan.com/prayer-times-api.
# latitude/longitude are passed on the command line, and iso8601 is not
# supported because the cache expects plain HH:MM times.
OPTION_PREFIX = "@prayer_"
API_PARAMETERS = frozenset(
    {
        "method",
        "methodSettings",
        "shafaq",
        "tune",
        "school",
        "midnightMode",
        "timezonestring",
        "latitudeAdjustmentMethod",
        "calendarMethod",
        "adjustment",
    }
)
NON_API_OPTIONS = frozenset({"latitude", "longitude"})
# The API silently falls back to its defaults for invalid values, which would
# show wrong times without any error, so validate the enumerated ones here.
ALLOWED_VALUES = {
    "method": {str(number) for number in (*range(24), 99)},
    "shafaq": {"general", "ahmer", "abyad"},
    "school": {"0", "1"},
    "midnightMode": {"0", "1"},
    "latitudeAdjustmentMethod": {"1", "2", "3"},
    "calendarMethod": {"HJCoSA", "UAQ", "DIYANET", "MATHEMATICAL"},
}
INTEGER_LIST = re.compile(r"^-?\d+(?:,-?\d+)*$")


def parse_coordinates(latitude: str, longitude: str) -> tuple[float, float]:
    if not COORDINATE.fullmatch(latitude) or not COORDINATE.fullmatch(longitude):
        raise ValueError("latitude and longitude must be decimal numbers")
    lat, lon = float(latitude), float(longitude)
    if not -90 <= lat <= 90 or not -180 <= lon <= 180:
        raise ValueError("latitude must be between -90 and 90 and longitude between -180 and 180")
    return lat, lon


def cache_paths(latitude: float, longitude: float) -> tuple[Path, Path]:
    cache_root = Path(os.environ.get("XDG_CACHE_HOME", Path.home() / ".cache"))
    key = hashlib.sha256(f"{latitude:.6f},{longitude:.6f}".encode()).hexdigest()[:20]
    directory = cache_root / "tmux-prayer-plugin"
    return directory / f"{key}.json", directory / f"{key}.lock"


def tmux(*arguments: str) -> str:
    try:
        result = subprocess.run(
            ("tmux", *arguments), capture_output=True, text=True, check=True, timeout=5
        )
    except subprocess.CalledProcessError as error:
        detail = error.stderr.strip() or f"exit status {error.returncode}"
        raise RuntimeError(f"could not read tmux options: {detail}") from error
    except (OSError, subprocess.SubprocessError) as error:
        raise RuntimeError(f"could not read tmux options: {error}") from error
    return result.stdout


def read_api_parameters() -> tuple[dict[str, str], list[str]]:
    """Return the API parameters set as @prayer_* tmux options.

    The second element lists @prayer_* options that are not recognised API
    parameters, so callers can warn about likely typos.
    """
    parameters, unknown = {}, []
    for line in tmux("show-options", "-g").splitlines():
        name = line.split(maxsplit=1)[0] if line.strip() else ""
        if not name.startswith(OPTION_PREFIX):
            continue
        parameter = name[len(OPTION_PREFIX):]
        if parameter in NON_API_OPTIONS:
            continue
        if parameter not in API_PARAMETERS:
            unknown.append(name)
            continue
        value = tmux("show-options", "-gqv", name).strip()
        if value:
            validate_parameter(name, parameter, value)
            parameters[parameter] = value
    return dict(sorted(parameters.items())), unknown


def validate_parameter(name: str, parameter: str, value: str) -> None:
    allowed = ALLOWED_VALUES.get(parameter)
    if allowed is not None and value not in allowed:
        choices = ", ".join(sorted(allowed, key=lambda item: (len(item), item)))
        raise ValueError(f"{name} must be one of {choices} (got {value!r})")
    if parameter in {"tune", "adjustment"} and not INTEGER_LIST.fullmatch(value):
        raise ValueError(f"{name} must be a comma-separated list of integers (got {value!r})")
    if parameter == "adjustment" and "," in value:
        raise ValueError(f"{name} must be a single integer (got {value!r})")
    if parameter == "timezonestring":
        try:
            ZoneInfo(value)
        except (ZoneInfoNotFoundError, ValueError) as error:
            raise ValueError(f"{name} is not a known timezone (got {value!r})") from error


def fetch_timings(day: date, latitude: float, longitude: float, parameters: dict[str, str]) -> dict:
    query = urlencode({"latitude": latitude, "longitude": longitude, **parameters})
    url = f"{API_URL.format(date=day.strftime('%d-%m-%Y'))}?{query}"
    request = Request(url, headers={"User-Agent": "tmux-prayer-plugin/1.0"})
    try:
        with urlopen(request, timeout=20) as response:
            body = response.read()
    except HTTPError as error:
        # Invalid parameters produce a 4xx whose JSON body explains the problem.
        body = error.read()
    payload = json.loads(body.decode("utf-8"))

    if not isinstance(payload, dict) or payload.get("code") != 200 or not isinstance(payload.get("data"), dict):
        code = payload.get("code") if isinstance(payload, dict) else None
        detail = payload.get("data") if isinstance(payload, dict) else None
        message = f"Aladhan API returned an unexpected response (code {code})"
        if isinstance(detail, str):
            message += f": {detail}"
        raise RuntimeError(message)
    data = payload["data"]
    timezone = data.get("meta", {}).get("timezone", "UTC")
    timings = data.get("timings", {})
    parsed = {}
    for key, _ in PRAYERS:
        value = timings.get(key)
        match = re.match(r"^(\d{1,2}):(\d{2})", str(value))
        if not match:
            raise RuntimeError(f"Aladhan response did not contain a valid {key} time")
        parsed[key] = f"{int(match.group(1)):02d}:{match.group(2)}"
    try:
        ZoneInfo(timezone)
    except (ZoneInfoNotFoundError, TypeError):
        timezone = "UTC"
    return {"date": day.isoformat(), "timezone": timezone, "parameters": parameters, "timings": parsed}


def save_cache(path: Path, payload: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            json.dump(payload, stream)
            stream.write("\n")
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def load_cache(path: Path) -> dict | None:
    try:
        with path.open(encoding="utf-8") as stream:
            cache = json.load(stream)
        if isinstance(cache, dict) and isinstance(cache.get("timings"), dict):
            return cache
    except (OSError, ValueError):
        pass
    return None


def location_now(cache: dict | None) -> datetime:
    try:
        zone = ZoneInfo(cache["timezone"]) if cache else datetime.now().astimezone().tzinfo
    except (KeyError, ZoneInfoNotFoundError, TypeError):
        zone = ZoneInfo("UTC")
    return datetime.now(zone)


def update_for_today(path: Path, latitude: float, longitude: float, parameters: dict[str, str]) -> dict:
    cache = load_cache(path)
    now = location_now(cache)
    # Refetch when the day changes or when the user changes any @prayer_*
    # calculation option.
    if cache and cache.get("date") == now.date().isoformat() and cache.get("parameters", {}) == parameters:
        return cache

    # On first launch the location's timezone is not known until the API
    # responds. Fetch using the host date, then correct if the location is on
    # the other side of midnight.
    result = fetch_timings(now.date(), latitude, longitude, parameters)
    local_date = datetime.now(ZoneInfo(result["timezone"])).date()
    if local_date.isoformat() != result["date"]:
        result = fetch_timings(local_date, latitude, longitude, parameters)
    save_cache(path, result)
    return result


def next_midnight(now: datetime) -> datetime:
    next_day = now.date() + timedelta(days=1)
    return datetime.combine(next_day, datetime_time.min, tzinfo=now.tzinfo)


def run_daemon(path: Path, lock_path: Path, latitude: float, longitude: float) -> None:
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    with lock_path.open("w") as lock:
        try:
            fcntl.flock(lock, fcntl.LOCK_EX | fcntl.LOCK_NB)
        except BlockingIOError:
            return

        while True:
            try:
                # Re-read the options every pass so changes made with
                # `tmux set` take effect without restarting the updater.
                parameters, _ = read_api_parameters()
                cache = update_for_today(path, latitude, longitude, parameters)
                now = datetime.now(ZoneInfo(cache["timezone"]))
                seconds = (next_midnight(now) - now).total_seconds()
                # Recheck periodically rather than sleeping uninterrupted
                # until midnight. This also recovers if the system clock or
                # location timezone changes while the updater is asleep.
                time.sleep(max(1, min(seconds, 60)))
            except (URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
                print(f"tmux-prayer-plugin: refresh failed: {error}", file=sys.stderr, flush=True)
                # Retry transient failures without polling the API continuously.
                time.sleep(60)


def status(path: Path, latitude: float, longitude: float) -> str:
    cache = load_cache(path)
    if not cache:
        return "--:--"
    try:
        now = datetime.now(ZoneInfo(cache["timezone"]))
        if cache.get("date") != now.date().isoformat():
            return "--:--"
        candidates = []
        for key, label in PRAYERS:
            hour, minute = (int(part) for part in cache["timings"][key].split(":", 1))
            prayer_time = now.replace(hour=hour, minute=minute, second=0, microsecond=0)
            if prayer_time > now:
                candidates.append((prayer_time, label))

        if candidates:
            prayer_time, label = min(candidates)
        else:
            # Tomorrow's schedule is intentionally not fetched; use today's
            # Fajr clock time as the best available next-day estimate.
            hour, minute = (int(part) for part in cache["timings"]["Fajr"].split(":", 1))
            tomorrow = now.date() + timedelta(days=1)
            prayer_time = datetime.combine(tomorrow, datetime_time(hour, minute), tzinfo=now.tzinfo)
            label = "Fajr"
        minutes = max(0, math.ceil((prayer_time - now).total_seconds() / 60))
        return f"{label} {minutes // 60:02d}:{minutes % 60:02d}"
    except (KeyError, ValueError, TypeError, ZoneInfoNotFoundError):
        return "--:--"


def main(arguments: list[str]) -> int:
    if len(arguments) != 4 or arguments[1] not in {"status", "daemon", "refresh"}:
        print("usage: prayer.py (status|daemon|refresh) LATITUDE LONGITUDE", file=sys.stderr)
        return 2
    command, latitude_arg, longitude_arg = arguments[1:]
    try:
        latitude, longitude = parse_coordinates(latitude_arg, longitude_arg)
    except ValueError as error:
        if command != "status":
            print(f"tmux-prayer-plugin: {error}", file=sys.stderr)
        return 0 if command == "status" else 2

    path, lock_path = cache_paths(latitude, longitude)
    if command == "status":
        print(status(path, latitude, longitude))
    elif command == "refresh":
        try:
            parameters, unknown = read_api_parameters()
            for name in unknown:
                print(f"tmux-prayer-plugin: ignoring unknown option {name}", file=sys.stderr)
            cache = update_for_today(path, latitude, longitude, parameters)
            settings = ", ".join(f"{key}={value}" for key, value in parameters.items()) or "API defaults"
            print(f"Cached prayer times for {cache['date']} ({cache['timezone']}; {settings})")
        except (URLError, TimeoutError, OSError, RuntimeError, ValueError) as error:
            print(f"tmux-prayer-plugin: refresh failed: {error}", file=sys.stderr)
            return 1
    else:
        run_daemon(path, lock_path, latitude, longitude)
    return 0


if __name__ == "__main__":
    raise SystemExit(main(sys.argv))
