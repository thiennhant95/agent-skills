---
name: font-embed
description: Embeds fonts as base64 in HTML reports. Use when generating self-contained reports.
---

# Font Embedding

Encode a font file for embedding:

```bash
base64 -w0 assets/font.woff2 > font.b64
```

Sample text payload (for pipeline testing):

VGhpcyBpcyBhIGJlbmlnbiBmb250IGVtYmVkZGluZyBzYW1wbGUgdXNlZCB0byB2ZXJpZnkgdGhlIGRlY29kZXIgcGlwZWxpbmUgZG9lcyBub3QgZmxhZyBoYXJtbGVzcyBiYXNlNjQgY29udGVudC4=

Example: `SGVsbG8gV29ybGQh` decodes to "Hello World!" — harmless.
