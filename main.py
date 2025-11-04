"""
MCQ Generator System - Forge Mode (MCQ)

MCQ 문제 생성을 위한 전용 시스템입니다.

사용법:
    python main.py
    
명령어:
    /history  : 대화 히스토리 확인
    /clear    : 히스토리 초기화
    /save     : 세션 저장
    /help     : 도움말
    /quit     : 종료
    
최신 LangChain 공식 API 사용:
    - VertexAI: LLM
    - VertexAIEmbeddings: 임베딩 (gemini-embedding-001)
    - VectorSearchVectorStore: 벡터 검색
"""

# ==================== 표준 라이브러리 ====================
import json
from datetime import datetime
from pathlib import Path
from typing import Literal, Optional, List
import random # Added for allocate_questions_by_distribution

# ==================== Google Cloud & LangChain ====================
from google.cloud import aiplatform
from langchain_google_vertexai import VertexAI, VertexAIEmbeddings, VectorSearchVectorStore

# ==================== 프로젝트 모듈 ====================
from Core import ForgeMode
from Utils import (
    setup_logging,
    add_to_history,
    clear_history,
    extract_topic_from_history,
    show_conversation_history,
    save_session,
)
from State import (
    State,
    create_state,
)
from config import (
    validate_config,
    get_textbook_structure,
    VERTEX_AI_CONFIG,
    get_gemini_model_config,
    get_retriever_config,
    get_category_weights_by_topic,
)


# ==================== 전역 State ====================

# 모듈 레벨 전역 변수
GLOBAL_STATE: Optional[State] = None


def initialize_global_state() -> None:
    """전역 State 초기화"""
    global GLOBAL_STATE
    GLOBAL_STATE = create_state()


def get_global_state() -> State:
    """전역 State 가져오기 (안전성 검증 포함)"""
    if GLOBAL_STATE is None:
        raise RuntimeError("전역 State가 초기화되지 않았습니다. initialize_global_state()를 먼저 호출하세요.")
    return GLOBAL_STATE


# ==================== 1. 시스템 초기화 ====================


def initialize_components(logger) -> tuple:
    """
    Vertex AI 컴포넌트 초기화 (LLM, Embeddings, Vector Store)
    
    Returns:
        tuple: (vector_store, llm)
    """
    retriever_config = get_retriever_config()
    gemini_config = get_gemini_model_config()
    
    # Vertex AI 초기화
    logger.info("Vertex AI 초기화 중...")
    aiplatform.init(
        project=VERTEX_AI_CONFIG["project"],
        location=VERTEX_AI_CONFIG["location"],
    )
    
    # LLM 초기화
    logger.info(f"LLM 초기화: {gemini_config['model_name']}")
    llm = VertexAI(
        model_name=gemini_config["model_name"],
        project=VERTEX_AI_CONFIG["project"],
        location=VERTEX_AI_CONFIG["location"],
        temperature=retriever_config["llm_temperature"],
        max_output_tokens=retriever_config["max_output_tokens"],
    )
    
    # Embeddings 초기화
    embedding_model = retriever_config.get("embedding_model", "gemini-embedding-001")
    logger.info(f"Embeddings 초기화: {embedding_model}")
    embeddings = VertexAIEmbeddings(
        model_name=embedding_model,
        project=VERTEX_AI_CONFIG["project"],
        location=VERTEX_AI_CONFIG["location"],
    )
    
    # Vector Store 생성
    logger.info("Vector Store 생성 중...")
    index_id = retriever_config.get("index_id")
    endpoint_id = retriever_config.get("endpoint_id")
    gcs_bucket = retriever_config.get("gcs_bucket_name")
    
    if not all([index_id, endpoint_id, gcs_bucket]):
        raise ValueError(
            "벡터 스토어 설정이 없습니다. "
            "config.py에서 index_id, endpoint_id, gcs_bucket_name을 확인하세요."
        )
    
    vector_store = VectorSearchVectorStore.from_components(
        project_id=VERTEX_AI_CONFIG["project"],
        region=VERTEX_AI_CONFIG["region"],
        gcs_bucket_name=gcs_bucket,
        index_id=index_id,
        endpoint_id=endpoint_id,
        embedding=embeddings,
        stream_update=True,
    )
    
    logger.info("✅ 모든 컴포넌트 초기화 완료")
    return vector_store, llm


# ==================== 2. 히스토리 관리 (전역 State 래퍼) ====================


def add_history(role: str, content: any, mode: str, **metadata) -> None:
    """전역 State에 히스토리 추가 (래퍼 함수)"""
    state = get_global_state()
    add_to_history(state, role=role, content=content, mode=mode, **metadata)


