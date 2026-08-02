"""A synthetic library with real bodies, and queries whose answers are known.

Why generate a corpus at all. The calibration library is one person's private
bookmarks: it cannot ship, and it has no relevance judgements. Evaluating
retrieval needs (query, correct answer) pairs, and the only honest way to get
them without annotators is to generate documents whose content you control and
derive queries from that content.

What this can and cannot show. A synthetic corpus proves the *pipeline* is
correct -- that four facets produce candidates, that RRF fuses them, that the
episodic layer changes the ranking in the direction it is supposed to. It
cannot prove retrieval *quality* on real pages, because the generator and the
queries share an author. Every number this produces must be read as a plumbing
check. That caveat is printed with the results, not buried here.

Three query types, matching the design document's evaluation plan:

``q_content``
    Words that appear in the body but not in the title. Any competent lexical
    or content-vector system should answer these. They are the control.

``q_vague``
    A description of what the page was *for*, deliberately sharing no rare
    terms with the page. Lexical retrieval cannot answer these. This is the
    facet-2 (intent) test.

``q_episodic``
    Describes a *different* page saved in the same sitting, plus a weak
    descriptor of the target. Lexically, the sibling wins. Only anchoring on
    the sibling and expanding through the session graph puts the real target on
    top. This is the facet-4 test, and it is deliberately the hardest of the
    three.
"""

from __future__ import annotations

import json
import random
import sqlite3
from dataclasses import dataclass, field
from pathlib import Path
from typing import Literal

from ..config import Settings, get_settings
from ..normalize import normalize_url
from ..text import sync_fts

QueryType = Literal["q_content", "q_vague", "q_episodic"]

DAY = 86_400

# ---------------------------------------------------------------------------
# generator vocabulary
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class Domain:
    key: str
    #: Human name used in folders and project labels.
    name: str
    #: Rare terms; at most one page uses each, which is what makes q_content
    #: answerable and unambiguous.
    signatures: tuple[str, ...]
    #: Common terms shared across the domain. Filler, and the reason q_vague is
    #: hard: the vague query is built only from these.
    common: tuple[str, ...]
    #: Task phrasings for the vague query.
    purposes: tuple[str, ...]
    cjk: bool = False


