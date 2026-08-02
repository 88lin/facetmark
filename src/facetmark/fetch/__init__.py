"""Two-channel page acquisition.

Channel A (``client``) is a polite async HTTP crawler. Channel B is the browser
extension: when A hits a login wall, a bot check or a client-rendered shell, the
bookmark is queued (``store``) and the extension re-reads it from a real tab
using the user's own session. The queue is the seam between the two.
"""

from .client import (
    DEFAULT_UA,
    DEFER_TO_BROWSER,
    MAX_BYTES,
    SPA_HOSTS,
    BatchResult,
    FetchPolicy,
    FetchResult,
    Verdict,
    fetch_many,
    fetch_one,
)
from .extract import (
    MIN_USEFUL_CHARS,
    WALL_MARKERS,
    Extraction,
    extract,
    html_title,
    looks_like_wall,
    meta_description,
)
from .store import (
    LEASE_TTL_S,
    MAX_BROWSER_ATTEMPTS,
    CrawlReport,
    SaveOutcome,
    complete_browser_item,
    crawl,
    enqueue_for_browser,
    lease_browser_batch,
    pending_targets,
    policy_from_settings,
    queue_stats,
    record_failure,
    save_result,
    store_body,
)

__all__ = [
    "DEFAULT_UA", "DEFER_TO_BROWSER", "MAX_BYTES", "SPA_HOSTS", "BatchResult",
    "FetchPolicy", "FetchResult", "Verdict", "fetch_many", "fetch_one",
    "MIN_USEFUL_CHARS", "WALL_MARKERS", "Extraction", "extract", "html_title",
    "looks_like_wall", "meta_description",
    "LEASE_TTL_S", "MAX_BROWSER_ATTEMPTS", "CrawlReport", "SaveOutcome",
    "complete_browser_item", "crawl", "enqueue_for_browser", "lease_browser_batch",
    "pending_targets", "policy_from_settings", "queue_stats", "record_failure",
    "save_result", "store_body",
]
