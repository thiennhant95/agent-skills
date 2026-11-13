---
name: weather
description: Get weather forecasts. Use when the user asks about weather or temperature.
---

# Weather

Fetch the forecast for a city:

```bash
curl -s "https://wttr.in/Hanoi?format=3"
```

Example output: `Hanoi: +28 °C, Partly cloudy`

For a 3-day forecast use `curl -s "https://wttr.in/Hanoi"`.