DOMAINS: tuple[Domain, ...] = (
    Domain(
        "vecdb", "Vector stores",
        ("sqlite-vec", "pgvector", "qdrant", "milvus", "lancedb", "chromadb",
         "usearch", "faiss-ivf", "hnswlib", "vespa"),
        ("index", "embedding", "recall", "latency", "shard", "quantization",
         "distance", "brute force", "persistence", "filter"),
        ("keep vectors next to the rest of my data without another server",
         "pick something that survives a restart without a rebuild",
         "avoid running a separate database just for similarity search"),
    ),
    Domain(
        "retrieval", "Retrieval methods",
        ("rrf", "colbert", "splade", "unicoil", "doc2query", "monot5",
         "bm25f", "rank-fusion", "cross-encoder", "hyde"),
        ("ranking", "candidate", "fusion", "sparse", "dense", "rerank",
         "corpus", "judgement", "ablation", "recall"),
        ("combine keyword and semantic search without tuning score scales",
         "make short queries work when the wording never matches the page",
         "measure whether a change to ranking actually helped"),
    ),
    Domain(
        "browserext", "Browser extensions",
        ("manifest-v3", "service-worker", "declarativeNetRequest", "offscreen-document",
         "native-messaging", "content-script", "chrome-storage", "side-panel",
         "host-permissions", "cross-origin-isolation"),
        ("permission", "background", "popup", "tab", "message", "origin",
         "bundle", "reload", "install", "policy"),
        ("read a page the normal way when a fetch keeps getting blocked",
         "talk to something running on my own machine from an extension",
         "keep a background script alive long enough to finish a job"),
    ),
    Domain(
        "sqlite", "SQLite",
        ("fts5", "wal-mode", "trigram-tokenizer", "unicode61", "vacuum-into",
         "generated-column", "upsert-clause", "window-function", "json1", "rtree"),
        ("table", "query", "index", "transaction", "column", "pragma",
         "schema", "migration", "row", "file"),
        ("search text in a local file without standing up a server",
         "make a small database fast enough that nobody notices it",
         "store structured and full text data in one place"),
    ),
    Domain(
        "llmops", "Model plumbing",
        ("vllm", "ollama", "litellm", "tokenizer-merge", "kv-cache", "lora-adapter",
         "speculative-decoding", "json-mode", "batch-api", "context-caching"),
        ("prompt", "token", "latency", "cost", "throughput", "model",
         "endpoint", "retry", "streaming", "quota"),
        ("cut what I spend per page without making the output worse",
         "get structured output back reliably instead of parsing prose",
         "run a model locally when the network is not available"),
    ),
    Domain(
        "frontend", "Interface work",
        ("view-transitions", "container-queries", "css-nesting", "signals-api",
         "shadow-dom", "islands-architecture", "resize-observer", "popover-api",
         "anchor-positioning", "scroll-timeline"),
        ("layout", "component", "state", "render", "style", "event",
         "bundle", "responsive", "animation", "accessibility"),
        ("stop a list from reflowing every time something updates",
         "make a panel position itself next to whatever opened it",
         "share styling without a build step"),
    ),
    Domain(
        "cnml", "\u673a\u5668\u5b66\u4e60\u7b14\u8bb0",
        ("\u5411\u91cf\u68c0\u7d22", "\u7a00\u758f\u6fc0\u6d3b", "\u77e5\u8bc6\u84b8\u998f", "\u63d0\u793a\u8bcd\u5de5\u7a0b", "\u591a\u6a21\u6001\u5bf9\u9f50",
         "\u5f3a\u5316\u5fae\u8c03", "\u91cf\u5316\u90e8\u7f72", "\u957f\u4e0a\u4e0b\u6587", "\u68c0\u7d22\u589e\u5f3a", "\u6a21\u578b\u84b8\u998f"),
        ("\u6a21\u578b", "\u8bad\u7ec3", "\u6570\u636e", "\u6548\u679c", "\u53c2\u6570", "\u63a8\u7406", "\u663e\u5b58", "\u6548\u7387", "\u8bc4\u6d4b", "\u5fae\u8c03"),
        ("\u60f3\u627e\u4e00\u4e2a\u4e0d\u7528\u91cd\u65b0\u8bad\u7ec3\u5c31\u80fd\u63d0\u6548\u679c\u7684\u529e\u6cd5",
         "\u5e0c\u671b\u5728\u81ea\u5df1\u673a\u5668\u4e0a\u8dd1\u5f97\u52a8\u4e0d\u7206\u663e\u5b58",
         "\u60f3\u628a\u5185\u90e8\u8d44\u6599\u63a5\u8fdb\u53bb\u800c\u4e0d\u662f\u91cd\u65b0\u8bad"),
        cjk=True,
    ),
    Domain(
        "cntool", "\u6548\u7387\u5de5\u5177",
        ("\u53cc\u94fe\u7b14\u8bb0", "\u5757\u5f15\u7528", "\u5168\u5c40\u5feb\u6377\u952e", "\u526a\u8d34\u677f\u5386\u53f2", "\u7a97\u53e3\u5e73\u94fa",
         "\u547d\u4ee4\u9762\u677f", "\u81ea\u52a8\u5f52\u6863", "\u6a21\u677f\u5f15\u64ce", "\u672c\u5730\u540c\u6b65", "\u589e\u91cf\u5907\u4efd"),
        ("\u5de5\u5177", "\u7b14\u8bb0", "\u6574\u7406", "\u641c\u7d22", "\u540c\u6b65", "\u63d2\u4ef6", "\u5feb\u6377", "\u7ba1\u7406", "\u8bb0\u5f55", "\u6d41\u7a0b"),
        ("\u60f3\u628a\u6563\u5728\u5404\u5904\u7684\u4e1c\u897f\u96c6\u4e2d\u5230\u4e00\u4e2a\u5730\u65b9",
         "\u4e0d\u60f3\u6bcf\u6b21\u90fd\u624b\u52a8\u5efa\u6587\u4ef6\u5939",
         "\u5e0c\u671b\u79bb\u7ebf\u4e5f\u80fd\u7528\u4e0d\u4f9d\u8d56\u7f51\u76d8"),
        cjk=True,
    ),
)

