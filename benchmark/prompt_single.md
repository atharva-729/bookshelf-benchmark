# Single-photo prompt

For experiment 2 (one photo per chat). Attach **one** image from `data/` (`e.jpg` or `f.jpg`), then send this exact text in the same message. Copy everything between the lines.

The rules are the same as in the standard prompt ([prompt.md](prompt.md)). Only the parts about several photos are removed.

---

I have attached a photo of a bookshelf.

List every book whose title you can read in the photo.

Rules:
- Only include a book if you can actually read its title in the photo. Do not guess, and do not add books that are likely to be there but whose titles you cannot read.
- If several copies of the same book are visible, list it once.
- Include the author if you can read it or are confident who wrote the book. Otherwise use null.
- Write titles as they appear on the book, in their original language and script.

Reply with only this JSON and nothing else:

{"books": [{"title": "...", "author": "..."}]}

---
