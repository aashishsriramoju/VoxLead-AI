# tests/test_lead_scoring.py – 3 deterministic unit tests for lead qualification scoring
#
# Tests run in < 100ms with zero network or database dependencies.
# Qualification statuses:
#   hot:  score >= 70
#   warm: 40 <= score <= 69
#   cold: score < 40

import os
import sys
import pytest

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from services.lead_service import calculate_lead_score


def test_hot_lead_scoring():
    """
    Test 1: Hot Lead (Score >= 70)
    High budget ($1500), urgent timeline (7 days), detailed requirements,
    positive sentiment, and multiple conversational turns.
    Expected: Score >= 70 and status 'hot'.
    """
    score, status = calculate_lead_score(
        budget=1500.0,
        timeline_days=7,
        requirements="We need an enterprise CRM with automated email sequences, telephony integration, and 30 user seats.",
        sentiment="positive",
        turn_count=5,
    )

    assert score >= 70.0, f"Expected hot lead (>=70), got score {score}"
    assert status == "hot", f"Expected status 'hot', got '{status}'"
    # Verify subcomponent breakdown
    # Budget=25, Timeline=25, Requirements=25, Engagement=25 -> Total=100
    assert score == 100.0


def test_warm_lead_scoring():
    """
    Test 2: Warm Lead (40 <= Score <= 69)
    Moderate budget ($300), 30-day timeline, standard requirements,
    neutral sentiment, and moderate engagement.
    Expected: Score between 40 and 69 and status 'warm'.
    """
    score, status = calculate_lead_score(
        budget=300.0,
        timeline_days=25,
        requirements="Looking to track pipeline deals and client follow-ups.",
        sentiment="neutral",
        turn_count=3,
    )

    assert 40.0 <= score <= 69.0, f"Expected warm lead (40-69), got score {score}"
    assert status == "warm", f"Expected status 'warm', got '{status}'"


def test_cold_lead_scoring():
    """
    Test 3: Cold Lead (Score < 40)
    No budget disclosed, unknown timeline, vague or empty requirements,
    negative or neutral sentiment, and minimal engagement (1 turn).
    Expected: Score < 40 and status 'cold'.
    """
    score, status = calculate_lead_score(
        budget=None,
        timeline_days=None,
        requirements="",
        sentiment="negative",
        turn_count=1,
    )

    assert score < 40.0, f"Expected cold lead (<40), got score {score}"
    assert status == "cold", f"Expected status 'cold', got '{status}'"
    # Engagement alone with negative sentiment and 1 turn:
    # sentiment=0, turns=3 -> Total=3.0
    assert score == 3.0