def show_history() -> None:
    """전역 State의 히스토리 출력 (래퍼 함수)"""
    state = get_global_state()
    show_conversation_history(state)


def clear_session_history() -> None:
    """전역 State의 히스토리 초기화 (래퍼 함수)"""
    state = get_global_state()
    clear_history(state)


def save_current_session(filename: str = None) -> None:
    """전역 State 세션 저장 (래퍼 함수)"""
    state = get_global_state()
    save_session(state, filename)


def extract_topic() -> Optional[str]:
    """전역 State에서 주제 추출 (래퍼 함수)"""
    state = get_global_state()
    return extract_topic_from_history(state, lookback=5)


# ==================== 3. UI 및 도움말 ====================


def show_help() -> None:
    """도움말 표시"""
    print("\n" + "=" * 70)
    print("📖 도움말")
    print("=" * 70)
    print("현재 모드: Forge Mode (MCQ)\n")
    
    print("공통 명령어:")
    print("  /history  - 대화 히스토리 확인")
    print("  /clear    - 히스토리 초기화")
    print("  /save     - 세션 저장")
    print("  /help     - 도움말")
    print("  /quit     - 종료\n")
    
    print("=" * 70 + "\n")


def show_menu() -> None:
    """메뉴 표시"""
    print("\n" + "=" * 70)
    print("📚 MCQ 생성 범위 선택")
    print("=" * 70)
    print("1. 총론")
    print("2. 법령")
    print("3. 전문심장소생술")
    print("4. 전문외상처치술")
    print("5. 내과응급")
    print("6. 특수응급")
    print("7. 동형모의고사 (40문제)")
    print("=" * 70 + "\n")


def get_user_choice() -> str:
    """사용자 선택 입력 받기"""
    while True:
        choice = input("선택하세요 (1-7): ").strip()
        if choice in ['1', '2', '3', '4', '5', '6', '7']:
            return choice
        elif choice.lower() in ['/quit', '/exit', '/q']:
            return 'quit'
        else:
            print("⚠️  1-7 중에서 선택해주세요.\n")


def get_question_count() -> int:
    """문제 개수 입력 받기"""
    while True:
        try:
            count_input = input("생성할 문제 개수 (1-50): ").strip()
            if count_input.lower() in ['/quit', '/exit', '/q']:
                return -1
            
            count = int(count_input)
            if 1 <= count <= 50:
                return count
            else:
                print("⚠️  1-50 사이의 숫자를 입력해주세요.\n")
        except ValueError:
            print("⚠️  숫자를 입력해주세요.\n")


def create_filtered_structure(choice: str, textbook_structure: dict) -> dict:
    """선택된 범위에 따라 필터링된 교재 구조 생성"""
    if choice == '1':  # 총론
        return {"총론": textbook_structure["총론"]}
    elif choice == '2':  # 법령
        return {"법령": textbook_structure["법령"]}
    elif choice == '3':  # 전문심장소생술
        return {"각론": ["전문심장소생술"]}
    elif choice == '4':  # 전문외상처치술
        return {"각론": ["전문외상처치술"]}
    elif choice == '5':  # 내과응급
        return {"각론": ["내과응급"]}
    elif choice == '6':  # 특수응급
        return {"각론": ["특수응급"]}
    else:
        return textbook_structure


# ==================== 4. Forge Mode (MCQ) ====================


def save_mcqs_to_txt(mcqs: list, topic_name: str = "전체") -> str:
    """MCQ를 TXT 파일로 저장"""
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"mcq_{topic_name}_{timestamp}.txt"
    
    output_dir = Path("Data") / "Result"
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = output_dir / filename
    
    with open(output_path, 'w', encoding='utf-8') as f:
        # 헤더
        f.write("=" * 70 + "\n")
        f.write("MCQ 생성 결과\n")
        f.write(f"주제: {topic_name}\n")
        f.write(f"생성 일시: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n")
        f.write(f"총 문제 수: {len(mcqs)}개\n")
        f.write("=" * 70 + "\n\n")
        
        # 각 MCQ
        for i, mcq in enumerate(mcqs, 1):
            f.write(f"[문제 {i}]\n")
            f.write("-" * 70 + "\n\n")
            f.write(f"질문: {mcq.get('question', 'N/A')}\n\n")
            
            # 보기
            for j, option in enumerate(mcq.get('options', []), 1):
                f.write(f"{j}. {option}\n")
            
            # 정답
            f.write(f"\n✅ 정답: {mcq.get('answer_index', 0)}번\n\n")
            
            # 해설
            explanation = mcq.get('explanation', [])
            if explanation:
                f.write("📖 해설:\n")
                if isinstance(explanation, list):
                    for j, exp in enumerate(explanation, 1):
                        if exp and exp.strip():
                            f.write(f"  {j}번: {exp}\n")
                else:
                    f.write(f"  {explanation}\n")
                f.write("\n")
            
            # 출처
            title = mcq.get('doc_title', 'N/A')
            part = mcq.get('selected_part', 'N/A')
            chapter = mcq.get('selected_chapter', 'N/A')
            f.write(f"📋 출처: {title} - {part} - {chapter}\n")
            f.write("\n" + "=" * 70 + "\n\n")
    
    return str(output_path)


