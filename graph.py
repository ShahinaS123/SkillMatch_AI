from langgraph.graph import StateGraph, END
from state import SkillMatchingState
from nodes import jd_analyzer_node, candidate_analyzer_node, matching_engine_node, market_strategy_node

def create_graph():
    workflow = StateGraph(SkillMatchingState)

    # Add the nodes
    workflow.add_node("analyze_jd", jd_analyzer_node)
    workflow.add_node("analyze_candidate", candidate_analyzer_node)
    workflow.add_node("match_skills", matching_engine_node)
    workflow.add_node("generate_strategy", market_strategy_node)

    # Set the flow
    workflow.set_entry_point("analyze_jd")
    workflow.add_edge("analyze_jd", "analyze_candidate")
    workflow.add_edge("analyze_candidate", "match_skills")
    workflow.add_edge("match_skills", "generate_strategy")
    workflow.add_edge("generate_strategy", END)

    return workflow.compile()