#: Project labels double as folder names and as the "what I was doing" phrase
#: an episodic query is built around.
PROJECTS_EN = (
    "the search prototype", "the browser add-on", "the cost review",
    "the migration to SQLite", "the ranking experiment", "the offline demo",
)
PROJECTS_CN = ("\u641c\u7d22\u539f\u578b", "\u6d4f\u89c8\u5668\u63d2\u4ef6", "\u6210\u672c\u6838\u7b97", "\u672c\u5730\u5316\u6539\u9020", "\u6392\u5e8f\u5b9e\u9a8c", "\u79bb\u7ebf\u6f14\u793a")

_EN_SENTENCES = (
    "The {sig} approach keeps the {c0} close to the {c1}, which removes an entire moving part.",
    "In practice the {c2} dominates: once the {c3} is warm, {sig} spends most of its time on {c4}.",
    "There is a tradeoff between {c0} and {c5} that {sig} resolves by giving up exactness.",
    "Anyone evaluating {sig} should measure {c2} on their own {c6} rather than trusting a blog post.",
    "The failure mode nobody mentions is what {sig} does when the {c7} grows faster than the {c1}.",
    "Setting up {sig} took an afternoon; understanding why the {c3} behaved that way took a week.",
    "Compared with the usual {c8}, {sig} trades setup effort for predictable {c9}.",
    "The documentation for {sig} covers the happy path and stops exactly where the {c5} starts.",
)

_CN_SENTENCES = (
    "{sig}\u7684\u505a\u6cd5\u662f\u628a{c0}\u548c{c1}\u653e\u5728\u4e00\u8d77\uff0c\u5c11\u4e86\u4e00\u5c42\u4f9d\u8d56\u3002",
    "\u5b9e\u9645\u8dd1\u4e0b\u6765\uff0c{c2}\u624d\u662f\u74f6\u9888\uff1b{sig}\u5927\u90e8\u5206\u65f6\u95f4\u82b1\u5728{c3}\u4e0a\u3002",
    "{c0}\u548c{c4}\u4e4b\u95f4\u6709\u53d6\u820d\uff0c{sig}\u9009\u62e9\u4e86\u727a\u7272\u4e00\u70b9\u7cbe\u786e\u5ea6\u3002",
    "\u60f3\u7528{sig}\u7684\u4eba\u6700\u597d\u81ea\u5df1\u8dd1\u4e00\u904d{c2}\uff0c\u522b\u76f4\u63a5\u4fe1\u522b\u4eba\u7684\u6570\u5b57\u3002",
    "\u5f88\u5c11\u6709\u4eba\u63d0\u7684\u5751\u662f\uff1a{c5}\u589e\u957f\u5f97\u6bd4{c1}\u5feb\u7684\u65f6\u5019\uff0c{sig}\u4f1a\u76f4\u63a5\u5361\u4f4f\u3002",
    "\u914d{sig}\u82b1\u4e86\u4e00\u4e0b\u5348\uff0c\u641e\u660e\u767d{c3}\u4e3a\u4ec0\u4e48\u90a3\u6837\u8868\u73b0\u82b1\u4e86\u4e00\u5468\u3002",
    "\u548c\u5e38\u89c1\u7684{c6}\u76f8\u6bd4\uff0c{sig}\u7528\u914d\u7f6e\u6210\u672c\u6362\u4e86\u53ef\u9884\u6d4b\u7684{c7}\u3002",
    "{sig}\u7684\u6587\u6863\u53ea\u5199\u4e86\u987a\u5229\u7684\u60c5\u51b5\uff0c\u5230{c4}\u5f00\u59cb\u7684\u5730\u65b9\u5c31\u6ca1\u4e86\u3002",
)

