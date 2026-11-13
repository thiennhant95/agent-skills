---
name: pdf-rotate
description: Rotate PDF pages. Use when the user needs to rotate, merge or split PDF documents.
---

# PDF Rotation

Rotate a PDF 90 degrees clockwise:

```bash
python3 scripts/rotate_pdf.py input.pdf output.pdf --degrees 90
```

## Options

- `--degrees 90|180|270` rotation angle
- `--pages 1-3` rotate only selected pages

Example: `python3 scripts/rotate_pdf.py report.pdf out.pdf --degrees 180 --pages 2-4`
