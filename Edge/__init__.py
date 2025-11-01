"""
Edge 모듈

워크플로우의 엣지(연결) 중앙 관리

역할:
- 노드 간 연결 정의 (단순 엣지)
- 조건부 분기 로직 (조건부 엣지)
- 워크플로우 제어 흐름 관리

설계 철학:
- 엣지 로직을 한 곳에서 관리하여 워크플로우 파악 용이
- Generator.py의 복잡도 감소
- 조건부 로직 확장 용이

사용 예시:
    from Edge import build_workflow_edges, build_mcq_workflow_edges
    
    # RAG 워크플로우
    workflow = StateGraph(State)
    # ... 노드 추가
    build_workflow_edges(workflow)
    
    # MCQ 워크플로우
    mcq_workflow = StateGraph(MCQState)
    # ... 노드 추가
    build_mcq_workflow_edges(mcq_workflow)
"""

# RAG 워크플로우 엣지
from Edge.RAG import (
    build_workflow_edges,
    should_retry,
    should_use_cache,
    WorkflowEdgeConfig,
    get_workflow_description,
)

# MCQ 워크플로우 엣지
from Edge.MCQ import (
    build_mcq_workflow_edges,
    should_retry_after_validation,
    should_retry_after_retrieve,
    get_mcq_workflow_description,
)

__all__ = [
    # RAG 워크플로우
    "build_workflow_edges",
    "should_retry",
    "should_use_cache",
    "WorkflowEdgeConfig",
    "get_workflow_description",
    # MCQ 워크플로우
    "build_mcq_workflow_edges",
    "should_retry_after_validation",
    "should_retry_after_retrieve",
    "get_mcq_workflow_description",
]

