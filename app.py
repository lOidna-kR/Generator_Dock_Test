"""Streamlit 기반 Ask/Forge 통합 UI."""

from __future__ import annotations

import random
import re
from collections import Counter
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import streamlit as st

from Core import AskMode, ForgeMode
from Utils import setup_logging
from config import (
    get_category_weights_by_topic,
    get_mcq_generation_config,
    get_textbook_structure,
    validate_config,
)


FORGE_TOPIC_ALIASES: Dict[str, List[str]] = {
    "mock_exam": ["동형모의고사", "모의고사", "모의", "mock"],
    "총론": ["총론"],
    "법령": ["법령"],
    "각론": ["각론"],
    "전문심장소생술": ["전문심장소생술", "심장소생술", "심장", "acls"],
    "전문외상처치술": ["전문외상처치술", "외상처치술", "외상"],
    "내과응급": ["내과응급", "내과"],
    "특수응급": ["특수응급", "특수"],
}

FORGE_TOPIC_TYPES: Dict[str, str] = {
    "mock_exam": "mock_exam",
    "총론": "part",
    "법령": "part",
    "각론": "part",
    "전문심장소생술": "chapter",
    "전문외상처치술": "chapter",
    "내과응급": "chapter",
    "특수응급": "chapter",
}

FORGE_TOPIC_DISPLAY_NAMES: Dict[str, str] = {
    "mock_exam": "동형모의고사",
    "총론": "총론",
    "법령": "법령",
    "각론": "각론",
    "전문심장소생술": "전문심장소생술",
    "전문외상처치술": "전문외상처치술",
    "내과응급": "내과응급",
    "특수응급": "특수응급",
}


@st.cache_resource(show_spinner=False)
def load_app_components() -> Tuple[AskMode, ForgeMode, Dict[str, Any], Dict[str, List[str]], Any]:
    """Streamlit 앱에서 사용할 Ask/Forge 컴포넌트를 초기화합니다."""

    if not validate_config():
        raise RuntimeError("환경 변수가 올바르게 설정되지 않았습니다. .env 파일을 확인하세요.")

    logger = setup_logging("Streamlit.App")
    ask_mode = AskMode(logger=logger)

    try:
        forge_mode = ForgeMode(
            vector_store=ask_mode.vector_store,
            llm=ask_mode.llm,
            logger=logger,
        )
    except Exception as exc:  # pragma: no cover - 초기화 실패는 사용자 환경 문제
        raise RuntimeError(f"ForgeMode 초기화 실패: {exc}") from exc

    system_info = ask_mode.get_system_info()
    textbook_structure = get_textbook_structure()

    return ask_mode, forge_mode, system_info, textbook_structure, logger


def init_session_state() -> None:
    """필요한 세션 상태 키를 초기화합니다."""

    if "messages" not in st.session_state:
        st.session_state.messages: List[Dict[str, Any]] = []
    if "ui_mode" not in st.session_state:
        st.session_state.ui_mode = "Ask"
    if "forge_results" not in st.session_state:
        st.session_state.forge_results: List[Dict[str, Any]] = []
    if "forge_generated_mcqs" not in st.session_state:
        st.session_state.forge_generated_mcqs: List[Dict[str, Any]] = []
    if "forge_feedback" not in st.session_state:
        st.session_state.forge_feedback: Optional[str] = None


def reset_forge_state() -> None:
    """Forge 모드 관련 상태를 초기화합니다."""

    st.session_state.forge_results = []
    st.session_state.forge_generated_mcqs = []
    st.session_state.forge_feedback = None


