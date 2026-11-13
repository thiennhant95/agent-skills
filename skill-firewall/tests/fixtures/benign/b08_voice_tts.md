---
name: voice-tts
description: Text-to-speech voice synthesis. Use when the user wants audio narration or voice output.
---

# Voice TTS

Synthesize speech from text using the provider API:

```python
import os
import requests

api_key = os.environ.get("ELEVENLABS_API_KEY")
resp = requests.post(
    "https://api.elevenlabs.io/v1/text-to-speech/voice-1",
    json={"text": text},
    headers={"xi-api-key": api_key},
)
open("out.mp3", "wb").write(resp.content)
```

Example voices: Nova (warm), Onyx (deep). Rate: 1.0x normal speed.