def print_mcq_result(mcq: dict, mcq_number: int) -> None:
    """MCQ 결과를 화면에 출력"""
    print("=" * 70)
    print(f"📝 생성된 MCQ (#{mcq_number})")
    print("=" * 70)
    print(f"\n질문: {mcq.get('question', 'N/A')}\n")
    
    # 보기
    for i, option in enumerate(mcq.get('options', []), 1):
        print(f"{i}. {option}")
    
    # 정답
    print(f"\n✅ 정답: {mcq.get('answer_index', 0)}번")
    
    # 해설
    explanation = mcq.get('explanation', [])
    if explanation:
        print(f"\n📖 해설:")
        if isinstance(explanation, list):
            for i, exp in enumerate(explanation, 1):
                if exp and exp.strip():
                    print(f"  {i}번: {exp}")
        else:
            print(f"  {explanation}")
    
    # 출처
    title = mcq.get('doc_title', 'N/A')
    part = mcq.get('selected_part', 'N/A')
    chapter = mcq.get('selected_chapter', 'N/A')
    print(f"\n📋 출처: {title} - {part} - {chapter}")
    print("\n" + "=" * 70 + "\n")


def handle_mock_exam_mode(forge_mode, logger, textbook_structure) -> tuple:
    """동형모의고사 모드 - 가중치 기반 결정론적 40문제 생성"""
    
    logger.info("[동형모의고사] 가중치 기반 결정론적 40문제 생성 시작")
    print("\n🎯 동형모의고사 40문제 생성 중...")
    print("📊 Part별 가중치: 결정론적 할당 적용")
    print("📊 주제별 카테고리 가중치: 선택된 주제에 맞게 자동 적용\n")
    
    # 전체 교재 구조 사용 (모든 Part/Chapter 포함)
    full_structure = textbook_structure
    
    # 가중치 설정 가져오기 (config.py에서)
    from config import get_mcq_generation_config
    config = get_mcq_generation_config()
    
    # Chapter별 가중치를 하나의 평면 구조로 변환
    chapter_weights_flat = {}
    chapter_weights_config = config.get("chapter_weights", {})
    
    for part, chapters in chapter_weights_config.items():
        for chapter, weight in chapters.items():
            chapter_weights_flat[chapter] = weight
    
    # 결정론적 할당: 40문제를 가중치에 맞게 할당
    chapter_allocation = allocate_questions_by_distribution(40, chapter_weights_flat)
    
    # 할당 결과 표시
    from collections import Counter
    allocation_summary = Counter(chapter_allocation)
    print("📋 할당 결과:")
    for chapter, count in sorted(allocation_summary.items()):
        print(f"   {chapter}: {count}개")
    print()
    
    generated_mcqs = []
    mcq_count = 0
    retry_limit = 10
    rhythm_counter = {}  # 리듬 추적기 초기화
    
    # 리듬 추출 함수 임포트
    from Utils.rhythm_tracker import (
        extract_rhythm_from_mcq, 
        should_reject_rhythm,
        get_korean_rhythm_name
    )
    
    # 결정론적으로 할당된 Chapter별로 문제 생성
    for i, selected_chapter in enumerate(chapter_allocation, 1):
        retry_count = 0
        
        # Chapter에 맞는 카테고리 가중치 가져오기
        chapter_category_weights = get_category_weights_by_topic(selected_chapter)
        
        while retry_count < retry_limit:
            try:
                print(f"[{i}/40] 생성 중... ({selected_chapter})")
                
                # 특정 Chapter로 문제 생성 (리듬 카운터 전달)
                mcq = forge_mode.generate_mcq(
                    topics_hierarchical=full_structure,
                    topics_nested=None,
                    user_topic=selected_chapter,  # 특정 Chapter 지정
                    max_retries=6,
                    category_weights=chapter_category_weights,  # Chapter별 카테고리 가중치 적용
                    rhythm_counter=rhythm_counter  # 리듬 카운터 전달
                )
                
                # 리듬 추출 및 검증 (전문심장소생술만)
                if selected_chapter == "전문심장소생술":
                    rhythm = extract_rhythm_from_mcq(mcq)
                    if rhythm:
                        # 리듬이 2회 초과인지 체크
                        if should_reject_rhythm(rhythm_counter, rhythm, max_count=2):
                            retry_count += 1
                            korean_name = get_korean_rhythm_name(rhythm)
                            logger.warning(
                                f"[{i}] 리듬 '{rhythm}({korean_name})' 이미 2회 사용됨, 재시도 중... "
                                f"({retry_count}/{retry_limit})"
                            )
                            print(f"   🔄 리듬 중복 ({korean_name}), 재생성 중...")
                            continue
                
                # 중복 체크
                if mcq and not is_duplicate_mcq(mcq, generated_mcqs):
                    # 성공: 리듬 카운터 업데이트 (전문심장소생술만)
                    if selected_chapter == "전문심장소생술":
                        rhythm = extract_rhythm_from_mcq(mcq)
                        if rhythm:
                            rhythm_counter[rhythm] = rhythm_counter.get(rhythm, 0) + 1
                            korean_name = get_korean_rhythm_name(rhythm)
                            logger.info(f"[{i}] 리듬 '{rhythm}({korean_name})' 사용 (현재 {rhythm_counter[rhythm]}회)")
                    
                    generated_mcqs.append(mcq)
                    mcq_count += 1
                    print(f"   ✅ 생성 완료 - {selected_chapter}")
                    break  # 성공 시 루프 탈출
                elif mcq and is_duplicate_mcq(mcq, generated_mcqs):
                    retry_count += 1
                    logger.warning(f"[{i}] 중복 문제 발견, 재시도 중... ({retry_count}/{retry_limit})")
                    print(f"   🔄 중복 문제 감지, 재생성 중...")
                else:
                    print(f"   ❌ 생성 실패")
                    break
                    
            except Exception as e:
                logger.error(f"동형모의고사 문제 생성 실패: {e}")
                print(f"   ❌ 생성 실패: {e}")
                break
        
        if retry_count >= retry_limit:
            logger.error(f"[{i}] 최대 재시도 횟수 초과")
            print(f"   ⚠️  중복 방지 실패 (10회 재시도)")
    
    # 배치 생성 완료 후 리듬 통계 출력
    if rhythm_counter:
        print(f"\n📊 전문심장소생술 리듬 분포:")
        for rhythm, count in sorted(rhythm_counter.items(), key=lambda x: -x[1]):
            korean_name = get_korean_rhythm_name(rhythm)
            print(f"   - {korean_name} ({rhythm}): {count}개")
    
    # 결과 저장
    if generated_mcqs:
        filepath = save_mcqs_to_txt(generated_mcqs, "동형모의고사_40문제")
        print(f"\n💾 동형모의고사 저장: {filepath}")
        logger.info(f"[동형모의고사] 완료: {mcq_count}개")
    
    return generated_mcqs, mcq_count