def render_sidebar(system_info: Dict[str, Any]) -> None:
    """사이드바 UI를 렌더링합니다."""

    st.sidebar.header("옵션")
    sidebar_mode = st.sidebar.selectbox(
        "모드",
        options=("Ask", "Forge"),
        index=0 if st.session_state.ui_mode == "Ask" else 1,
        key="sidebar_mode_selector",
    )
    if sidebar_mode != st.session_state.ui_mode:
        st.session_state.ui_mode = sidebar_mode
        st.session_state.messages = []
        reset_forge_state()
        st.rerun()

    if st.sidebar.button("대화/결과 초기화"):
        st.session_state.messages = []
        reset_forge_state()
        st.sidebar.success("초기화했습니다.")

    st.sidebar.divider()
    st.sidebar.header("시스템 정보")
    st.sidebar.caption("현재 Vertex AI · LangGraph 구성을 요약합니다.")
    try:
        st.sidebar.json(system_info, expanded=False)
    except TypeError:
        st.sidebar.write(system_info)


def render_source_documents(sources: List[Dict[str, Any]]) -> None:
    """응답에 포함된 참고 문서를 출력합니다."""

    if not sources:
        return

    st.markdown("**📚 참고 문서**")
    for idx, doc in enumerate(sources, 1):
        metadata = doc.get("metadata", {})
        title = metadata.get("title") or metadata.get("doc_title") or metadata.get("source")
        part = metadata.get("part") or metadata.get("chapter")
        page = metadata.get("page_number")
        segments = []
        if title:
            segments.append(title)
        if part:
            segments.append(str(part))
        if page is not None:
            segments.append(f"p.{page}")

        header = " · ".join(segments) if segments else "문서"
        st.markdown(f"{idx}. {header}")


def save_mcqs_to_txt(mcqs: List[Dict[str, Any]], topic_name: str) -> str:
    """생성된 MCQ를 텍스트 파일로 저장합니다."""

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcq_{topic_name}_{timestamp}.txt"
    output_dir = Path("Data") / "Result"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename

    with open(output_path, "w", encoding="utf-8") as file:
        file.write("=" * 70 + "\n")
        file.write("MCQ 생성 결과\n")
        file.write(f"주제: {topic_name}\n")
        file.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        file.write(f"총 문제 수: {len(mcqs)}개\n")
        file.write("=" * 70 + "\n\n")

        for idx, mcq in enumerate(mcqs, 1):
            file.write(f"[문제 {idx}]\n")
            file.write("-" * 70 + "\n\n")
            file.write(f"질문: {mcq.get('question', 'N/A')}\n\n")

            for option_idx, option in enumerate(mcq.get("options", []), 1):
                file.write(f"{option_idx}. {option}\n")

            file.write(f"\n✅ 정답: {mcq.get('answer_index', 0)}번\n\n")

            explanation = mcq.get("explanation", [])
            if explanation:
                file.write("📖 해설:\n")
                if isinstance(explanation, list):
                    for exp_idx, exp in enumerate(explanation, 1):
                        if exp and exp.strip():
                            file.write(f"  {exp_idx}번: {exp}\n")
                else:
                    file.write(f"  {explanation}\n")
                file.write("\n")

            title = mcq.get("doc_title", "N/A")
            part = mcq.get("selected_part", "N/A")
            chapter = mcq.get("selected_chapter", "N/A")
            file.write(f"📋 출처: {title} - {part} - {chapter}\n")
            file.write("\n" + "=" * 70 + "\n\n")

    return str(output_path)


