from agent.agents.rag.reflection import should_pass
from agent.agents.rag.router import route_question
from agent.agents.rag.rag_graph import run_rag_round


def test_router_uses_sql_for_structured_numeric_questions():
    assert route_question("What is the total amount of invoice INV-100?") == "sql"
    assert route_question("Why was invoice INV-100 rejected?") == "rag"


def test_should_pass_uses_strict_threshold():
    assert should_pass({"relevance": 0.8, "groundedness": 0.8, "context_relevance": 0.7}) is True
    assert should_pass({"relevance": 0.7, "groundedness": 0.7, "context_relevance": 0.7}) is False


def test_retry_loop_stops_after_three_attempts():
    calls = []

    def fake_attempt(question: str, attempt: int, **kwargs):
        calls.append((question, attempt))
        return {"answer": f"attempt-{attempt}", "scores": {"relevance": 0.2, "groundedness": 0.2, "context_relevance": 0.2}, "mode": "rag"}

    result = run_rag_round("Why was invoice INV-100 rejected?", fake_attempt)

    assert result["attempts"] == 3
    assert result["low_confidence"] is True
    assert len(calls) == 3
