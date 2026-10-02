# Security Policy

## Reporting a vulnerability

Use GitHub's private vulnerability reporting on this repository
(Security → Report a vulnerability). Do not open a public issue.

Expect an acknowledgement within a week. This is a single-maintainer project;
there is no on-call rotation and no service to page.

## What this software touches

Worth knowing before you assess risk, because the trust boundaries are not
where they are in a typical web application:

**Your library lives on the machine running facetmark.** Bookmarks and derived
indexes are stored in SQLite. Importing through the web UI sends the selected
file to that instance; online model calls send the relevant text and queries
to the provider you configure. There is no facetmark-hosted storage service.

`facetmark serve` binds `127.0.0.1` by default. Protected API routes require a
pairing token in `Authorization: Bearer …` or `x-facetmark-token`. Automatic
pairing requires both a loopback peer and a loopback request hostname. Admin
routes also require a loopback peer and can be disabled with
`FACETMARK_ADMIN_API=false`. Use SSH forwarding for remote administration.
If you expose an instance, protect its transport and pairing token; it is a
single-user service, not a multi-user account system.

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

**API keys.** Read from the environment, a `.env` file or `config.toml`.
The settings UI stores changes in `config.toml` and returns masked keys.
Keep configuration backups private. Keys are sent to the base URL you configured, which
may be a local `llama.cpp` server — the whole pipeline was evaluated against one.

**The browser extension** talks only to your local instance. It requests no
host permissions beyond that.

## Out of scope

- Denial of service achieved by feeding it a deliberately enormous local file.
- Anything requiring an attacker who already has read access to your home
  directory, which is where the database and the key live.

## Supported versions

The latest tagged release. This project does not backport.
