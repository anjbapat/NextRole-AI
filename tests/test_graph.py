from langgraph.types import Command

from nextrole import storage
from nextrole.graph import build_graph

RESUME = "Python engineer building machine learning RAG systems, data pipelines, LangGraph Azure cloud APIs leadership."
JD = "Seeking Python engineer with machine learning, RAG, data pipelines, LangGraph, and Azure."


def setup(tmp_path, monkeypatch, name):
    monkeypatch.setattr(storage, "DB_PATH", tmp_path / "nextrole.db")
    import nextrole.graph as graph_module

    monkeypatch.setattr(graph_module, "DB_PATH", tmp_path / "nextrole.db")
    return build_graph(), {"configurable": {"thread_id": name}}


def test_approval_and_persistent_checkpoint(tmp_path, monkeypatch):
    g, c = setup(tmp_path, monkeypatch, "test")
    g.invoke(
        {
            "journey_id": "test",
            "resume_text": RESUME,
            "job_description": JD,
            "demo_mode": True,
            "errors": [],
        },
        c,
    )
    assert g.get_state(c).values["status"] == "awaiting_approval"
    g.invoke(Command(resume="approve"), c)
    assert g.get_state(c).values["status"] == "ready_to_submit"
    assert storage.load_journeys()[0]["current_stage"] == "INTERVIEW_PREPARATION"


def test_rejection(tmp_path, monkeypatch):
    g, c = setup(tmp_path, monkeypatch, "reject")
    g.invoke(
        {
            "journey_id": "reject",
            "resume_text": RESUME,
            "job_description": JD,
            "demo_mode": True,
            "errors": [],
        },
        c,
    )
    g.invoke(Command(resume="reject"), c)
    assert g.get_state(c).values["status"] == "rejected"
