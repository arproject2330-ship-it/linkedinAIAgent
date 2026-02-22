"""LangGraph workflow for post generation."""

def create_post_graph():
    """Lazy import to avoid circular import with app.agents."""
    from app.workflow.graph import create_post_graph as _create
    return _create()

__all__ = ["create_post_graph"]