def is_duplicate_mcq(
    new_mcq: Dict[str, Any],
    existing_mcqs: List[Dict[str, Any]],
    similarity_threshold: float = 0.8,
) -> bool:
    """새로 생성한 MCQ가 기존 항목과 중복인지 검사합니다."""

    new_question = new_mcq.get("question", "").strip().lower()
    new_options = new_mcq.get("options", [])
    new_chapter = new_mcq.get("selected_chapter", "")

    new_content = new_question + " " + " ".join(opt.strip().lower() for opt in new_options)

    same_chapter_mcqs = []
    if new_chapter:
        same_chapter_mcqs = [
            mcq for mcq in existing_mcqs if mcq.get("selected_chapter", "") == new_chapter
        ]
    chapter_threshold = 0.75 if same_chapter_mcqs else similarity_threshold

    for existing_mcq in existing_mcqs:
        existing_question = existing_mcq.get("question", "").strip().lower()
        existing_options = existing_mcq.get("options", [])

        if new_question == existing_question:
            return True

        existing_content = (
            existing_question + " " + " ".join(opt.strip().lower() for opt in existing_options)
        )
        current_threshold = (
            chapter_threshold
            if existing_mcq.get("selected_chapter", "") == new_chapter
            else similarity_threshold
        )

        shorter = min(len(new_content), len(existing_content))
        if shorter == 0:
            continue

        common_chars = sum(1 for a, b in zip(new_content, existing_content) if a == b)
        similarity = common_chars / shorter

        if similarity >= current_threshold:
            return True

        new_options_lower = [opt.strip().lower() for opt in new_options]
        existing_options_lower = [opt.strip().lower() for opt in existing_options]
        matching_options = sum(1 for opt in new_options_lower if opt in existing_options_lower)
        if matching_options >= 3:
            return True

    return False


def allocate_questions_by_distribution(num_questions: int, weights: Dict[str, float]) -> List[str]:
    """가중치에 따라 항목을 결정론적으로 배분합니다."""

    if not weights or num_questions <= 0:
        return []

    total_weight = sum(weights.values())
    if total_weight == 0:
        return []

    allocations: Dict[str, int] = {}
    fractional_parts: Dict[str, float] = {}

    for name, weight in weights.items():
        count = (weight / total_weight) * num_questions
        integer_part = int(count)
        allocations[name] = integer_part
        fractional_parts[name] = count - integer_part

    total_allocated = sum(allocations.values())
    remaining = num_questions - total_allocated

    if remaining > 0:
        sorted_by_fraction = sorted(
            fractional_parts.items(), key=lambda item: item[1], reverse=True
        )
        for idx in range(remaining):
            name = sorted_by_fraction[idx][0]
            allocations[name] += 1

    result: List[str] = []
    for name, count in allocations.items():
        result.extend([name] * count)

    random.shuffle(result)
    return result


def build_filtered_structure(
    topic_key: str, topic_type: str, textbook_structure: Dict[str, List[str]]
) -> Dict[str, List[str]]:
    """요청된 범위를 ForgeMode 입력 구조에 맞게 변환합니다."""

    if topic_type == "part":
        if topic_key not in textbook_structure:
            raise ValueError(f"'{topic_key}' 범위를 교재 구조에서 찾을 수 없습니다.")
        return {topic_key: textbook_structure[topic_key]}

    if topic_type == "chapter":
        for part, chapters in textbook_structure.items():
            if topic_key in chapters:
                return {part: [topic_key]}
        raise ValueError(f"'{topic_key}' 챕터를 교재 구조에서 찾을 수 없습니다.")

    raise ValueError("Mock Exam은 별도 처리 대상입니다.")


def parse_forge_request(text: str) -> Optional[Dict[str, Any]]:
    """자연어 입력에서 Forge 요청 정보를 추출합니다."""

    normalized = re.sub(r"\s+", "", text.lower())

    topic_key: Optional[str] = None
    for key, aliases in FORGE_TOPIC_ALIASES.items():
        if any(alias in normalized for alias in aliases):
            topic_key = key
            break

    if topic_key is None:
        return None

    count_match = re.search(r"(\d+)", text)
    count = int(count_match.group(1)) if count_match else 1
    count = max(1, min(50, count))

    topic_type = FORGE_TOPIC_TYPES.get(topic_key, "part")
    if topic_type == "mock_exam":
        count = 40

    return {
        "topic_key": topic_key,
        "topic_type": topic_type,
        "count": count,
        "display_name": FORGE_TOPIC_DISPLAY_NAMES.get(topic_key, topic_key),
    }