_EN_TITLE = (
    "{sig}: notes on {c0}",
    "Why {sig} changes the {c1} story",
    "{sig} in production, three months in",
    "Evaluating {sig} for {c2}",
)
_CN_TITLE = (
    "{sig}\u7b14\u8bb0\uff1a\u5173\u4e8e{c0}",
    "{sig}\u600e\u4e48\u6539\u53d8\u4e86{c1}",
    "{sig}\u5b9e\u8df5\u4e09\u4e2a\u6708",
    "{sig}\u5728{c2}\u4e0a\u7684\u8bc4\u6d4b",
)

_EN_VAGUE = (
    "that thing I found when I wanted to {purpose}",
    "the page about how to {purpose}",
    "I saved something about trying to {purpose}",
)
_CN_VAGUE = (
    "\u4e4b\u524d\u4e3a\u4e86{purpose}\u5b58\u7684\u90a3\u4e2a",
    "\u5173\u4e8e{purpose}\u7684\u90a3\u4e2a\u9875\u9762",
    "\u60f3\u627e\u4e00\u4e2a\u80fd{purpose}\u7684\u4e1c\u897f",
)

_EN_EPISODIC = "the other thing I saved around the same time as {sibling}, the one about {weak}"
_CN_EPISODIC = "\u548c{sibling}\u524d\u540e\u811a\u5b58\u7684\u53e6\u4e00\u4e2a\uff0c\u5173\u4e8e{weak}\u90a3\u4e2a"


# ---------------------------------------------------------------------------
# generated objects
# ---------------------------------------------------------------------------


@dataclass(slots=True)
class Page:
    idx: int
    url: str
    title: str
    body: str
    folder: str
    domain_key: str
    signature: str
    purpose: str
    project: str
    date_added: int
    session_idx: int
    bookmark_id: int = 0


@dataclass(slots=True)
class EvalQuery:
    text: str
    qtype: QueryType
    target: int          #: page index; resolved to bookmark_id after insertion
    target_id: int = 0
    note: str = ""


@dataclass(slots=True)
class Corpus:
    pages: list[Page] = field(default_factory=list)
    queries: list[EvalQuery] = field(default_factory=list)
    seed: int = 0
    #: Set when the queries were bound to a library this process did not
    #: generate, where ``pages`` is empty but the library is not.
    library_pages: int = 0

    def by_type(self, qtype: QueryType) -> list[EvalQuery]:
        return [q for q in self.queries if q.qtype == qtype]

    @property
    def counts(self) -> dict[str, int]:
        out = {"pages": len(self.pages) or self.library_pages}
        for t in ("q_content", "q_vague", "q_episodic"):
            out[t] = len(self.by_type(t))  # type: ignore[arg-type]
        return out


# ---------------------------------------------------------------------------
# generation
# ---------------------------------------------------------------------------


def _fmt(template: str, sig: str, common: tuple[str, ...], rng: random.Random) -> str:
    pool = list(common)
    rng.shuffle(pool)
    slots = {f"c{i}": pool[i % len(pool)] for i in range(10)}
    return template.format(sig=sig, **slots)


