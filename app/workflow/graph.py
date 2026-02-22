"""Compiled LangGraph: Performance -> Input -> Strategy -> Post -> END. Image is optional (Generate image button)."""
from langgraph.graph import START, END
from langgraph.graph import StateGraph

from app.workflow.state import WorkflowState
from app.agents.performance_agent import performance_agent
from app.agents.input_handler_agent import input_handler_agent
from app.agents.strategy_agent import strategy_agent
from app.agents.post_generator import post_generator_agent


def create_post_graph():
    """Build and compile the post-generation graph (text only; image via optional button)."""
    builder = StateGraph(WorkflowState)

    builder.add_node("performance", performance_agent)
    builder.add_node("input_handler", input_handler_agent)
    builder.add_node("strategy_agent", strategy_agent)
    builder.add_node("post_generator", post_generator_agent)

    builder.add_edge(START, "performance")
    builder.add_edge("performance", "input_handler")
    builder.add_edge("input_handler", "strategy_agent")
    builder.add_edge("strategy_agent", "post_generator")
    builder.add_edge("post_generator", END)

    return builder.compile()
