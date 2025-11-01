"""
세션 및 히스토리 관리 유틸리티

통합 Generator System의 대화 히스토리와 세션을 관리합니다.

주요 기능:
- 대화 히스토리 추가/조회/초기화
- 최근 대화에서 주제 추출
- 세션 저장/로드
- 히스토리 시각화
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

from State import State


# ==================== 히스토리 조작 ====================


def add_to_history(
    state: State,
    role: Literal["user", "assistant"],
    content: Any,
    mode: Literal["ask", "forge"],
    **metadata
) -> None:
    """
    대화 히스토리에 항목 추가
    
    Args:
        state: State
        role: "user" 또는 "assistant"
        content: 내용 (질문, 답변, MCQ 등)
        mode: "ask" 또는 "forge"
        **metadata: 추가 메타데이터 (sources, timestamp 등)
    
    Example:
        >>> add_to_history(
        ...     state,
        ...     role="user",
        ...     content="심폐소생술 압박 깊이는?",
        ...     mode="ask"
        ... )
    """
    entry = {
        "timestamp": datetime.now().isoformat(),
        "role": role,
        "mode": mode,
        "content": content,
        **metadata
    }
    
    state["conversation_history"].append(entry)


def get_recent_history(
    state: State,
    lookback: int = 5,
    mode: Optional[Literal["ask", "forge"]] = None
) -> List[Dict[str, Any]]:
    """
    최근 대화 히스토리 가져오기
    
    Args:
        state: State
        lookback: 최근 몇 개 가져올지 (기본: 5)
        mode: 특정 모드만 필터링 (None이면 전체)
    
    Returns:
        최근 대화 히스토리 리스트
    
    Example:
        >>> recent_asks = get_recent_history(state, lookback=5, mode="ask")
    """
    history = state["conversation_history"]
    
    if mode:
        history = [h for h in history if h["mode"] == mode]
    
    return history[-lookback:] if len(history) > lookback else history


def clear_history(state: State) -> None:
    """
    대화 히스토리 초기화
    
    Args:
        state: State (in-place 수정)
    """
    state["conversation_history"] = []
    state["messages"] = []


# ==================== 주제 추출 ====================


def extract_topic_from_history(state: State, lookback: int = 5) -> Optional[str]:
    """
    최근 대화에서 주제 추출 (의료 키워드 기반)
    
    Args:
        state: State
        lookback: 최근 몇 개 대화 확인 (기본: 5)
    
    Returns:
        추출된 주제 (None이면 못 찾음)
    
    Example:
        >>> topic = extract_topic_from_history(state, lookback=5)
        >>> print(topic)  # "심폐소생술"
    """
    recent = get_recent_history(state, lookback=lookback, mode="ask")
    questions = [h["content"] for h in recent if h["role"] == "user"]
    
    if not questions:
        return None
    
    # 주요 의료 키워드 리스트
    medical_keywords = [
        "심폐소생술", "CPR", "압박", "기도폐쇄", "하임리히", "복부밀어올리기",
        "외상", "출혈", "골절", "화상", "쇼크", "염좌", "탈구",
        "응급의료", "구급차", "응급실", "119", "응급처치",
        "호흡", "맥박", "의식", "평가", "생체징후",
        "환자평가", "초기평가", "2차평가", "SAMPLE", "OPQRST",
        "기도개방", "산소", "인공호흡", "제세동", "AED"
    ]
    
    # 키워드 추출
    found_keywords = []
    for q in questions:
        for keyword in medical_keywords:
            if keyword in q:
                found_keywords.append(keyword)
    
    # 가장 많이 언급된 키워드 반환
    if found_keywords:
        return max(set(found_keywords), key=found_keywords.count)
    
    # 키워드 못 찾으면 최근 질문 반환
    return questions[-1] if questions else None


def get_recent_sources_info(state: State, lookback: int = 3) -> List[str]:
    """
    최근 대화의 출처 정보 추출
    
    Args:
        state: State
        lookback: 최근 몇 개 대화 확인
    
    Returns:
        출처 정보 리스트 ["Part - Chapter", ...]
    
    Example:
        >>> sources = get_recent_sources_info(state, lookback=3)
        >>> print(sources)  # ["총론 - 심폐소생술", "각론 - 외상"]
    """
    recent = get_recent_history(state, lookback=lookback, mode="ask")
    
    sources = set()
    for h in recent:
        if h["role"] == "assistant" and "sources" in h:
            for source in h["sources"]:
                part = source.get("part", "")
                chapter = source.get("chapter", "")
                if part and chapter:
                    sources.add(f"{part} - {chapter}")
    
    return list(sources)


# ==================== 히스토리 시각화 ====================


def show_conversation_history(state: State) -> None:
    """
    대화 히스토리를 화면에 출력
    
    Args:
        state: State
    
    Example:
        >>> show_conversation_history(state)
        ======================================================================
        💬 대화 히스토리
        ======================================================================
        [1] 💬 사용자 (16:30:15)
            심폐소생술의 압박 깊이는?
        ...
    """
    print("\n" + "=" * 70)
    print("💬 대화 히스토리")
    print("=" * 70)
    
    history = state["conversation_history"]
    
    if not history:
        print("  (대화 없음)\n")
        print("=" * 70 + "\n")
        return
    
    for i, h in enumerate(history, 1):
        mode_icon = "💬" if h["mode"] == "ask" else "📝"
        role = "사용자" if h["role"] == "user" else "AI"
        timestamp = h["timestamp"].split("T")[1][:8]  # HH:MM:SS
        
        print(f"\n[{i}] {mode_icon} {role} ({timestamp})")
        
        if h["mode"] == "ask":
            content = h["content"]
            if len(content) > 100:
                content = content[:100] + "..."
            print(f"    {content}")
            
            if h["role"] == "assistant" and "sources" in h:
                print(f"    📚 출처: {len(h['sources'])}개 문서")
        else:  # forge
            if isinstance(h["content"], dict):
                question = h["content"].get("question", "")
                if len(question) > 60:
                    question = question[:60] + "..."
                print(f"    문제: {question}")
    
    # 통계
    ask_count = len([h for h in history if h["mode"] == "ask" and h["role"] == "user"])
    mcq_count = len([h for h in history if h["mode"] == "forge"])
    
    print("\n" + "=" * 70)
    print(f"📊 통계: 질문 {ask_count}개, MCQ {mcq_count}개")
    print("=" * 70 + "\n")


# ==================== 세션 저장/로드 ====================


def save_session(state: State, filename: str = None) -> None:
    """
    세션을 JSON 파일로 저장
    
    Args:
        state: State
        filename: 파일명 (None이면 자동 생성)
    
    Example:
        >>> save_session(state)
        💾 세션 저장: Logs/session_20251023_163045.json
           질문 5개, MCQ 3개 저장됨
    """
    if filename is None:
        filename = f"session_{state['session_id']}.json"
    
    filepath = Path("Logs") / filename
    filepath.parent.mkdir(parents=True, exist_ok=True)
    
    # 저장할 데이터 선택
    session_data = {
        "session_id": state["session_id"],
        "execution_mode": state["execution_mode"],
        "conversation_history": state["conversation_history"],
        "recent_chapters": state["recent_chapters"],
    }
    
    with open(filepath, 'w', encoding='utf-8') as f:
        json.dump(session_data, f, ensure_ascii=False, indent=2, default=str)
    
    ask_count = len([h for h in state["conversation_history"] if h["mode"] == "ask" and h["role"] == "user"])
    mcq_count = len([h for h in state["conversation_history"] if h["mode"] == "forge"])
    
    print(f"\n💾 세션 저장: {filepath}")
    print(f"   질문 {ask_count}개, MCQ {mcq_count}개 저장됨\n")


def load_session(state: State, filename: str) -> None:
    """
    세션을 JSON 파일에서 로드
    
    Args:
        state: State (in-place 업데이트)
        filename: 파일명
    
    Example:
        >>> load_session(state, "session_20251023_163045.json")
        ✅ 세션 로드: session_20251023_163045.json
           질문 5개, MCQ 3개 복구됨
    """
    filepath = Path("Logs") / filename
    
    if not filepath.exists():
        raise FileNotFoundError(f"세션 파일을 찾을 수 없습니다: {filepath}")
    
    with open(filepath, 'r', encoding='utf-8') as f:
        session_data = json.load(f)
    
    # State 업데이트
    state["session_id"] = session_data.get("session_id", state["session_id"])
    state["execution_mode"] = session_data.get("execution_mode", "ask")
    state["conversation_history"] = session_data.get("conversation_history", [])
    state["recent_chapters"] = session_data.get("recent_chapters", [])
    
    ask_count = len([h for h in state["conversation_history"] if h["mode"] == "ask" and h["role"] == "user"])
    mcq_count = len([h for h in state["conversation_history"] if h["mode"] == "forge"])
    
    print(f"\n✅ 세션 로드: {filename}")
    print(f"   질문 {ask_count}개, MCQ {mcq_count}개 복구됨\n")


def get_session_statistics(state: State) -> Dict[str, Any]:
    """
    세션 통계 정보 반환
    
    Args:
        state: State
    
    Returns:
        통계 정보 딕셔너리
    
    Example:
        >>> stats = get_session_statistics(state)
        >>> print(f"질문: {stats['ask_count']}개, MCQ: {stats['mcq_count']}개")
    """
    history = state["conversation_history"]
    
    ask_count = len([h for h in history if h["mode"] == "ask" and h["role"] == "user"])
    mcq_count = len([h for h in history if h["mode"] == "forge"])
    
    return {
        "session_id": state["session_id"],
        "execution_mode": state["execution_mode"],
        "total_conversations": len(history),
        "ask_count": ask_count,
        "mcq_count": mcq_count,
        "recent_chapters": len(state["recent_chapters"]),
    }