def display_mcq(mcq: Dict[str, Any], index: int) -> None:
    """Streamlit 컴포넌트로 MCQ를 출력합니다."""

    st.markdown(f"**문제 {index}. {mcq.get('question', 'N/A')}**")
    options = mcq.get("options", [])
    if options:
        st.markdown("\n".join([f"{idx}. {opt}" for idx, opt in enumerate(options, 1)]))

    st.markdown(f"✅ **정답:** {mcq.get('answer_index', 0)}번")

    explanation = mcq.get("explanation", [])
    if explanation:
        st.markdown("📖 **해설**")
        if isinstance(explanation, list):
            for idx, exp in enumerate(explanation, 1):
                if exp and exp.strip():
                    st.markdown(f"- {idx}번: {exp}")
        else:
            st.markdown(f"- {explanation}")

    title = mcq.get("doc_title", "N/A")
    part = mcq.get("selected_part", "N/A")
    chapter = mcq.get("selected_chapter", "N/A")
    st.caption(f"📋 출처: {title} · {part} · {chapter}")


def record_forge_result(
    request_text: str,
    title: str,
    mcqs: List[Dict[str, Any]],
    file_path: str,
    warnings: Optional[List[str]] = None,
) -> None:
    """세션 상태에 Forge 생성 결과를 저장합니다."""

    st.session_state.forge_generated_mcqs.extend(mcqs)
    st.session_state.forge_results.insert(
        0,
        {
            "request": request_text,
            "title": title,
            "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "mcqs": mcqs,
            "file_path": file_path,
            "warnings": warnings or [],
        },
    )


def handle_mock_exam_request(
    request_text: str,
    forge_mode: ForgeMode,
    textbook_structure: Dict[str, List[str]],
    logger,
) -> None:
    """동형 모의고사 40문제를 생성하고 결과를 표시합니다."""

    config = get_mcq_generation_config()
    chapter_weights_flat: Dict[str, float] = {}
    for part, chapters in config.get("chapter_weights", {}).items():
        for chapter, weight in chapters.items():
            chapter_weights_flat[chapter] = weight

    chapter_allocation = allocate_questions_by_distribution(40, chapter_weights_flat)
    allocation_summary = Counter(chapter_allocation)

    st.markdown("#### 📋 Chapter 할당 결과")
    for chapter, count in sorted(allocation_summary.items()):
        st.markdown(f"- {chapter}: {count}문제")

    status_container = st.container()
    progress_bar = st.progress(0)
    logs: List[str] = []
    generated_mcqs: List[Dict[str, Any]] = []
    retry_limit = 10

    for index, selected_chapter in enumerate(chapter_allocation, 1):
        progress_bar.progress(index / 40)
        chapter_weights = get_category_weights_by_topic(selected_chapter)
        retry_count = 0
        while retry_count < retry_limit:
            try:
                mcq = forge_mode.generate_mcq(
                    topics_hierarchical=textbook_structure,
                    topics_nested=None,
                    user_topic=selected_chapter,
                    max_retries=6,
                    category_weights=chapter_weights,
                )
            except Exception as exc:
                logger.error(f"동형모의고사 [{index}] 실패: {exc}")
                logs.append(f"[{index}/40] ❌ {selected_chapter}: {exc}")
                break

            if mcq and not is_duplicate_mcq(mcq, generated_mcqs):
                generated_mcqs.append(mcq)
                logs.append(f"[{index}/40] ✅ {selected_chapter} 문제 생성 완료")
                break

            retry_count += 1
            logs.append(
                f"[{index}/40] 🔄 {selected_chapter} 중복 감지, 재시도 ({retry_count}/{retry_limit})"
            )

        if retry_count >= retry_limit:
            logs.append(f"[{index}/40] ⚠️ {selected_chapter} 중복 방지 실패")

        status_container.markdown("\n".join(logs))

    progress_bar.progress(1.0)

    if not generated_mcqs:
        st.warning("생성된 문제가 없습니다. 설정을 확인하세요.")
        return

    file_path = save_mcqs_to_txt(generated_mcqs, "동형모의고사_40문제")
    record_forge_result(
        request_text=request_text,
        title="동형모의고사 40문제",
        mcqs=generated_mcqs,
        file_path=file_path,
    )
    st.success(f"동형모의고사 결과를 저장했습니다: {file_path}")