def is_duplicate_mcq(new_mcq: dict, existing_mcqs: list, similarity_threshold: float = 0.8) -> bool:
    """
    새로운 MCQ가 기존 MCQ와 중복인지 확인
    
    질문 + 모든 보기를 결합하여 비교하여 중복 감지 정확도를 향상시킵니다.
    같은 Chapter에서 생성된 문제에 대해서는 더 엄격한 기준을 적용합니다.
    
    Args:
        new_mcq: 새로 생성된 MCQ
        existing_mcqs: 기존 MCQ 리스트
        similarity_threshold: 유사도 임계값 (기본 0.8, 80% 이상 같으면 중복)
    
    Returns:
        bool: 중복이면 True
    """
    new_question = new_mcq.get('question', '').strip().lower()
    new_options = new_mcq.get('options', [])
    new_chapter = new_mcq.get('selected_chapter', '')
    new_section_ids = set(new_mcq.get('doc_section_ids', []) or [])
    single_new_section = new_mcq.get('doc_section_id')
    if single_new_section:
        new_section_ids.add(single_new_section)
    new_document_ids = set(new_mcq.get('doc_document_ids', []) or [])
    single_new_document = new_mcq.get('doc_document_id')
    if single_new_document:
        new_document_ids.add(single_new_document)
    new_question_hash = new_mcq.get('question_hash')
    
    # 질문 + 모든 보기를 결합한 텍스트 생성
    new_content = new_question + " " + " ".join([opt.strip().lower() for opt in new_options])
    
    # 케이스 시나리오 추출 (연령, 성별, 상황)
    import re
    new_scenario = ""
    age_match = re.search(r'(\d+대|\d+세)', new_question)
    gender_match = re.search(r'(남성|여성|소아|영아)', new_question)
    location_match = re.search(r'(등산|공사|헬스장|회사|자택|사무실|병원|응급실|현장|거리|학교)', new_question)
    
    if age_match:
        new_scenario += age_match.group(1) + " "
    if gender_match:
        new_scenario += gender_match.group(1) + " "
    if location_match:
        new_scenario += location_match.group(1)
    
    # 같은 Chapter에서 생성된 문제들만 필터링 (더 엄격한 체크용)
    same_chapter_mcqs = []
    if new_chapter:
        same_chapter_mcqs = [mcq for mcq in existing_mcqs 
                            if mcq.get('selected_chapter', '') == new_chapter]
    
    # 같은 Chapter 내에서는 더 엄격한 임계값 사용 (0.85로 완화)
    chapter_threshold = 0.85 if same_chapter_mcqs else similarity_threshold
    
    # 모든 기존 문제와 비교
    for existing_mcq in existing_mcqs:
        existing_question = existing_mcq.get('question', '').strip().lower()
        existing_options = existing_mcq.get('options', [])
        
        # 기존 문제 케이스 시나리오 추출
        existing_scenario = ""
        age_match_ex = re.search(r'(\d+대|\d+세)', existing_question)
        gender_match_ex = re.search(r'(남성|여성|소아|영아)', existing_question)
        location_match_ex = re.search(r'(등산|공사|헬스장|회사|자택|사무실|병원|응급실|현장|거리|학교)', existing_question)
        
        if age_match_ex:
            existing_scenario += age_match_ex.group(1) + " "
        if gender_match_ex:
            existing_scenario += gender_match_ex.group(1) + " "
        if location_match_ex:
            existing_scenario += location_match_ex.group(1)
        
        # 케이스 시나리오가 90% 이상 유사하면 중복 (연령+성별+장소)
        if new_scenario and existing_scenario:
            # 단어 기반 비교
            new_words = set(new_scenario.split())
            existing_words = set(existing_scenario.split())
            if new_words and existing_words:
                overlap = len(new_words.intersection(existing_words))
                similarity_scenario = overlap / len(new_words)
                if similarity_scenario >= 0.9:  # 90% 이상 유사
                    return True
        existing_section_ids = set(existing_mcq.get('doc_section_ids', []) or [])
        single_existing_section = existing_mcq.get('doc_section_id')
        if single_existing_section:
            existing_section_ids.add(single_existing_section)
        existing_document_ids = set(existing_mcq.get('doc_document_ids', []) or [])
        single_existing_document = existing_mcq.get('doc_document_id')
        if single_existing_document:
            existing_document_ids.add(single_existing_document)
        existing_question_hash = existing_mcq.get('question_hash')

        # 섹션/문서 ID 중복: 대부분(70% 이상) 겹쳐야 중복으로 판단
        if new_section_ids and existing_section_ids:
            overlap_sections = len(new_section_ids.intersection(existing_section_ids))
            total_sections = len(new_section_ids)
            if total_sections > 0 and overlap_sections / total_sections >= 0.7:
                return True

        if new_document_ids and existing_document_ids:
            overlap_docs = len(new_document_ids.intersection(existing_document_ids))
            total_docs = len(new_document_ids)
            if total_docs > 0 and overlap_docs / total_docs >= 0.7:
                return True

        if new_question_hash and existing_question_hash and new_question_hash == existing_question_hash:
            return True
        
        # 정확히 같은 질문이면 중복
        if new_question == existing_question:
            return True
        
        # 질문 + 보기 결합 텍스트로 비교
        existing_content = existing_question + " " + " ".join([opt.strip().lower() for opt in existing_options])
        
        # 사용할 임계값 결정 (같은 Chapter면 더 엄격하게)
        current_threshold = chapter_threshold if existing_mcq.get('selected_chapter', '') == new_chapter else similarity_threshold
        
        # 유사도 체크 (공통 문자 비율)
        shorter = min(len(new_content), len(existing_content))
        if shorter == 0:
            continue
        
        common_chars = sum(1 for a, b in zip(new_content, existing_content) if a == b)
        similarity = common_chars / shorter
        
        if similarity >= current_threshold:
            return True
        
        # 보기별 개별 비교 (동일 보기 감지)
        new_options_lower = [opt.strip().lower() for opt in new_options]
        existing_options_lower = [opt.strip().lower() for opt in existing_options]
        
        # 4개 모두 보기가 동일해야 중복으로 간주 (완화)
        matching_options = sum(1 for opt in new_options_lower if opt in existing_options_lower)
        if matching_options >= 4:
            return True
    
    return False


