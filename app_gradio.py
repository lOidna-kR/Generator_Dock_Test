# app_gradio.py - Gradio Ask/Forge 통합 UI

from __future__ import annotations

import random
import re
from collections import Counter
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import gradio as gr

from Core import AskMode, ForgeMode
from Utils import setup_logging
from config import (
    get_category_weights_by_topic,
    get_mcq_generation_config,
    get_textbook_structure,
    validate_config,
)
from gradio.themes.base import Base
from gradio.themes.utils import colors, fonts


class TransparentTheme(Base):
    def __init__(self):
        super().__init__(
            primary_hue=colors.blue,
            secondary_hue=colors.gray,
            neutral_hue=colors.gray,
            font=fonts.GoogleFont("Pretendard"),
        )

        self.set(
            body_background_fill="transparent",
            body_background_fill_dark="transparent",
            body_text_color="#dfe6ef",
            background_fill_primary="rgba(0, 0, 0, 0)",
            background_fill_secondary="rgba(0, 0, 0, 0)",
            panel_background_fill="rgba(0, 0, 0, 0)",
            block_border_width="0px",
            block_shadow="0 0 0 0 rgba(0,0,0,0)",
            block_background_fill="rgba(0, 0, 0, 0)",
        )

        self.set(
            input_background_fill="rgba(0, 0, 0, 0)",
            input_background_fill_dark="rgba(0, 0, 0, 0)",
            input_shadow="0 0 0 0 rgba(0,0,0,0)",
            input_border_color="rgba(255, 255, 255, 0.2)",
            input_placeholder_color="#9fa6b4",
            button_primary_background_fill="rgba(255,255,255,0.12)",
            button_primary_text_color="#dfe6ef",
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


@lru_cache(maxsize=1)
def init_backend() -> Tuple[AskMode, ForgeMode, Dict[str, Any], Dict[str, List[str]], Any]:
    """Ask/Forge 백엔드를 초기화합니다."""

    if not validate_config():
        raise RuntimeError("환경 변수가 올바르게 설정되지 않았습니다. .env 파일을 확인하세요.")

    logger = setup_logging("Gradio.App")
    ask_mode = AskMode(logger=logger)

    try:
        forge_mode = ForgeMode(
            vector_store=ask_mode.vector_store,
            llm=ask_mode.llm,
            logger=logger,
        )
    except Exception as exc:
        raise RuntimeError(f"ForgeMode 초기화 실패: {exc}") from exc

    system_info = ask_mode.get_system_info()
    textbook_structure = get_textbook_structure()

    return ask_mode, forge_mode, system_info, textbook_structure, logger


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


def render_forge_result(history: List[Tuple[str, str]], mcqs: List[Dict[str, Any]], title: str, file_path: str) -> None:
    """Forge 결과를 챗봇 히스토리에 추가합니다."""

    messages = ["### 📘 Forge 결과"]
    messages.append(f"- **주제:** {title}")
    messages.append(f"- **저장 경로:** `{file_path}`")
    messages.append("\n")

    for idx, mcq in enumerate(mcqs, 1):
        question = mcq.get("question", "N/A")
        options = mcq.get("options", [])
        answer = mcq.get("answer_index", "N/A")
        explanation = mcq.get("explanation", [])
        title_meta = mcq.get("doc_title", "N/A")
        part = mcq.get("selected_part", "N/A")
        chapter = mcq.get("selected_chapter", "N/A")

        messages.append(f"**문제 {idx}. {question}**")
        if options:
            messages.append("\n".join([f"{opt_idx}. {opt}" for opt_idx, opt in enumerate(options, 1)]))
        messages.append(f"✅ 정답: {answer}번")

        if explanation:
            messages.append("📖 해설")
            if isinstance(explanation, list):
                for exp_idx, exp in enumerate(explanation, 1):
                    if exp and exp.strip():
                        messages.append(f"- {exp_idx}번: {exp}")
            else:
                messages.append(f"- {explanation}")

        messages.append(f"📋 출처: {title_meta} · {part} · {chapter}")
        messages.append("---")

    history.append((None, "\n".join(messages)))


def handle_mock_exam_request(
    request_text: str,
    forge_mode: ForgeMode,
    textbook_structure: Dict[str, List[str]],
    logger,
) -> Tuple[str, List[Dict[str, Any]], List[str]]:
    """동형 모의고사 40문제를 생성하고 로그를 반환합니다."""

    config = get_mcq_generation_config()
    chapter_weights_flat: Dict[str, float] = {}
    for part, chapters in config.get("chapter_weights", {}).items():
        for chapter, weight in chapters.items():
            chapter_weights_flat[chapter] = weight

    chapter_allocation = allocate_questions_by_distribution(40, chapter_weights_flat)
    allocation_summary = Counter(chapter_allocation)
    logs: List[str] = ["### 📋 Chapter 할당 결과"]
    logs.extend([f"- {chapter}: {count}문제" for chapter, count in sorted(allocation_summary.items())])

    generated_mcqs: List[Dict[str, Any]] = []
    retry_limit = 10

    for index, selected_chapter in enumerate(chapter_allocation, 1):
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
                mcq = None
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

    if not generated_mcqs:
        raise RuntimeError("생성된 문제가 없습니다. 설정을 확인하세요.")

    file_path = save_mcqs_to_txt(generated_mcqs, "동형모의고사_40문제")
    return file_path, generated_mcqs, logs


def handle_forge_request(
    request_text: str,
    parsed_command: Dict[str, Any],
    forge_mode: ForgeMode,
    textbook_structure: Dict[str, List[str]],
    existing_mcqs: List[Dict[str, Any]],
    logger,
) -> Tuple[str, List[Dict[str, Any]], List[str], List[str]]:
    """일반 Forge 요청을 처리하고 결과/로그/경고를 반환합니다."""

    topic_key = parsed_command["topic_key"]
    topic_type = parsed_command["topic_type"]
    count = parsed_command["count"]
    display_name = parsed_command["display_name"]

    filtered_structure = build_filtered_structure(topic_key, topic_type, textbook_structure)

    category_weights = get_category_weights_by_topic(topic_key)
    if not category_weights:
        category_weights = get_category_weights_by_topic(display_name)

    logs: List[str] = [f"### ⚙️ '{display_name}' 범위로 {count}개 생성"]
    generated_mcqs: List[Dict[str, Any]] = []
    warnings: List[str] = []
    retry_limit = 10

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
                mcq, existing_mcqs + generated_mcqs
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

    if not generated_mcqs:
        raise RuntimeError("생성된 문제가 없습니다. 요청을 다시 시도해주세요.")

    file_path = save_mcqs_to_txt(generated_mcqs, f"{display_name}_{len(generated_mcqs)}개")
    return file_path, generated_mcqs, logs, warnings


def chat_function(message: str, history: List[Tuple[str, str]], app_state: Dict[str, Any]) -> Tuple[str, List[Tuple[str, str]]]:
    """Gradio가 호출하는 메인 핸들러."""

    ask_mode, forge_mode, system_info, textbook_structure, logger = init_backend()

    app_state = app_state or {}
    mode = app_state.get("mode", "Ask")
    if not message.strip():
        return "", history 

    if mode == "Ask":
        try:
            result = ask_mode.process(message)
        except Exception as exc:
            error_msg = f"❌ 오류: {exc}"
            history.append((message, error_msg))
            return "", history

        answer = result.get("answer", "답변을 생성하지 못했습니다.")
        pipeline = result.get("pipeline", "rag")
        routing_reason = result.get("routing_reason")
        sources = result.get("source_documents", [])

        response_lines = [answer]
        if pipeline != "rag":
            response_lines.append("💡 문서 검색 없이 일반 대화로 응답했습니다.")
            if routing_reason:
                response_lines.append(f"- 판단 근거: {routing_reason}")
        elif sources:
            response_lines.append("📚 참고 문서")
            for idx, doc in enumerate(sources, 1):
                metadata = doc.get("metadata", {})
                title = metadata.get("title") or metadata.get("doc_title") or metadata.get("source")
                part = metadata.get("part") or metadata.get("chapter")
                page = metadata.get("page_number")
                segments = [seg for seg in [title, part, f"p.{page}" if page is not None else None] if seg]
                label = " · ".join(segments) if segments else "문서"
                response_lines.append(f"- {idx}. {label}")

        history.append((message, "\n".join(response_lines)))
        return "", history

    # Forge 모드
    parsed = parse_forge_request(message)
    if parsed is None:
        history.append((message, "⚠️ 요청을 이해하지 못했습니다. 범위와 개수를 다시 입력해주세요."))
        return "", history

    try:
        if parsed["topic_type"] == "mock_exam":
            file_path, mcqs, logs = handle_mock_exam_request(message, forge_mode, textbook_structure, logger)
            history.append((message, "\n".join(logs)))
            render_forge_result(history, mcqs, "동형모의고사 40문제", file_path)
        else:
            file_path, mcqs, logs, warnings = handle_forge_request(
                message,
                parsed,
                forge_mode,
                textbook_structure,
                app_state.setdefault("forge_mcqs", []),
                logger,
            )
            history.append((message, "\n".join(logs)))
            render_forge_result(history, mcqs, parsed["display_name"], file_path)
            app_state.setdefault("forge_mcqs", []).extend(mcqs)
            if warnings:
                history.append((None, "\n".join([f"⚠️ {warn}" for warn in warnings])))
    except Exception as exc:
        history.append((message, f"❌ 오류: {exc}"))

    return "", history 


def handle_mode_change(new_mode: str, app_state: Dict[str, Any], history: List[Tuple[str, str]]):
    app_state = app_state or {}
    history = history or []
    app_state["mode"] = new_mode
    if new_mode == "Forge":
        history.append((None, "✅ Forge Mode로 전환되었습니다. 예: '각론 5문제 만들어줘'"))
    else:
        history.append((None, "✅ Ask Mode로 전환되었습니다. 질문을 입력하세요."))
    return app_state, history
# -----------------------------------------------------------------
custom_css = """
body::-webkit-scrollbar {
    display: none !important;
}

body {
    scrollbar-width: none !important;
}

#main_input_row {
    justify-content: center !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    padding: 0 !important;
    --block-background-fill: transparent !important;
    --block-shadow: none !important;
    --panel-background-fill: transparent !important;
    --body-background-fill: transparent !important;
}

#chat_input_container {
    width: 60% !important;
    max-width: 60% !important;
    margin: 0 auto 16px auto !important;
    background-color: transparent !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    border-radius: 16px !important;
    padding: 14px 18px 10px 18px !important;
    display: flex !important;
    flex-direction: column !important;
    gap: 6px !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    --block-background-fill: transparent !important;
    --block-shadow: none !important;
    --input-background-fill: transparent !important;
    --input-border-color: rgba(255, 255, 255, 0.2) !important;
}

#chat_input_container::before,
#chat_input_container::after {
    display: none !important;
}

#chat_input_container * {
    background-color: transparent !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
    border-style: none !important;
}

#chat_input_textbox {
    width: 100% !important;
    background-color: transparent !important;
    border: none !important;
    box-shadow: none !important;
    --block-background-fill: transparent !important;
    --block-shadow: none !important;
    --block-border-color: transparent !important;
    border-radius: 10px !important;
    padding: 0 !important;
}

#chat_input_textbox * {
    background-color: transparent !important;
    box-shadow: none !important;
    backdrop-filter: none !important;
}

#chat_input_textbox::before,
#chat_input_textbox::after {
    display: none !important;
}

#chat_input_textbox textarea {
    min-height: 52px !important;
    border-radius: 10px !important;
    border: none !important;
    box-shadow: none !important;
    background-color: transparent !important;
    font-size: 1.1rem !important;
    padding: 12px 16px !important;
    color: inherit !important;
    overflow-y: hidden !important;
    overflow-x: hidden !important;
    scrollbar-width: none !important;
}

#chat_input_textbox textarea::-webkit-scrollbar {
    display: none !important;
}

textarea[data-testid="textbox"] {
    background-color: transparent !important;
    scrollbar-width: none !important;
}

textarea[data-testid="textbox"]::-webkit-scrollbar {
    display: none !important;
}

#chat_input_textbox textarea:focus {
    outline: none !important;
    border: none !important;
    box-shadow: none !important;
}

#chat_input_bottom {
    border-top: none !important;
    width: 100% !important;
    display: flex !important;
    justify-content: space-between !important;
    align-items: center !important;
    gap: 12px !important;
    min-height: 36px !important;
    padding-top: 0 !important;
    background-color: transparent !important;
}

#mode_select {
    width: 90px !important;
    min-width: 90px !important;
    max-width: 90px !important;
    height: 30px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: flex-start !important;
    margin: 0 !important;
}

#mode_select > div {
    margin: 0 !important;
    width: 100% !important;
    display: flex !important;
}

#mode_select .auto-margin {
    margin: 0 !important;
}

#mode_select button,
#mode_select div > button {
    width: 100% !important;
    height: 30px !important;
    font-size: 0.75rem !important;
    border-radius: 10px !important;
    border: 1px solid rgba(255, 255, 255, 0.18) !important;
    background-color: rgba(255, 255, 255, 0.08) !important;
    padding: 0 8px !important;
    display: flex !important;
    align-items: center !important;
    justify-content: space-between !important;
    color: inherit !important;
}

#mode_select button span,
#mode_select div > button span {
    font-size: 0.75rem !important;
}

#mode_select button svg,
#mode_select div > button svg {
    margin-left: auto !important;
}

#mode_select input[role="listbox"] {
    width: 100% !important;
    text-align: left !important;
    padding: 0 !important;
    margin: 0 !important;
    font-size: 0.75rem !important;
}

#mode_select::after,
#mode_select::before {
    box-shadow: none !important;
}

#chat_submit_button {
    background-color: rgba(255, 255, 255, 0.12) !important;
    color: inherit !important;
    border-radius: 50% !important;
    width: 40px !important;
    min-width: 40px !important;
    max-width: 40px !important;
    height: 40px !important;
    padding: 0 !important;
    display: flex !important;
    justify-content: center !important;
    align-items: center !important;
}
"""

# -----------------------------------------------------------------
# 4. (핵심) gr.Blocks UI 조립
# -----------------------------------------------------------------
with gr.Blocks(theme=TransparentTheme(), css=custom_css) as demo:
    
    gr.Markdown("# 🤖 Generator Dock Gradio 챗봇")
    
    chatbot = gr.Chatbot(label="대화창", height=500)
    app_state = gr.State({
        "mode": "Ask",
        "forge_mcqs": [],
    })

    with gr.Row(elem_id="main_input_row"):
        chat_column = gr.Column(elem_id="chat_input_container")
        with chat_column:
            msg_input = gr.Textbox(
                placeholder="질문 또는 Forge 요청을 입력하세요...",
                elem_id="chat_input_textbox",
                show_label=False,
                lines=1,
            )

            with gr.Row(elem_id="chat_input_bottom"):
                mode_select = gr.Dropdown(
                    ["Ask", "Forge"],
                    value="Ask",
                    label="모드",
                    show_label=False,
                    elem_id="mode_select",
                    container=False,
                )
                submit_btn = gr.Button(
                    "▶️",
                    elem_id="chat_submit_button",
                    variant="primary",
                    size="sm",
                )

    # -----------------------------------------------------------------
    # 5. 이벤트 핸들러 연결
    # -----------------------------------------------------------------

    mode_select.change(
        fn=handle_mode_change,
        inputs=[mode_select, app_state, chatbot],
        outputs=[app_state, chatbot],
    )

    msg_input.submit(
        fn=chat_function,
        inputs=[msg_input, chatbot, app_state],
        outputs=[msg_input, chatbot],
    )

    submit_btn.click(
        fn=chat_function,
        inputs=[msg_input, chatbot, app_state],
        outputs=[msg_input, chatbot],
    )

# -----------------------------------------------------------------
# 6. 앱 실행
# -----------------------------------------------------------------
if __name__ == "__main__":
    demo.launch()