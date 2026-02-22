"""Performance Intelligence Agent: analyze past posts and output best_days, best_times, etc."""
from app.services.analytics_service import AnalyticsService
from app.workflow.state import WorkflowState


async def performance_agent(state: WorkflowState) -> dict:
    """Compute performance insights from post history. Requires state['session']."""
    session = state.get("session")
    if not session:
        return {"performance_insights": {}}
    service = AnalyticsService(session)
    insights = await service.get_performance_insights()
    return {"performance_insights": insights.model_dump()}
