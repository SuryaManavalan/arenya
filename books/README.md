# books/

```
books/book<N>/
  chapters/c<CC>.md     finished chapters (human-written openers, then the Author's revisions)
  drafts/c<CC>/s<SS>.md the Author's per-scene first drafts
  README.md             title, chapter list, synopsis (written when the book ends)
```

Human-written chapters use this frontmatter:

```markdown
---
book: 1
chapter: 1
title: <title>
pov: [<character ids>]
source: human
status: final
---
```

Their voice, tense and POV conventions set the style for the whole series (see `rules/author.md`).
