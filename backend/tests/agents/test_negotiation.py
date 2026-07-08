from __future__ import annotations

import pytest

from app.agents.exceptions import NegotiationError
from app.agents.negotiation import NegotiationEngine
from app.agents.types import ConsensusOutcome


def test_full_negotiation_session_resolves_to_highest_confidence_proposal():
    engine = NegotiationEngine()
    session = engine.start_session("incident-1")

    session.propose(
        agent_id="predictive_intelligence", content={"action": "evacuate_zone_a"}, confidence=0.6
    )
    session.propose(
        agent_id="resource_coordination", content={"action": "add_medic"}, confidence=0.9
    )
    session.challenge(
        agent_id="predictive_intelligence", content={"reason": "insufficient evidence"}
    )
    session.rebut(agent_id="resource_coordination", content={"reason": "historical pattern match"})
    session.vote(agent_id="predictive_intelligence", supports=True)
    session.vote(agent_id="incident_analysis", supports=False)

    decision = session.resolve()

    assert decision.outcome == ConsensusOutcome.ACCEPTED
    assert decision.decision == {"action": "add_medic"}
    assert decision.confidence == 0.9
    assert "resource_coordination" in decision.supporting_agent_ids
    assert session.turn_count == 7  # 6 turns + the resolution turn


def test_no_proposals_yields_no_consensus():
    engine = NegotiationEngine()
    session = engine.start_session("incident-2")

    decision = session.resolve()
    assert decision.outcome == ConsensusOutcome.NO_CONSENSUS


def test_resolution_before_any_proposal_is_invalid():
    engine = NegotiationEngine()
    session = engine.start_session("incident-3")

    with pytest.raises(NegotiationError):
        session.vote(agent_id="x", supports=True)


def test_cannot_add_turns_after_resolution():
    engine = NegotiationEngine()
    session = engine.start_session("incident-4")
    session.propose(agent_id="a", content={}, confidence=0.5)
    session.resolve()

    with pytest.raises(NegotiationError):
        session.propose(agent_id="b", content={}, confidence=0.5)


def test_duplicate_session_start_raises():
    engine = NegotiationEngine()
    engine.start_session("incident-5")
    with pytest.raises(NegotiationError):
        engine.start_session("incident-5")


def test_get_or_start_creates_once():
    engine = NegotiationEngine()
    first = engine.get_or_start("incident-6")
    second = engine.get_or_start("incident-6")
    assert first is second
