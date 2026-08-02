"""URL normalisation.

Produces a stable key for de-duplication and identity while keeping the original
URL untouched for navigation.

The governing principle, from the design doc: **prefer under-merging to
mis-merging**. A missed duplicate costs one redundant row; a wrong merge
destroys a bookmark the user can never find again. Therefore only parameters on
an explicit tracking denylist are stripped, and every unknown parameter is
preserved.

Measured on a real 1697-bookmark library: exact-URL duplicates 1, duplicates
after normalisation 5. The value of this module is correctness of identity, not
volume of merging.
"""

from __future__ import annotations

import hashlib
import re
from collections.abc import Sequence
from dataclasses import dataclass
from urllib.parse import parse_qsl, quote, unquote, urlencode, urlsplit, urlunsplit

# ---------------------------------------------------------------------------
# Tracking parameters. Exact names plus prefix families.
# ---------------------------------------------------------------------------
TRACKING_PARAMS_EXACT: frozenset[str] = frozenset(
    {
        "fbclid",
        "gclid",
        "dclid",
        "msclkid",
        "yclid",
        "twclid",
        "igshid",
        "si",
        "spm",
        "scm",
        "ref",
        "ref_src",
        "ref_url",
        "referrer",
        "from",
        "from_source",
        "share_source",
        "share_medium",
        "share_plat",
        "share_token",
        "mkt_tok",
        "_hsenc",
        "_hsmi",
        "hsCtaTracking",
        "vero_id",
        "vero_conv",
        "mc_cid",
        "mc_eid",
        "oly_anon_id",
        "oly_enc_id",
        "wt_mc",
        "trk",
        "trkCampaign",
        "sourceid",
        "spref",
        "xtor",
        "at_medium",
        "at_campaign",
    }
)

TRACKING_PARAM_PREFIXES: tuple[str, ...] = ("utm_", "pk_", "piwik_", "matomo_", "ga_", "_ga")

DEFAULT_PORTS: dict[str, int] = {"http": 80, "https": 443, "ftp": 21, "ws": 80, "wss": 443}

# ---------------------------------------------------------------------------
# Hosts where the fragment identifies distinct content and must be preserved.
# Bookmarks that share a normalised URL but differ only by fragment are linked
# with an ``anchor_sibling`` edge rather than merged.
# ---------------------------------------------------------------------------
ANCHOR_MEANINGFUL_HOSTS: frozenset[str] = frozenset(
    {
        "github.com",
        "gist.github.com",
        "gitlab.com",
        "stackoverflow.com",
        "serverfault.com",
        "superuser.com",
        "askubuntu.com",
        "developer.mozilla.org",
        "docs.python.org",
        "docs.rs",
        "en.wikipedia.org",
        "zh.wikipedia.org",
        "news.ycombinator.com",
        "groups.google.com",
        "mail.google.com",
        "docs.google.com",
        "web.archive.org",
    }
)

#: Schemes we index. Anything else (data:, javascript:, chrome:, file:) is kept
#: as a row but never fetched, enriched or probed.
INDEXABLE_SCHEMES: frozenset[str] = frozenset({"http", "https"})

_MULTI_SLASH = re.compile(r"/{2,}")


@dataclass(frozen=True, slots=True)
class NormalizedURL:
    original: str
    normalized: str
    #: sha256 of ``normalized`` -- the identity key.
    hash: str
    host: str
    scheme: str
    #: Fragment that was preserved because the host is anchor-meaningful.
    kept_fragment: str = ""
    #: Fragment that was dropped. Used to detect anchor siblings.
    dropped_fragment: str = ""
    indexable: bool = True


def _is_tracking(name: str) -> bool:
    low = name.lower()
    if low in TRACKING_PARAMS_EXACT:
        return True
    return any(low.startswith(p) for p in TRACKING_PARAM_PREFIXES)


def _fragment_is_route(fragment: str) -> bool:
    """Hash-based client-side routing: ``#!/path`` or ``#/path``.

    These are the whole address on old SPA frameworks, so dropping them would
    collapse an entire site into one row.
    """
    return fragment.startswith(("!", "/"))


def _clean_path(path: str) -> str:
    if not path:
        return "/"
    # Re-encode percent escapes to a canonical uppercase-hex form while leaving
    # already-safe characters (including non-ASCII) alone.
    path = quote(unquote(path), safe="/-._~!$&'()*+,;=:@%")
    path = _MULTI_SLASH.sub("/", path)
    if len(path) > 1 and path.endswith("/"):
        path = path.rstrip("/") or "/"
    return path