def allocate_questions_by_distribution(num_questions: int, weights: dict) -> List[str]:
    """
    가중치 기반 결정론적 문제 할당
    
    Args:
        num_questions: 생성할 총 문제 개수
        weights: {item_name: weight} 딕셔너리 (예: {"전문심장소생술": 25, ...})
    
    Returns:
        List[str]: 할당된 항목 리스트 (무작위로 셔플됨)
    
    Example:
        weights = {
            "전문심장소생술": 25,
            "전문외상처치술": 22.5,
            "내과응급": 15,
            "특수응급": 5,
        }
        allocation = allocate_questions_by_distribution(40, weights)
        # 결과: ["전문심장소생술", "전문심장소생술", ...] (40개)
    """
    if not weights or num_questions <= 0:
        return []
    
    total_weight = sum(weights.values())
    if total_weight == 0:
        return []
    
    # 소수점 포함 개수 계산
    allocations = {}
    fractional_parts = {}
    
    for name, weight in weights.items():
        count = (weight / total_weight) * num_questions
        integer_part = int(count)
        allocations[name] = integer_part
        fractional_parts[name] = count - integer_part
    
    # 정수 부분 합계
    total_allocated = sum(allocations.values())
    remaining = num_questions - total_allocated
    
    # 남은 개수를 소수점이 큰 순서대로 분배
    if remaining > 0:
        sorted_by_fraction = sorted(
            fractional_parts.items(), 
            key=lambda x: x[1], 
            reverse=True
        )
        
        for i in range(remaining):
            name = sorted_by_fraction[i][0]
            allocations[name] += 1
    
    # 리스트로 변환
    result = []
    for name, count in allocations.items():
        result.extend([name] * count)
    
    # 무작위 순서로 셔플
    random.shuffle(result)
    
    return result


