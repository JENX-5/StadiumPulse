"""
RiskScoringService: the deterministic (non-LLM) risk scorer referenced by
the Predictive Intelligence Agent's trigger condition (ADR-0001) and the
Redis-cache / Postgres-history split (ADR-0004).

Split of responsibilities, mirrored from `risk_score.py`'s own docstring:
  - The CURRENT score per zone lives in Redis (`risk:zone:<zone_id>`) --
    this is the hot read path the heatmap polls every few seconds.
  - Every computation is also write-through appended to the Postgres
    `risk_scores` table as history/audit trail -- NOT the hot read path.
    This service is the only writer of that table's `DETERMINISTIC` rows;
    `LLM_NARRATIVE` rows are written separately by the Predictive
    Intelligence Agent once it generates a narrative for a crossed zone.

Scoring itself (`compute_score`) is pure arithmetic, synchronous, and has
no I/O -- this is deliberate so it can be unit-tested directly without a
Redis/Postgres fixture, per the Verification Plan's "Unit tests for the
deterministic Risk Scoring Function."

NOTE ON WEIGHTS/THRESHOLD: The weights and threshold below are calibrated
to ensure crowd density + velocity dominate as the primary crush/stampede signal;
noise and historical-pattern-match are corroborating, not primary. They
are constructor parameters specifically so they can be recalibrated in the future
if needed, as per ADR-0001.
"""

from __future__ import annotations

import json
import logging
import uuid
from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Any

from redis.asyncio import Redis
from sqlalchemy import select
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.db.models.risk_score import RiskScore, RiskScoreSource

logger = logging.getLogger(__name__)


@dataclass(frozen=True, slots=True)
class RiskFactors:
    """Raw per-zone signal inputs to the deterministic scorer.

    Every field is expected in [0.0, 1.0] (already normalized upstream --
    e.g. `crowd_density` is occupancy / capacity, not a raw headcount).
    Use `.clamped()` rather than trusting callers to have normalized
    correctly -- a single noisy sensor reading should degrade one zone's
    score gracefully, not raise and break the whole scoring tick.
    """

    crowd_density: float = 0.0
    crowd_velocity: float = 0.0
    noise_level: float = 0.0
    incident_proximity: float = 0.0
    historical_pattern_match: float = 0.0

    def clamped(self) -> "RiskFactors":
        def c(v: float) -> float:
            return max(0.0, min(1.0, v))

        return RiskFactors(
            crowd_density=c(self.crowd_density),
            crowd_velocity=c(self.crowd_velocity),
            noise_level=c(self.noise_level),
            incident_proximity=c(self.incident_proximity),
            historical_pattern_match=c(self.historical_pattern_match),
        )

    def as_dict(self) -> dict[str, float]:
        return {
            "crowd_density": self.crowd_density,
            "crowd_velocity": self.crowd_velocity,
            "noise_level": self.noise_level,
            "incident_proximity": self.incident_proximity,
            "historical_pattern_match": self.historical_pattern_match,
        }


@dataclass(frozen=True, slots=True)
class RiskScoreResult:
    """Return type for a single scoring computation or cache read."""

    zone_id: str
    venue_id: str
    score: float  # 0-100
    computed_at: datetime
    contributing_factors: dict[str, float]
    crossed_threshold: bool
    threshold: float

    def as_cache_payload(self) -> dict[str, Any]:
        return {
            "zone_id": self.zone_id,
            "venue_id": self.venue_id,
            "score": self.score,
            "computed_at": self.computed_at.isoformat(),
            "contributing_factors": self.contributing_factors,
        }


DEFAULT_WEIGHTS: dict[str, float] = {
    "crowd_density": 0.35,
    "crowd_velocity": 0.30,
    "noise_level": 0.10,
    "incident_proximity": 0.15,
    "historical_pattern_match": 0.10,
}

DEFAULT_THRESHOLD = 70.0


