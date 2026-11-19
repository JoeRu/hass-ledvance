# Changelog

## 0.2.3

- Fix mixed white/RGB ceiling lights (DP51 `mix_rgbcw`) becoming unavailable as soon as the LAN scan found them: their LAN status reply omits DP51 and other DPs, and the poll replaced the known state with that subset. LAN polls now merge onto the known DPs, and DP51 is requested explicitly so it stays current without cloud calls.

## 0.2.2

- Run full cloud discovery (homes, rooms, device list, per-device metadata) every 10 minutes instead of on every 30 s poll and after every command. Devices reachable on LAN now cost no cloud requests per poll; cloud-only devices cost one (`device.get`, which also keeps their online status current and picks up new local keys).
- Keep polling known devices over LAN when cloud discovery fails, retrying discovery after 60 s instead of failing the whole refresh.
- Restore the sanitized warning for rejected logins (error code, endpoint and app client ID) from the Sylvania login change.

## 0.2.1

- Propagate invalid authentication to Home Assistant reauthentication.
- Reject cloud HTTP redirects; avoid exposing signed URLs in request exceptions.
- Convert Tuya decimal scale and measurement units separately for electrical sensors.
- Correct LAN command regression tests for `set_multiple_values` and cover rejection/timeouts.
- Preserve areas manually assigned or cleared in Home Assistant across reloads.
- Bound concurrent cloud/device polling and back off on individual DPS fetch failures.
- Keep cloud discovery on schedule during LAN updates and register capabilities when schemas arrive.
- Isolate invalid device metadata and mark missing device entities unavailable until they return.
- Stop the LAN monitor on unload, including when a refresh is in flight.
- Handle HTTP authentication and rate-limit responses and keep signed URLs out of transport logs.
- Remove Local Key sensors and provide Recorder cleanup guidance for affected upgrades.
- Add regression tests, release checks and contributor attribution.

## 0.2.0

- Upstream baseline and bug fixes as described in the project's existing history.
