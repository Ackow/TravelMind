from functools import partial
from langgraph.checkpoint.base import BaseCheckpointSaver
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph
from app.agent.edges import route_after_constraints, route_after_human_interrupt
from app.agent.nodes.human import node_human_interrupt, node_prepare_review
from app.agent.nodes.planning import node_build_candidate
from app.agent.nodes.repair import node_propose_repairs
from app.agent.nodes.research import node_research_facts
from app.agent.nodes.validation import node_check_constraints
from app.agent.state import PlanState
from app.infrastructure.composite_facts_factory import CompositeFactsFactory


def create_travel_agent_graph(
    facts_factory: CompositeFactsFactory,
    checkpointer: BaseCheckpointSaver | None = None,
) -> StateGraph:
    """构建并编译 TravelMind 全功能 Agent 状态图。"""
    workflow = StateGraph(PlanState)

    # 注册所有纯函数节点
    workflow.add_node("research_facts", partial(node_research_facts, factory=facts_factory))
    workflow.add_node("build_candidate", node_build_candidate)
    workflow.add_node("check_constraints", node_check_constraints)
    workflow.add_node("propose_repairs", node_propose_repairs)
    workflow.add_node("prepare_review", node_prepare_review)
    workflow.add_node("human_interrupt", node_human_interrupt)

    # 编排固定流转边
    workflow.set_entry_point("research_facts")
    workflow.add_edge("research_facts", "build_candidate")
    workflow.add_edge("build_candidate", "check_constraints")
    workflow.add_edge("propose_repairs", "check_constraints")  # 修复后重新进行硬约束审计
    workflow.add_edge("prepare_review", "human_interrupt")

    # 编排智能条件路由边
    workflow.add_conditional_edges(
        "check_constraints",
        route_after_constraints,
        {
            "prepare_review": "prepare_review",
            "propose_repairs": "propose_repairs",
            "failed": END,
        },
    )

    workflow.add_conditional_edges(
        "human_interrupt",
        route_after_human_interrupt,
        {
            "end": END,
            "handle_feedback": "build_candidate",  # 接收反馈后带入新约束重新生成与审计
        },
    )

    # 编译图并绑定持久化检查点（默认使用内存 Saver）
    saver = checkpointer or MemorySaver()
    return workflow.compile(checkpointer=saver)