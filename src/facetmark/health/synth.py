"""Combine the layers into one conclusion.

The rules are short and the ordering is the whole design:

1. **Any positive observation from another egress wins.** If a reader proxy or
   the user's proxy rendered the page, or two public resolvers disagree about
   whether the host exists, the answer is ``restricted`` -- no matter how
   thoroughly the local probe failed. This clause is checked first precisely so
   that no amount of local failure can outvote one positive elsewhere.
2. **``gone`` requires the server to say so.** Only a local 404/410 can reach
   ``gone``, and only when nothing contradicted it. A DNS failure never gets
   there, even when both public resolvers return NXDOMAIN and the domain is
   plainly dead. That is stricter than the evidence warrants and it is the
   intended trade: the cost of waiting is one line of noise in a result list,
   the cost of being wrong is a bookmark the user never learns they lost.
3. **Absence of evidence changes nothing.** A missing snapshot, a resolver that
   timed out, a reader proxy that 502'd -- none of these move the needle in
   either direction. Only positive observations do.
4. **Local-only checks are capped below the confirmation bar.** With layer 2
   switched off (by config, or because the host is on the privacy exclusion
   list) a check can still run and still be recorded, but it can never become
   one of the two confirmations that ``gone`` requires.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field

from .external import ExternalReport
from .local import LocalProbe
from .verdicts import (
    BASE_CONFIDENCE,
    BONUS_PROXY_OK,
    BONUS_READER_OK,
    BONUS_RESOLVER_DIVERGENCE,
    BONUS_RESOLVERS_AGREE_NXDOMAIN,
    BONUS_SNAPSHOT_AFTER_FAILURE,
    LOCAL_ONLY_CAP,
    Evidence,
    LocalVerdict,
    Status,
    clamp,
)


@dataclass(slots=True)
class HealthCheck:
    url: str
    status: Status
    confidence: float
    checked_at: int
    http_status: int | None = None
    local: LocalProbe | None = None
    external: ExternalReport | None = None
    evidence: list[Evidence] = field(default_factory=list)
    archive_url: str = ""
    recovered_body: str = ""
    recovered_title: str = ""

    @property
    def is_dead_signal(self) -> bool:
        """Whether this verdict is one the metabolism layer treats as evidence
        of supersession (see ``search.decay.DEAD_VERDICTS``)."""
        return self.status in (Status.GONE, Status.DRIFTED, Status.SOFT_GONE)

    def as_dict(self) -> dict:
        return {
            "url": self.url,
            "status": self.status.value,
            "confidence": self.confidence,
            "checked_at": self.checked_at,
            "http_status": self.http_status,
            "archive_url": self.archive_url,
            "evidence": [e.as_dict() for e in self.evidence],
        }


_DIRECT: dict[LocalVerdict, Status] = {
    LocalVerdict.ALIVE: Status.ALIVE,
    LocalVerdict.DRIFTED: Status.DRIFTED,
    LocalVerdict.SOFT_GONE: Status.SOFT_GONE,
    LocalVerdict.SKIPPED: Status.UNKNOWN,
}


def synthesize(
    probe: LocalProbe,
    external: ExternalReport | None = None,
    *,
    now_ts: int | None = None,
) -> HealthCheck:
    now = int(time.time()) if now_ts is None else int(now_ts)
    ev: list[Evidence] = list(probe.evidence)
    ext_ran = bool(external and external.checked)
    if external is not None:
        ev.extend(external.evidence)

    archive = external.snapshot_url if external else ""

    def finish(status: Status, bonus: float = 0.0) -> HealthCheck:
        conf = BASE_CONFIDENCE[status] + bonus
        if not ext_ran:
            conf = min(conf, LOCAL_ONLY_CAP)
        return HealthCheck(
            url=probe.url, status=status, confidence=clamp(conf), checked_at=now,
            http_status=probe.http_status, local=probe, external=external,
            evidence=ev, archive_url=archive,
            recovered_body=(external.recovered_body if external else ""),
            recovered_title=(external.recovered_title if external else ""),
        )

    # A 200 answered the question; layer 2 was never asked.
    direct = _DIRECT.get(probe.verdict)
    if direct is not None:
        return finish(direct)

    # --- rule 1: one positive elsewhere outvotes any amount of local failure.
    if external is not None and external.checked:
        if external.reader_ok:
            return finish(Status.RESTRICTED, BONUS_READER_OK)
        if external.proxy_ok:
            return finish(Status.RESTRICTED, BONUS_PROXY_OK)
        if external.resolver_divergence:
            return finish(Status.RESTRICTED, BONUS_RESOLVER_DIVERGENCE)
        if probe.verdict is LocalVerdict.DNS_FAIL and external.any_resolved:
            # The local resolver is the outlier: two public resolvers found the
            # host this machine could not.
            ev.append(Evidence("doh", "local_resolver_diverges",
                               "public resolvers returned A records", now))
            return finish(Status.RESTRICTED, BONUS_RESOLVER_DIVERGENCE)
        if external.snapshot_after_failure:
            return finish(Status.RESTRICTED, BONUS_SNAPSHOT_AFTER_FAILURE)

    # --- rule 2: nothing contradicted the local observation.
    if probe.verdict is LocalVerdict.GONE:
        bonus = (BONUS_RESOLVERS_AGREE_NXDOMAIN
                 if external and external.resolvers_agree_nxdomain else 0.0)
        return finish(Status.GONE, bonus)
    if probe.verdict is LocalVerdict.BLOCKED:
        # 401/403/429/451 is the server refusing *us*. That is a restriction,
        # not a death certificate, and the UI contract keeps the bookmark fully
        # searchable with a badge.
        return finish(Status.RESTRICTED)
    if probe.verdict is LocalVerdict.DNS_FAIL:
        bonus = (BONUS_RESOLVERS_AGREE_NXDOMAIN
                 if external and external.resolvers_agree_nxdomain else 0.0)
        return finish(Status.UNREACHABLE, bonus)
    return finish(Status.UNREACHABLE)