def handle_forge_request(
    request_text: str,
    parsed_command: Dict[str, Any],
    forge_mode: ForgeMode,
    textbook_structure: Dict[str, List[str]],
    logger,
) -> None:
    """일반 Forge 요청을 처리합니다."""

    topic_key = parsed_command["topic_key"]
    topic_type = parsed_command["topic_type"]
    count = parsed_command["count"]
    display_name = parsed_command["display_name"]

    try:
        filtered_structure = build_filtered_structure(topic_key, topic_type, textbook_structure)
    except ValueError as exc:
        st.error(str(exc))
        return

    category_weights = get_category_weights_by_topic(topic_key)
    if not category_weights:
        category_weights = get_category_weights_by_topic(display_name)

    status_container = st.container()
    logs: List[str] = []
    generated_mcqs: List[Dict[str, Any]] = []
    warnings: List[str] = []
    retry_limit = 10

    with st.spinner(f"'{display_name}' 범위로 {count}개 문제 생성 중..."):
        for index in range(1, count + 1):
            retry_count = 0
            while retry_count < retry_limit:
                try:
                    mcq = forge_mode.generate_mcq(
                        topics_hierarchical=filtered_structure,
                        topics_nested=None,
                        user_topic=topic_key if topic_type == "chapter" else None,
                        max_retries=6,
                        category_weights=category_weights if category_weights else None,
                    )
                except Exception as exc:
                    logger.error(f"Forge 문제 생성 실패: {exc}")
                    logs.append(f"[{index}/{count}] ❌ 오류 발생: {exc}")
                    mcq = None
                    break

                if mcq and not is_duplicate_mcq(
                    mcq, st.session_state.forge_generated_mcqs + generated_mcqs
                ):
                    generated_mcqs.append(mcq)
                    logs.append(f"[{index}/{count}] ✅ 생성 완료")
                    break

                retry_count += 1
                logs.append(
                    f"[{index}/{count}] 🔄 중복 감지, 재시도 ({retry_count}/{retry_limit})"
                )

            if retry_count >= retry_limit:
                msg = f"[{index}/{count}] 중복 방지 실패"
                warnings.append(msg)
                logs.append(f"[{index}/{count}] ⚠️ 중복 방지 실패")

            status_container.markdown("\n".join(logs))

    if not generated_mcqs:
        st.warning("생성된 문제가 없습니다. 요청을 다시 시도해주세요.")
        return

    file_path = save_mcqs_to_txt(generated_mcqs, f"{display_name}_{len(generated_mcqs)}개")
    record_forge_result(
        request_text=request_text,
        title=f"{display_name} {len(generated_mcqs)}문제",
        mcqs=generated_mcqs,
        file_path=file_path,
        warnings=warnings,
    )

    st.success(f"총 {len(generated_mcqs)}개 문제를 생성하고 저장했습니다: {file_path}")
    if warnings:
        st.warning("\n".join(warnings))