class RiskScoringService:
    """Deterministic scorer + Redis cache + Postgres history writer.

    Constructed with a raw `redis_url` (rather than an injected client)
    to mirror `OperationalStateManager` / `TimelineEngine`'s existing
    constructor convention, so wiring in `container.py` stays consistent
    across all three Redis-backed services.
    """

    CACHE_PREFIX = "risk:zone:"
    # Cache entries expire so a crashed/stalled scorer doesn't leave the
    # heatmap showing a frozen (and increasingly wrong) zone score forever.
    CACHE_TTL_SECONDS = 300

    def __init__(
        self,
        *,
        redis_url: str,
        db_session_factory: async_sessionmaker,
        weights: dict[str, float] | None = None,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> None:
        self.redis: Redis = Redis.from_url(redis_url, decode_responses=True)
        self._session_factory = db_session_factory
        self.weights = weights or DEFAULT_WEIGHTS
        self.threshold = threshold

    # -- Pure computation (unit-testable without Redis/DB) -------------------

    def compute_score(self, factors: RiskFactors) -> tuple[float, dict[str, float]]:
        """Weighted sum of normalized factors, scaled to 0-100.

        Synchronous and side-effect-free by design -- this is the function
        the Verification Plan's deterministic-scorer unit tests target.
        """
        clamped = factors.clamped()
        breakdown = clamped.as_dict()
        raw = sum(breakdown[name] * weight for name, weight in self.weights.items())
        score = round(max(0.0, min(1.0, raw)) * 100, 2)
        return score, breakdown

    # -- Orchestrated read/write path -----------------------------------------

    async def record_score(
        self, *, venue_id: str, zone_id: str, factors: RiskFactors
    ) -> RiskScoreResult:
        """Compute, cache (Redis), and persist (Postgres history) one
        zone's score for this tick.

        `crossed_threshold` is a rising-edge flag (previous < threshold
        <= new) rather than "currently above threshold" -- this is what
        lets the caller trigger the Predictive Intelligence Agent exactly
        once per crossing instead of every tick a zone stays hot.
        """
        score, breakdown = self.compute_score(factors)
        computed_at = datetime.now(UTC)

        previous = await self.get_current_score(zone_id)
        crossed = score >= self.threshold and (
            previous is None or previous.score < self.threshold
        )

        result = RiskScoreResult(
            zone_id=zone_id,
            venue_id=venue_id,
            score=score,
            computed_at=computed_at,
            contributing_factors=breakdown,
            crossed_threshold=crossed,
            threshold=self.threshold,
        )

        await self._cache_current(result)
        await self._persist_history(result)

        if crossed:
            logger.warning(
                f"Risk threshold crossed: zone={zone_id} venue={venue_id} "
                f"score={score} threshold={self.threshold}"
            )

        return result

    async def get_current_score(self, zone_id: str) -> RiskScoreResult | None:
        """Hot-path read for the heatmap -- Redis only, never touches Postgres."""
        raw = await self.redis.get(f"{self.CACHE_PREFIX}{zone_id}")
        if not raw:
            return None
        payload = json.loads(raw)
        return self._result_from_payload(payload)

    async def get_venue_scores(
        self, venue_id: str, zone_ids: list[str]
    ) -> dict[str, RiskScoreResult]:
        """Batch fetch for the full heatmap in a single Redis round-trip."""
        if not zone_ids:
            return {}
        keys = [f"{self.CACHE_PREFIX}{zid}" for zid in zone_ids]
        raw_values = await self.redis.mget(keys)
        scores: dict[str, RiskScoreResult] = {}
        for zone_id, raw in zip(zone_ids, raw_values, strict=True):
            if not raw:
                continue
            payload = json.loads(raw)
            if payload.get("venue_id") != venue_id:
                continue  # defensive: skip stale/cross-venue key collisions
            scores[zone_id] = self._result_from_payload(payload)
        return scores

    async def get_history(
        self, zone_id: str, *, since: datetime | None = None, limit: int = 100
    ) -> list[RiskScore]:
        """Postgres read for trend charts / audit trail -- not the hot path."""
        async with self._session_factory() as session:
            stmt = (
                select(RiskScore)
                .where(RiskScore.zone_id == uuid.UUID(zone_id))
                .order_by(RiskScore.computed_at.desc())
                .limit(limit)
            )
            if since is not None:
                stmt = stmt.where(RiskScore.computed_at >= since)
            result = await session.execute(stmt)
            return list(result.scalars().all())

    async def close(self) -> None:
        await self.redis.aclose()

    # -- Internals -------------------------------------------------------------

    def _result_from_payload(self, payload: dict[str, Any]) -> RiskScoreResult:
        return RiskScoreResult(
            zone_id=payload["zone_id"],
            venue_id=payload["venue_id"],
            score=payload["score"],
            computed_at=datetime.fromisoformat(payload["computed_at"]),
            contributing_factors=payload["contributing_factors"],
            # A cache read is never itself a crossing event -- crossing is
            # only meaningful at the moment `record_score` computes a new
            # value against the previous one.
            crossed_threshold=False,
            threshold=self.threshold,
        )

    async def _cache_current(self, result: RiskScoreResult) -> None:
        await self.redis.set(
            f"{self.CACHE_PREFIX}{result.zone_id}",
            json.dumps(result.as_cache_payload()),
            ex=self.CACHE_TTL_SECONDS,
        )

    async def _persist_history(self, result: RiskScoreResult) -> None:
        async with self._session_factory() as session:
            session.add(
                RiskScore(
                    zone_id=uuid.UUID(result.zone_id),
                    score=result.score,
                    computed_at=result.computed_at,
                    source=RiskScoreSource.DETERMINISTIC,
                    contributing_factors=result.contributing_factors,
                )
            )
            await session.commit()