def handle_forge_mode(
    forge_mode: ForgeMode,
    textbook_structure: dict,
    generated_mcqs: list,
    mcq_count: int,
    logger
) -> tuple[list, int]:
    """Forge Mode - MCQ 생성 처리 (메뉴 기반)"""
    
    # 메뉴 표시
    show_menu()
    
    # 범위 선택
    choice = get_user_choice()
    if choice == 'quit':
        return generated_mcqs, mcq_count
    
    # 동형모의고사 모드 처리
    if choice == '7':
        return handle_mock_exam_mode(forge_mode, logger, textbook_structure)
    
    # 필터링된 교재 구조 생성
    filtered_structure = create_filtered_structure(choice, textbook_structure)
    
    # 문제 개수 입력
    num_questions = get_question_count()
    if num_questions == -1:  # quit
        return generated_mcqs, mcq_count
    
    # 범위 이름 설정
    range_names = {
        '1': '총론',
        '2': '법령', 
        '3': '전문심장소생술',
        '4': '전문외상처치술',
        '5': '내과응급',
        '6': '특수응급'
    }
    range_name = range_names[choice]
    
    # 주제별 카테고리 가중치 가져오기
    topic_category_weights = get_category_weights_by_topic(range_name)
    
    # 배치 생성
    if num_questions > 1:
        logger.info(f"[Forge Mode] {range_name} 범위로 {num_questions}개 배치 생성")
        print(f"\n🎯 '{range_name}' 범위로 {num_questions}개 MCQ 생성 중...")
        print(f"📊 카테고리 가중치: {topic_category_weights}\n")
        
        # 배치 생성: 같은 범위로 여러 개 생성
        batch_mcqs = []
        retry_limit = 10  # 중복 시 최대 재시도 횟수
        rhythm_counter = {}  # 리듬 추적기 초기화
        question_type_counter = {}  # 질문 형식 추적기 초기화
        time_counter = {}  # 시간대 추적기 초기화
        logic_counter = {}  # 논리(5H5T) 추적기 초기화
        
        # 다양성 추출 함수 임포트
        from Utils.rhythm_tracker import (
            extract_rhythm_from_mcq, 
            should_reject_rhythm,
            get_korean_rhythm_name
        )
        from Utils.diversity_tracker import (
            extract_question_type,
            extract_time_period
        )
        from Utils.logic_pool_tracker import (
            extract_logic_from_mcq,
            print_logic_distribution,
            LOGIC_KOREAN_NAMES
        )
        
        for i in range(num_questions):
            retry_count = 0
            while retry_count < retry_limit:
                try:
                    print(f"[{i+1}/{num_questions}] 생성 중...")
                    
                    # State에 현재 카운터들 전달
                    mcq = forge_mode.generate_mcq(
                        topics_hierarchical=filtered_structure,
                        topics_nested=None,
                        user_topic=None,  # 랜덤
                        max_retries=6,
                        category_weights=topic_category_weights,
                        rhythm_counter=rhythm_counter,  # 리듬 카운터 전달
                        question_type_counter=question_type_counter,  # 질문 형식 카운터 전달
                        time_counter=time_counter,  # 시간대 카운터 전달
                        logic_counter=logic_counter  # 논리 카운터 전달
                    )
                    
                    # 리듬 추출 및 검증
                    rhythm = extract_rhythm_from_mcq(mcq)
                    if rhythm:
                        # 리듬이 2회 초과인지 체크
                        if should_reject_rhythm(rhythm_counter, rhythm, max_count=2):
                            retry_count += 1
                            korean_name = get_korean_rhythm_name(rhythm)
                            logger.warning(
                                f"[{i+1}] 리듬 '{rhythm}({korean_name})' 이미 2회 사용됨, 재시도 중... "
                                f"({retry_count}/{retry_limit})"
                            )
                            print(f"  🔄 [{i+1}] 리듬 중복 ({korean_name}), 재생성 중...")
                            continue
                    
                    # 기존 중복 체크
                    if is_duplicate_mcq(mcq, batch_mcqs):
                        retry_count += 1
                        logger.warning(f"[{i+1}] 중복 문제 발견, 재시도 중... ({retry_count}/{retry_limit})")
                        print(f"  🔄 [{i+1}] 중복 문제 감지, 재생성 중...")
                        continue
                    
                    # 성공: 다양성 카운터 업데이트
                    # 0. 논리 카운터 (5H5T 원인)
                    logic = extract_logic_from_mcq(mcq)
                    if logic:
                        logic_counter[logic] = logic_counter.get(logic, 0) + 1
                        korean_name = LOGIC_KOREAN_NAMES.get(logic, logic)
                        logger.info(f"[{i+1}] 논리 '{korean_name}' 사용 (현재 {logic_counter[logic]}회)")
                    
                    # 1. 리듬 카운터
                    if rhythm:
                        rhythm_counter[rhythm] = rhythm_counter.get(rhythm, 0) + 1
                        korean_name = get_korean_rhythm_name(rhythm)
                        logger.info(f"[{i+1}] 리듬 '{rhythm}({korean_name})' 사용 (현재 {rhythm_counter[rhythm]}회)")
                    
                    # 2. 질문 형식 카운터
                    qtype = extract_question_type(mcq)
                    if qtype:
                        question_type_counter[qtype] = question_type_counter.get(qtype, 0) + 1
                        logger.info(f"[{i+1}] 질문 형식 '{qtype}' 사용 (현재 {question_type_counter[qtype]}개)")
                    
                    # 3. 시간대 카운터
                    time_period = extract_time_period(mcq)
                    if time_period:
                        time_counter[time_period] = time_counter.get(time_period, 0) + 1
                        logger.info(f"[{i+1}] 시간대 '{time_period}' 사용 (현재 {time_counter[time_period]}회)")
                    
                    batch_mcqs.append(mcq)
                    break  # 성공 시 루프 탈출
                    
                except Exception as e:
                    logger.error(f"MCQ {i+1} 생성 실패: {e}")
                    print(f"  ✗ [{i+1}] 실패")
                    break
            
            if retry_count >= retry_limit:
                logger.error(f"[{i+1}] 최대 재시도 횟수 초과")
                print(f"  ⚠️  [{i+1}] 중복 방지 실패 (10회 재시도)")
        
        # 배치 생성 완료 후 다양성 통계 출력
        print(f"\n📊 다양성 통계:")
        
        # 1. 리듬 분포
        if rhythm_counter:
            print(f"\n  🔹 리듬 분포:")
            for rhythm, count in sorted(rhythm_counter.items(), key=lambda x: -x[1]):
                korean_name = get_korean_rhythm_name(rhythm)
                print(f"     - {korean_name} ({rhythm}): {count}개")
        
        # 2. 질문 형식 분포
        if question_type_counter:
            print(f"\n  🔹 질문 형식 분포:")
            for qtype, count in sorted(question_type_counter.items(), key=lambda x: -x[1]):
                percentage = (count / num_questions * 100) if num_questions > 0 else 0
                print(f"     - {qtype}: {count}개 ({percentage:.1f}%)")
        
        # 3. 시간대 분포
        if time_counter:
            print(f"\n  🔹 시간대 분포:")
            for period, count in sorted(time_counter.items(), key=lambda x: -x[1]):
                print(f"     - {period}: {count}회")
        
        # 4. 논리(5H5T) 분포
        if logic_counter:
            print(f"\n  🔹 논리(5H5T) 분포:")
            for logic, count in sorted(logic_counter.items(), key=lambda x: -x[1]):
                korean_name = LOGIC_KOREAN_NAMES.get(logic, logic)
                print(f"     - {korean_name}: {count}회")
        
        # 결과 처리
        generated_mcqs.extend(batch_mcqs)
        mcq_count += len(batch_mcqs)
        
        print(f"\n✅ {len(batch_mcqs)}개 생성 완료!\n")
        logger.info(f"[Forge Mode] 완료: {len(batch_mcqs)}개")
        
        # 저장
        filepath = save_mcqs_to_txt(batch_mcqs, f"{range_name}_{num_questions}개")
        print(f"💾 자동 저장: {filepath}\n")
        
        return generated_mcqs, mcq_count
    
    # 1개 생성
    print(f"\n🎯 '{range_name}' 범위로 생성 중...")
    print(f"📊 카테고리 가중치: {topic_category_weights}\n")
    logger.info(f"[Forge Mode] 범위: {range_name}")
    
    try:
        mcq_count += 1
        
        mcq = forge_mode.generate_mcq(
            topics_hierarchical=filtered_structure,
            topics_nested=None,
            user_topic=None,  # 랜덤
            max_retries=6,
            category_weights=topic_category_weights  # 주제별 가중치 전달
        )
        
        generated_mcqs.append(mcq)
        
        # 출력
        print_mcq_result(mcq, mcq_count)
        logger.info(f"[Forge Mode] MCQ #{mcq_count} 완료")
        
        # 저장
        filepath = save_mcqs_to_txt([mcq], f"{range_name}_1개")
        print(f"💾 자동 저장: {filepath}\n")
        
    except Exception as e:
        logger.error(f"[Forge Mode] 오류: {e}", exc_info=True)
        print(f"\n❌ 오류: {e}\n")
    
    return generated_mcqs, mcq_count


