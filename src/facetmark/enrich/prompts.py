"""The enrichment prompt.

One call per page produces every enrichment field, including the intent
queries. Splitting it into two calls doubles the cost and the latency and buys
nothing: the queries are better when the model writes them while it still has
the summary in front of it.

Two constraints in here are load-bearing and should not be softened:

**Intent queries must be written in the words of someone who does not know the
page's vocabulary.** A query generated from the page's own terminology retrieves
that page trivially and adds nothing the lexical index did not already have.
The whole point of facet 2 is to bridge the gap between how the user will ask
six months from now and how the page words itself.

**Entities must be copied, not normalised.** The user remembers "the k8s thing",
not "Kubernetes (container orchestration platform)". Expanding an abbreviation
or translating a name destroys the exact string the user is most likely to type.
"""

from __future__ import annotations

PAGE_MARKER = "<<<PAGE>>>"

SYSTEM = """You index saved web pages for a personal retrieval system.
You return one JSON object and nothing else. No prose, no code fence."""

_TEMPLATE = """Read the page below and return a JSON object with exactly these keys:

  "summary"        string, at most 200 characters, in the page's own language.
                   What the page IS and what it is FOR. Not a topic list.
  "key_points"     array of 2-5 short strings. Concrete claims or steps, not
                   section headings.
  "entities"       array of 0-10 strings. Product names, library names, people,
                   organisations, standards, file formats, model names.
                   COPY THEM EXACTLY AS WRITTEN on the page: keep the original
                   capitalisation and spelling, do not translate them, do not
                   expand abbreviations, do not add explanations.
  "topics"         array of 2-6 short subject labels.
  "utility"        one of: reference | tutorial | tool | news | opinion |
                   documentation | paper | dataset | product | entertainment |
                   other. What the reader would USE this for.
  "content_type"   one of: article | docs | repo | video | thread | pdf |
                   slides | landing | forum | other.
  "intent_queries" array of exactly {n} strings.

Rules for "intent_queries" -- these matter most:
  * Write what a person would type into a search box MONTHS after saving this
    page, when they remember the problem but NOT the page's vocabulary.
  * Use ordinary words. Avoid the page's own jargon, product names and
    section titles unless a person would genuinely search for that name.
  * Cover different angles: the problem it solves, the situation that leads
    someone here, the comparison it settles, the mistake it prevents.
  * If the page is in Chinese, write most queries in Chinese; if English, in
    English; write one or two in the other language when a bilingual reader
    would plausibly switch.
  * Phrase them as questions or as things to look up, not as titles.

Metadata about the saved page:
  title:  {title}
  url:    {url}
  folder: {folder}

{marker}
{body}"""


def build_user_prompt(
    *,
    title: str,
    url: str,
    folder: str,
    body: str,
    n_queries: int,
) -> str:
    return _TEMPLATE.format(
        n=n_queries,
        title=title or "(none)",
        url=url,
        folder=folder or "(none)",
        marker=PAGE_MARKER,
        body=body or "(the page body could not be fetched; work from the title and url)",
    )
