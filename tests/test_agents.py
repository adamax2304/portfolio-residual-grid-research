from residual_grid_research.agents import AgentCache, ResearchAgents


def test_agent_output_is_cached_per_discrete_event(tmp_path):
    calls = []

    def provider(agent, payload):
        calls.append((agent, payload))
        return {"severity": "LOW_IMPACT"}

    agents = ResearchAgents(AgentCache(tmp_path / "cache.sqlite3"), provider)
    event = {"title": "routine announcement", "summary": "nothing material"}
    first = agents.event_news("XYZ", "news-1", event)
    second = agents.event_news("XYZ", "news-1", event)
    assert len(calls) == 1
    assert first["cached"] is False
    assert second["cached"] is True
    assert second["advisory_only"] is True