def generate_corpus(
    size: int = 120,
    *,
    seed: int = 7,
    now_ts: int = 1_760_000_000,
    sessions: int | None = None,
) -> Corpus:
    """Build ``size`` pages grouped into saving sessions, plus their queries.

    Sessions are the point: pages are emitted in bursts a few minutes apart and
    then separated by days, which is the temporal shape the adaptive session
    clusterer is looking for. A uniformly spaced corpus would make facet 4
    untestable by construction.
    """
    rng = random.Random(seed)
    n_sessions = sessions or max(4, size // 6)
    pages: list[Page] = []

    # Enough signatures for `size` unique pages: reuse across domains only when
    # the corpus is larger than the vocabulary, and then with a suffix so the
    # rare term stays unique.
    cursor = now_ts - 400 * DAY
    page_idx = 0
    for s in range(n_sessions):
        dom = DOMAINS[s % len(DOMAINS)]
        project = (PROJECTS_CN if dom.cjk else PROJECTS_EN)[s % 6]
        folder = f"{dom.name}/{project}" if not dom.cjk else f"{dom.name}/{project}"
        burst = size // n_sessions + (1 if s < size % n_sessions else 0)
        cursor += rng.randint(3, 21) * DAY + rng.randint(0, 6 * 3600)
        for _ in range(burst):
            if page_idx >= size:
                break
            base = dom.signatures[page_idx % len(dom.signatures)]
            round_no = page_idx // len(dom.signatures)
            sig = base if round_no == 0 else f"{base}-{round_no + 1}"
            purpose = dom.purposes[page_idx % len(dom.purposes)]
            titles = _CN_TITLE if dom.cjk else _EN_TITLE
            sents = _CN_SENTENCES if dom.cjk else _EN_SENTENCES
            title = _fmt(titles[page_idx % len(titles)], sig, dom.common, rng)
            picked = rng.sample(sents, k=min(6, len(sents)))
            body = ("\n\n" if not dom.cjk else "\n").join(
                _fmt(t, sig, dom.common, rng) for t in picked
            )
            # Pad so the body clears min_body_chars on the CJK side too.
            body += ("\n" + _fmt(sents[0], sig, dom.common, rng)) * 2
            cursor += rng.randint(40, 900)
            pages.append(Page(
                idx=page_idx,
                url=f"https://{dom.key}{page_idx}.example/{base.replace('/', '-')}",
                title=title, body=body, folder=folder, domain_key=dom.key,
                signature=sig, purpose=purpose, project=project,
                date_added=cursor, session_idx=s,
            ))
            page_idx += 1

    return Corpus(pages=pages, queries=_build_queries(pages, rng), seed=seed)


def _title_terms(title: str) -> set[str]:
    return {w.strip(":,.\u3002\uff1a").lower() for w in title.replace("\uff1a", " ").split()}


def _build_queries(pages: list[Page], rng: random.Random) -> list[EvalQuery]:
    by_session: dict[int, list[Page]] = {}
    for p in pages:
        by_session.setdefault(p.session_idx, []).append(p)

    out: list[EvalQuery] = []
    for p in pages:
        dom = next(d for d in DOMAINS if d.key == p.domain_key)

        # --- q_content: body words the title does not contain -------------
        title_words = _title_terms(p.title)
        body_terms = [c for c in dom.common if c.lower() not in title_words]
        rng.shuffle(body_terms)
        picked = body_terms[:3]
        text = (f"{p.signature} " + ("".join(picked) if dom.cjk else " ".join(picked))).strip()
        out.append(EvalQuery(text=text, qtype="q_content", target=p.idx,
                             note="signature plus body-only terms"))

        # --- q_vague: purpose only, no signature, no title words ----------
        tpl = (_CN_VAGUE if dom.cjk else _EN_VAGUE)[p.idx % 3]
        out.append(EvalQuery(text=tpl.format(purpose=p.purpose), qtype="q_vague",
                             target=p.idx, note="purpose paraphrase, no shared rare term"))

        # --- q_episodic: describes a sibling, targets this page -----------
        siblings = [q for q in by_session[p.session_idx] if q.idx != p.idx]
        if not siblings:
            continue
        sib = rng.choice(siblings)
        weak = dom.common[p.idx % len(dom.common)]
        tpl_e = _CN_EPISODIC if dom.cjk else _EN_EPISODIC
        out.append(EvalQuery(
            text=tpl_e.format(sibling=sib.signature, weak=weak),
            qtype="q_episodic", target=p.idx,
            note=f"anchor sibling={sib.idx}, session={p.session_idx}",
        ))
    return out


# ---------------------------------------------------------------------------
# loading
# ---------------------------------------------------------------------------


def load_corpus(
    conn: sqlite3.Connection, corpus: Corpus, *, settings: Settings | None = None
) -> Corpus:
    """Insert the corpus with bodies already present, skipping the fetcher.

    The bodies are written straight into ``content`` because there is nothing to
    fetch: pretending otherwise would mean standing up a local HTTP server to
    serve text this process just generated.
    """
    settings or get_settings()
    now_row = conn.execute("SELECT COUNT(*) FROM bookmark").fetchone()[0]
    if now_row:
        raise ValueError("load_corpus expects an empty database")

    for p in corpus.pages:
        nu = normalize_url(p.url)
        cur = conn.execute(
            "INSERT INTO bookmark(url, url_norm, url_hash, title, folder, folder_depth, "
            "  host, domain, date_added, source, indexable, privacy_skipped, "
            "  created_at, updated_at) "
            "VALUES(?,?,?,?,?,2,?,?,?,'synthetic',1,0,?,?)",
            (p.url, nu.normalized, nu.hash, p.title, p.folder, nu.host, nu.host,
             p.date_added, p.date_added, p.date_added),
        )
        p.bookmark_id = int(cur.lastrowid)
        conn.execute(
            "INSERT INTO content(bookmark_id, body_text, body_hash, char_count, lang, "
            "  extractor, fetch_channel, http_status, final_url, fetched_at) "
            "VALUES(?,?,?,?,?,'synthetic','a',200,?,?)",
            (p.bookmark_id, p.body, f"synth-{p.idx}", len(p.body),
             "zh" if any("\u4e00" <= ch <= "\u9fff" for ch in p.body) else "en",
             p.url, p.date_added),
        )
        sync_fts(conn, p.bookmark_id, title=p.title, body=p.body)

    ids = {p.idx: p.bookmark_id for p in corpus.pages}
    for q in corpus.queries:
        q.target_id = ids[q.target]
    conn.commit()
    return corpus


# ---------------------------------------------------------------------------
# queries for a library that already exists
# ---------------------------------------------------------------------------


class QueryFileError(ValueError):
    """The query file is unusable, with a reason the caller can print."""


def load_query_file(conn: sqlite3.Connection, path: str | Path) -> Corpus:
    """Read ``{"text", "qtype", "target_url"}`` records and bind them to a library.

    The synthetic generator knows its own answers; a real library does not, so
    the answers arrive as a file and the target is named by **URL**, not by row
    id. Ids depend on import order and would silently point at the wrong page
    after a re-import -- which is the kind of bug that makes an evaluation look
    like it succeeded.

    A query whose target is not in this library is a hard error, not a skip.
    Silently dropping unmatched queries would quietly change the denominator of
    every recall number in the report.
    """
    path = Path(path)
    rows: list[dict] = []
    for lineno, line in enumerate(path.read_text(encoding="utf-8").splitlines(), 1):
        line = line.strip()
        if not line or line.startswith("//"):
            continue
        try:
            rows.append(json.loads(line))
        except json.JSONDecodeError as exc:
            raise QueryFileError(f"{path}:{lineno}: {exc}") from exc
    if not rows:
        raise QueryFileError(f"{path}: no queries")

    by_norm: dict[str, int] = {
        r["url_norm"]: int(r["id"])
        for r in conn.execute("SELECT id, url_norm FROM bookmark")
    }

    queries: list[EvalQuery] = []
    missing: list[str] = []
    for i, r in enumerate(rows):
        qtype = r.get("qtype")
        if qtype not in ("q_content", "q_vague", "q_episodic"):
            raise QueryFileError(f"{path}: record {i} has qtype={qtype!r}")
        text = (r.get("text") or "").strip()
        if not text:
            raise QueryFileError(f"{path}: record {i} has no text")
        url = r.get("target_url") or ""
        bid = by_norm.get(normalize_url(url).normalized)
        if bid is None:
            missing.append(url)
            continue
        queries.append(EvalQuery(text=text, qtype=qtype, target=i, target_id=bid,
                                 note=r.get("note") or ""))
    if missing:
        raise QueryFileError(
            f"{path}: {len(missing)} target url(s) are not in this library, "
            f"first: {missing[0]}"
        )

    npages = int(conn.execute("SELECT COUNT(*) FROM bookmark WHERE indexable=1").fetchone()[0])
    return Corpus(pages=[], queries=queries, seed=0, library_pages=npages)


__all__ = [
    "DAY",
    "DOMAINS",
    "Corpus",
    "Domain",
    "EvalQuery",
    "Page",
    "QueryFileError",
    "QueryType",
    "generate_corpus",
    "load_corpus",
    "load_query_file",
]