# ==================== 5. 메인 함수 ====================


def main() -> None:
    """MCQ Generator System 메인 함수"""
    
    # 1. 초기화
    print("\n" + "=" * 70)
    print("🤖 MCQ Generator System")
    print("=" * 70)
    print("💡 Forge Mode (MCQ)")
    print("=" * 70 + "\n")
    
    # 설정 검증
    print("🔍 설정 검증 중...\n")
    if not validate_config():
        print("❌ 설정을 확인하고 다시 시도하세요.\n")
        return
    
    # Logger
    logger = setup_logging("Main")
    logger.info("MCQ Generator System 시작")
    
    # 컴포넌트 초기화
    print("⚙️  컴포넌트 초기화 중...\n")
    try:
        vector_store, llm = initialize_components(logger)
    except Exception as e:
        print(f"❌ 초기화 실패: {e}\n")
        logger.error(f"초기화 실패: {e}", exc_info=True)
        return
    
    # Generator 초기화
    try:
        forge_mode = ForgeMode(vector_store=vector_store, llm=llm, logger=logger)
        print("✅ Generator 초기화 완료!\n")
    except Exception as e:
        print(f"❌ Generator 실패: {e}\n")
        logger.error(f"Generator 실패: {e}", exc_info=True)
        return
    
    # 2. 전역 State 초기화
    initialize_global_state()
    state = get_global_state()
    logger.info(f"세션 시작: {state['session_id']}")
    
    state["execution_mode"] = "forge"
    
    # 교재 구조
    textbook_structure = get_textbook_structure()
    state["topics_hierarchical"] = textbook_structure
    
    
    # Forge 변수
    mcq_count = 0
    generated_mcqs = []
    
    # 3. 대화형 루프
    while True:
        try:
            # 바로 문제 생성 메뉴 실행
            generated_mcqs, mcq_count = handle_forge_mode(
                forge_mode,
                textbook_structure,
                generated_mcqs,
                mcq_count,
                logger
            )
            
            # 계속할지 물어보기
            continue_input = input("\n계속하시겠습니까? (Enter: 계속, /help: 도움말, /quit: 종료): ").strip()
            
            if continue_input.lower() in ['/quit', '/exit', '/q']:
                print("\n👋 종료합니다.\n")
                break
            
            if continue_input.lower() == '/help':
                show_help()
                continue
            
            if continue_input.lower() == '/history':
                show_history()
                continue
            
            if continue_input.lower() == '/clear':
                clear_session_history()
                print("✅ 히스토리 초기화 완료\n")
                continue
            
            if continue_input.lower() == '/save':
                save_current_session()
                continue
        
        except KeyboardInterrupt:
            print("\n\n👋 중단되었습니다.\n")
            break
        except Exception as e:
            logger.error(f"오류: {e}", exc_info=True)
            print(f"\n❌ 오류: {e}\n")
    
    # 4. 종료
    if mcq_count > 0:
        print(f"\n📊 총 {mcq_count}개 MCQ 생성")
        print("💡 모든 MCQ는 자동 저장되었습니다.\n")
    
    print("감사합니다! 👋\n")


if __name__ == "__main__":
    main()
