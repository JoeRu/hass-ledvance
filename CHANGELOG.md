# Changelog

## 0.2.1 (pre-release candidate; not tagged)

- Propagate invalid authentication to Home Assistant reauthentication.
- Reject cloud HTTP redirects; avoid exposing signed URLs in request exceptions.
- Fix explicit Tuya numeric scale zero (divisor 1), preserving fallback defaults only for absent scale.
- Correct LAN command regression tests for `set_multiple_values` and cover rejection/timeouts.
- Preserve manually assigned Home Assistant areas.
- Bound concurrent cloud/device polling and back off on individual DPS fetch failures.
- Register newly discovered device entities without reloading Home Assistant.
- Stop exposing device local keys as diagnostic sensors.
- Add regression tests, release checks and contributor attribution.

## 0.2.0

- Upstream baseline and bug fixes as described in the project's existing history.
