# Security Policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository
(Security → Report a vulnerability). Do not open a public issue.

Expect an acknowledgement within a week. This is a single-maintainer project;
there is no on-call rotation and no service to page.

## What this software touches

Worth knowing before you assess risk, because the trust boundaries are not
where they are in a typical web application:

**Your bookmarks are your bookmarks.** Everything is stored in one local SQLite
file. There is no server component you do not run, no telemetry, and no upload
of library contents anywhere. `facetmark serve` binds `127.0.0.1` by default and
has **no authentication** — it is designed for a single local user. If you bind
it to a routable interface, you have published your reading history and your
API key's blast radius to that network. Do not.

**It fetches arbitrary URLs on your behalf.** `facetmark crawl` requests the
pages you bookmarked. This is a deliberate SSRF-shaped capability: the URL list
comes from your own browser export, so the fetcher trusts it. It honours
`robots.txt`, caps response size, and times out, but it will happily resolve an
internal hostname if that is what you bookmarked. Do not point it at a
bookmark file you did not create.

**Page bodies are untrusted input that gets sent to a model.** Extracted text
goes into prompts for summarisation and intent extraction. A crafted page can
attempt prompt injection against those calls. The blast radius is bounded by
what those prompts can do — they produce summaries, topic labels and candidate
queries that land in your local database and can therefore influence your own
search results. They cannot execute code, and no tool calling is exposed to the
model in that path. Treat enriched fields as untrusted display data.

**API keys.** Read from the environment or a `.env` file, never written to the
database, never logged. They are sent only to the base URL you configured, which
may be a local `llama.cpp` server — the whole pipeline was evaluated against one.

**The browser extension** talks only to your local instance. It requests no
host permissions beyond that.

## Out of scope

- Missing authentication on `facetmark serve`. Documented above, by design,
  loopback only.
- Denial of service achieved by feeding it a deliberately enormous local file.
- Anything requiring an attacker who already has read access to your home
  directory, which is where the database and the key live.

## Supported versions

The latest tagged release. This project does not backport.