def render_forge_mode(
    forge_mode: ForgeMode,
    textbook_structure: Dict[str, List[str]],
    logger,
) -> None:
    """Forge 모드 UI를 렌더링합니다."""

    st.title("Forge Mode (MCQ 생성)")
    st.caption("자연어로 요청을 입력하면 해당 범위의 MCQ를 생성합니다.")
    st.markdown(
        "- 예시: `각론 5문제 만들어줘`, `전문외상처치술 문제 3개`, `동형모의고사 실행`"
    )

    if st.session_state.forge_results:
        st.markdown("### 최근 생성 결과")
        for result_idx, result in enumerate(st.session_state.forge_results, 1):
            with st.expander(f"{result_idx}. {result['title']} · {result['timestamp']}"):
                st.caption(f"요청 문장: {result['request']}")
                st.caption(f"저장 경로: `{result['file_path']}`")
                if result.get("warnings"):
                    st.warning("\n".join(result["warnings"]))
                for mcq_idx, mcq in enumerate(result["mcqs"], 1):
                    display_mcq(mcq, mcq_idx)
                    st.markdown("---")
    else:
        st.info("아직 생성된 결과가 없습니다. 아래 입력창에 요청을 입력하세요.")

    with st.form("forge_request_form", clear_on_submit=True):
        request_text = st.text_input("Forge 요청", placeholder="예) 각론 5문제 만들어줘")
        submitted = st.form_submit_button("문제 생성")

    if submitted:
        if not request_text.strip():
            st.warning("요청 문장을 입력해주세요.")
            return

        parsed = parse_forge_request(request_text)
        if parsed is None:
            st.warning("요청을 이해하지 못했습니다. 범위와 개수를 다시 입력해주세요.")
            return

        if parsed["topic_type"] == "mock_exam":
            handle_mock_exam_request(request_text, forge_mode, textbook_structure, logger)
        else:
            handle_forge_request(request_text, parsed, forge_mode, textbook_structure, logger)


def render_ask_mode(ask_mode: AskMode) -> None:
    """Ask 모드 UI를 렌더링합니다."""

    for message in st.session_state.messages:
        role = message.get("role", "user")
        content = message.get("content", "")
        sources = message.get("sources", [])
        pipeline = message.get("pipeline", "rag")
        routing_reason = message.get("routing_reason")

        with st.chat_message(role):
            st.markdown(content)
            if role == "assistant":
                if pipeline == "rag":
                    render_source_documents(sources)
                else:
                    st.caption("일반 대화로 분류되어 문서 검색 없이 응답했습니다.")
                    if routing_reason:
                        st.caption(f"판단 근거: {routing_reason}")

    prompt = st.chat_input("질문을 입력하세요")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})

    with st.chat_message("user"):
        st.markdown(prompt)

    try:
        with st.chat_message("assistant"):
            with st.spinner("답변 생성 중..."):
                result = ask_mode.process(prompt)

            answer = result.get("answer", "")
            sources = result.get("source_documents", [])
            pipeline = result.get("pipeline", "rag")
            routing_reason = result.get("routing_reason")

            st.markdown(answer or "답변을 생성하지 못했습니다.")
            if pipeline == "rag":
                render_source_documents(sources)
            else:
                st.caption("일반 대화로 분류되어 문서 검색 없이 응답했습니다.")
                if routing_reason:
                    st.caption(f"판단 근거: {routing_reason}")

        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": answer,
                "sources": sources if pipeline == "rag" else [],
                "pipeline": pipeline,
                "routing_reason": routing_reason,
            }
        )
    except Exception as exc:
        error_msg = f"답변 생성 중 오류가 발생했습니다: {exc}"
        st.error(error_msg)
        st.session_state.messages.append(
            {
                "role": "assistant",
                "content": error_msg,
                "sources": [],
            }
        )


def main() -> None:
    st.set_page_config(page_title="Generator Dock", page_icon="🤖", layout="wide")
    st.markdown(
        """
        <style>
        [data-testid="stChatMessage"] {
            padding: 0.75rem 0 !important;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    try:
        ask_mode, forge_mode, system_info, textbook_structure, logger = load_app_components()
    except Exception as exc:
        st.error(f"초기화에 실패했습니다: {exc}")
        return

    init_session_state()
    render_sidebar(system_info)

    st.divider()

    if st.session_state.ui_mode == "Forge":
        render_forge_mode(forge_mode, textbook_structure, logger)
        return

    st.title("RAG 챗봇 (Ask Mode)")
    st.write("Vertex AI Vector Search와 LangGraph 기반으로 답변을 생성합니다.")
    render_ask_mode(ask_mode)


if __name__ == "__main__":
    main()


