# Writing a new blog post (Markdown workflow)

You don't write HTML by hand. Write a Markdown file in this folder, then ask
Claude to publish it (or convert it yourself following the template in
`blog/*.html`).

This `drafts/` folder is **gitignored** — nothing here is deployed. It's your
local writing workspace.

## 1. Create the Markdown file

One file per post, named like the final URL slug:

    drafts/my-post-slug.md

Start with a front-matter block, then normal Markdown:

```markdown
---
title:   Human-Readable Post Title
date:    Jul 2026
tags:    Storage, Kubernetes        # pick from existing tags or add new ones
summary: One or two sentences shown on the blog index card.
related: https://github.com/...    # optional "related" footer link
minutes: 5                         # optional read-time estimate
---

Intro paragraph...

## A section heading

More paragraphs, `inline code`, **bold**, *italics*.

    # indented or fenced code blocks become styled code boxes
    kubectl get volumesnapshots
```

## 2. Publish it

Tell Claude: *"publish drafts/my-post-slug.md"*. That converts it to
`blog/<slug>.html` in the site's style, adds the card to `blog/index.html`
(with tags wired into the filter), updates `sitemap.xml`, and pushes.

An example of source → published output:

- Source: `drafts/topolvm-volume-snapshots.md` (this folder)
- Published: `blog/topolvm-volume-snapshots.html`

## Existing tags

Distributed Systems · Databases · Kubernetes · Concurrency · Storage · Performance
