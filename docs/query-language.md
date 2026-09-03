# The Query Language

facetmark's search box accepts plain text — that is still what it is built
around, and a query with no syntax behaves exactly as it did before the
language existed. The language below is **ported from
[hister](https://github.com/asciimoo/hister)** (the private search engine by
searx's author), adapted to a bookmark library's fields. It exists for the
question "I know *where* or *when* I saved it, and roughly *what* it said" —
the cases the four facets are worst at.

A query with syntax is answered by the same pipeline as one without: the
filters cut the candidate pool **after** ranking and never move a surviving
document's score, and `sort:` re-orders only when asked. No default ranking
changed to make this work; that constraint is why this is a filter language
rather than a ranker.

## Field filters

| Field | Matches | Examples |
|---|---|---|
| `domain:` (alias `site:`) | the site, exact or wildcard | `domain:github.com`, `site:*.github.io` |
| `url:` | part of the address | `url:*/docs/*` |
| `title:` | words in the title only | `title:encryption` |
| `text:` | words in the page body only | `text:"GDPR compliance"` |
| `folder:` | the browser folder it was saved in | `folder:study` |
| `topic:` | an enrichment topic | `topic:postgres` |
| `lang:` | the detected language | `lang:zh` |
| `added:` (aliases `saved:`, `before:`, `after:`) | when it was saved | `added:>90d`, `added:>=2026-04-01` |
| `opened:` | how many times you opened it | `opened:10..`, `opened:2..4` |

```textplain
postgres domain:github.com
title:encryption domain:(signal.org|whatsapp.com) -deprecated
kafka added:<7d
```

## When it was saved

Relative durations compare against the bookmark's **age**; absolute dates
compare against the timestamp. Both forms, exactly as hister defines them:

```textplain
added:<7d          saved within the last 7 days
added:>90d         saved more than 90 days ago
added:>=2026-04-01 saved on or after 2026-04-01 (UTC midnight)
added:<2026-05-01  saved before 2026-05-01
added:2026-04-01   that whole day
added:2026-04      that whole month
added:2026         that whole year
added:2026-01-01..2026-03-31   a range
before:2026-05-01  sugar for added:<2026-05-01
after:2024-01-01   sugar for added:>=2024-01-01
```

Units: `s`, `m`, `h`, `d`, `w`, `y` (365 days — the column has no calendar).

## Negation

A `-` before a term or a field excludes it:

```textplain
privacy -facebook
privacy -domain:facebook.com
-"social media"
```

A hyphen *inside* a word is not a negation (`state-of-the-art` is one term).

## Phrases and alternation

```textplain
"consumer group rebalancing"     exact phrase, in the lexical facets
(security|privacy|encryption)    OR — expands to alternatives
domain:(github.com|gitlab.com)   alternation inside a field
```

## Sorting

```textplain
kafka sort:date       newest first
kafka sort:-date      oldest first
sort:domain           grouped by site (also: title, url, relevance)
```

A query of only a sort directive plus filters (e.g. `domain:github.com
sort:date`) is a **browse**: the filters are the retrieval, no model call is
made, the ranking layers (context multiplier, decay, reranker) are skipped,
and the order is the sort's. Paging through a browse works like any other
query.

`sort:relevance` names the ranking rather than a column, so it is a no-op on a
ranked query and, on a browse, the same newest-first order an unsorted browse
gets — there is nothing scored to rank when the filters *are* the retrieval.

## Wildcards

`*` stands for any run of characters in `domain`, `url`, `title`, `folder`,
`text` values:

```textplain
domain:*.github.io
url:*/docs/*
title:compar*
```

## Compatibility rules

These are the rules that keep a decade of plain queries working, and they are
pinned by tests:

- A `:` only means a filter when the name is one of the fields above.
  `note: something` and `https://example.com` are ordinary text.
- A `-` only means negation at the start of a token followed by more
  characters.
- Quotes inside a word keep the word together (`text:"GDPR compliance"` is
  one token).
- A filter value that does not parse (`added:90d`) is reported in the
  response's `filters.ignored` rather than silently applied or dropped.
- A query with no syntax produces a response with `filters: null` — the
  pre-language behaviour, byte for byte.

## Where the syntax is accepted

Every search surface: the web UI's box, `facetmark search`, the REST API's
`/search` and `/quick`, the MCP server's tools, and the karakeep plugin's
query field. The response echoes what was applied under `filters`, and
`facetmark search --explain` prints it.

The web UI completes the syntax as you type: type `dom` or `domain:git` and
the suggestion list offers the fields and the *values that exist in your
library*. The time chips under the search box and the activity timeline on
the Library view are the same language wearing a UI — every chip writes an
`added:` token you could have typed.