def normalize_url(url: str, *, force_https: bool = True) -> NormalizedURL:
    """Apply the eight normalisation steps.

    1. unify scheme to https (comparison only; ``original`` is untouched)
    2. lowercase host, strip a leading ``www.``
    3. drop the port when it is the scheme default
    4. strip tracking parameters (denylist + prefix families)
    5. keep every unknown parameter
    6. sort the remaining query pairs
    7. drop the trailing slash
    8. drop the fragment, except hash routes and anchor-meaningful hosts
    """
    raw = (url or "").strip()
    parts = urlsplit(raw)
    scheme = (parts.scheme or "http").lower()

    if scheme not in INDEXABLE_SCHEMES:
        # Opaque scheme: normalise to a trimmed form and mark non-indexable.
        norm = raw
        return NormalizedURL(
            original=raw,
            normalized=norm,
            hash=hashlib.sha256(norm.encode("utf-8")).hexdigest(),
            host="",
            scheme=scheme,
            indexable=False,
        )

    host = (parts.hostname or "").lower()
    if host.startswith("www.") and host.count(".") >= 2:
        host = host[4:]

    netloc = host
    if parts.port and parts.port != DEFAULT_PORTS.get(scheme):
        netloc = f"{host}:{parts.port}"

    pairs = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if not _is_tracking(k)]
    query = urlencode(sorted(pairs), doseq=True)

    frag = parts.fragment
    keep_frag = ""
    drop_frag = ""
    if frag:
        if _fragment_is_route(frag) or host in ANCHOR_MEANINGFUL_HOSTS:
            keep_frag = frag
        else:
            drop_frag = frag

    out_scheme = "https" if force_https else scheme
    normalized = urlunsplit((out_scheme, netloc, _clean_path(parts.path), query, keep_frag))

    return NormalizedURL(
        original=raw,
        normalized=normalized,
        hash=hashlib.sha256(normalized.encode("utf-8")).hexdigest(),
        host=host,
        scheme=scheme,
        kept_fragment=keep_frag,
        dropped_fragment=drop_frag,
        indexable=True,
    )


def registrable_domain(host: str) -> str:
    """Cheap eTLD+1 approximation.

    A full public-suffix list is deliberately avoided: this value is only used
    for the low-weight ``same_domain`` edge and for per-host fetch throttling,
    where an occasional wrong grouping is harmless. Measured on the real library,
    95% of domains appear exactly once, so this edge carries little weight
    regardless.
    """
    host = host.lower().strip(".")
    if not host or host.replace(".", "").isdigit():
        return host
    labels = host.split(".")
    if len(labels) <= 2:
        return host
    two_level = {
        "co", "com", "net", "org", "gov", "edu", "ac", "or", "ne", "go",
        "in", "id", "web", "sch", "res", "mil", "info", "biz", "gen", "ltd",
        "plc", "me", "nom", "firm", "store", "art", "adm",
    }
    if labels[-2] in two_level and len(labels) >= 3:
        return ".".join(labels[-3:])
    return ".".join(labels[-2:])


def body_normalize_for_hash(text: str) -> str:
    """Canonicalise body text before hashing.

    Removes the churn that would otherwise make every re-fetch look like a
    content change and trigger a needless (paid) re-enrichment: collapsed
    whitespace, timestamp-shaped strings, and short navigational leftovers.
    """
    if not text:
        return ""
    t = re.sub(r"\d{4}[-/]\d{1,2}[-/]\d{1,2}([ T]\d{1,2}:\d{2}(:\d{2})?)?", " ", text)
    t = re.sub(r"\b\d{1,2}:\d{2}(:\d{2})?\b", " ", t)
    t = re.sub(r"\b\d+\s*(minutes?|hours?|days?|weeks?|months?|years?)\s+ago\b", " ", t, flags=re.I)
    t = re.sub(r"\b\d+\s*(分钟|小时|天|周|个月|年)前\b", " ", t)
    lines = [ln.strip() for ln in t.splitlines()]
    lines = [ln for ln in lines if len(ln) > 2]
    t = "\n".join(lines)
    return re.sub(r"\s+", " ", t).strip()


def body_hash(text: str) -> str:
    return hashlib.sha256(body_normalize_for_hash(text).encode("utf-8")).hexdigest()


def host_excluded(host: str, excluded: Sequence[str]) -> bool:
    """Suffix match against the privacy exclusion list.

    One definition, used by the importer (which refuses to enrich these) and by
    the health layer (which refuses to send them to any third party). Two
    copies of this rule would eventually disagree, and the disagreement would
    be a privacy leak rather than a bug report.
    """
    if not host or not excluded:
        return False
    h = host.lower()
    return any(h == d.lower().lstrip(".") or h.endswith("." + d.lower().lstrip("."))
               for d in excluded)
