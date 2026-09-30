# Standard prompt

Attach all 6 images from `data/` (`a.jpg`, `b.jpg`, `c.png`, `d.jpg`, `e.jpg`, `f.jpg`) in that order, then send this exact text in the same message. Use this prompt for every experiment. Copy everything between the lines.

---

I have attached 6 photos of bookshelves, named a, b, c, d, e and f (in that order).

For each photo, list every book whose title you can read.

Rules:
- Only include a book if you can actually read its title in that photo. Do not guess, and do not add books that are likely to be there but whose titles you cannot read.
- Keep the photos separate. List each book under the photo it appears in.
- If several copies of the same book are visible in a photo, list it once.
- Include the author if you can read it or are confident who wrote the book. Otherwise use null.
- Write titles as they appear on the book, in their original language and script.

Reply with only this JSON and nothing else:

{
  "a": {"difficulty": "easy", "books": [{"title": "...", "author": "..."}]},
  "b": {"difficulty": "easy", "books": []},
  "c": {"difficulty": "medium", "books": []},
  "d": {"difficulty": "medium", "books": []},
  "e": {"difficulty": "hard", "books": []},
  "f": {"difficulty": "hard", "books": []}
}

---
