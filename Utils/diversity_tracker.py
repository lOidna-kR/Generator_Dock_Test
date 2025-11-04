"""
다양성 추적 유틸리티 (질문 형식, 시간대, 나이, 성별)

MCQ 생성 시 질문 형식, 시간대 등의 다양성을 추적하고
동적 제약을 생성하여 프롬프트에 삽입합니다.
"""

import re
from typing import Dict, Optional, Tuple


# ============================================================================
# 질문 형식 추출 및 추적
# ============================================================================

QUESTION_TYPE_PATTERNS = {
    # 부정형 (20%)
    "부정형": [
        r"절대.*?안.*?되는",
        r"적절.*?않은",
        r"적절하지\s*않은",
        r"부적절한",
        r"금기",
        r"해서는\s*안\s*되는",
        r"잘못된",
        r"틀린",
        r"옳지\s*않은",
    ],
    
    # 단계형 (15%)
    "단계형": [
        r"다음.*?조치",
        r"직후.*?조치",
        r"이후.*?조치",
        r"먼저.*?시행",
        r"가장.*?우선",
        r"첫.*?번째",
        r"다음.*?단계",
        r"순서",
    ],
    
    # 비교형 (10%)
    "비교형": [
        r"가장.*?적절한",
        r"가장.*?중요한",
        r"가장.*?효과적인",
        r"우선순위",
        r"가장.*?먼저",
    ],
    
    # 복수 정답형 (5%)
    "복수형": [
        r"모두.*?고르시오",
        r"모두.*?고른",      # "모두 고른 것은" 매칭
        r"모두.*?옳은",
        r"모두.*?해당",
        r"㉠㉡㉢㉣",         # 복수 선택 기호
        r"몇\s*개",
    ],
}


def extract_question_type(mcq: dict) -> str:
    """
    MCQ의 질문 형식을 추출합니다.
    
    Args:
        mcq: 생성된 MCQ 딕셔너리
    
    Returns:
        질문 형식 ("긍정형", "부정형", "단계형", "비교형", "복수형")
    
    Examples:
        >>> mcq = {"question": "다음 중 적절하지 않은 것은?"}
        >>> extract_question_type(mcq)
        '부정형'
    """
    question = mcq.get("question", "")
    
    # 우선순위: 부정형 > 복수형 > 단계형 > 비교형 > 긍정형
    for qtype, patterns in QUESTION_TYPE_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return qtype
    
    # 기본값: 긍정형 (50%)
    return "긍정형"


def get_question_type_constraint(type_counter: Dict[str, int], max_positive: int = 5, max_negative: int = 2,
                                   max_sequential: int = 2, max_comparative: int = 1, max_multiple: int = 1) -> str:
    """
    질문 형식 다양성 제약을 생성합니다 (프롬프트 삽입용).
    
    Args:
        type_counter: 질문 형식별 카운터 (예: {"긍정형": 3, "부정형": 1})
        max_positive: 긍정형 최대 개수 (기본: 5개)
        max_negative: 부정형 최대 개수 (기본: 2개)
        max_sequential: 단계형 최대 개수 (기본: 2개)
        max_comparative: 비교형 최대 개수 (기본: 1개)
        max_multiple: 복수형 최대 개수 (기본: 1개)
    
    Returns:
        프롬프트에 삽입할 제약 텍스트
    """
    if not type_counter:
        return ""
    
    max_counts = {
        "긍정형": max_positive,
        "부정형": max_negative,
        "단계형": max_sequential,
        "비교형": max_comparative,
        "복수형": max_multiple,
    }
    
    status_lines = []
    forbidden_types = []
    recommended_types = []
    
    for qtype, max_count in max_counts.items():
        current_count = type_counter.get(qtype, 0)
        
        if current_count >= max_count:
            status_lines.append(f"- {qtype}: {current_count}/{max_count}개 ❌ 최대 도달! 절대 금지")
            forbidden_types.append(qtype)
        elif current_count == 0:
            status_lines.append(f"- {qtype}: {current_count}/{max_count}개 ⭐ 아직 미사용! 우선 선택")
            recommended_types.append(qtype)
        else:
            remaining = max_count - current_count
            status_lines.append(f"- {qtype}: {current_count}/{max_count}개 ✅ {remaining}개 더 가능")
    
    status_text = "\n".join(status_lines)
    
    # 경고 메시지
    warnings = []
    if forbidden_types:
        warnings.append(f"[절대 금지] {', '.join(forbidden_types)}은 더 이상 사용할 수 없습니다!")
    if recommended_types:
        warnings.append(f"[강력 권장] {', '.join(recommended_types)}을 우선 선택하세요!")
    
    warning_text = "\n".join(warnings) if warnings else "[권장] 다양한 질문 형식을 골고루 사용하세요."
    
    return f"""

⚠️ 질문 형식 현황 (10문제 기준):
{status_text}

{warning_text}
"""


# ============================================================================
# 시간대 추출 및 추적
# ============================================================================

TIME_PERIOD_PATTERNS = {
    "새벽": [r"새벽", r"이른\s*아침", r"동이\s*트기\s*전", r"새벽\s*\d+시"],
    "오전": [r"오전", r"아침", r"점심\s*전", r"오전\s*\d+시"],
    "오후": [r"오후", r"점심\s*후", r"낮", r"오후\s*\d+시"],
    "저녁": [r"저녁", r"밤", r"야간", r"늦은\s*밤", r"저녁\s*\d+시", r"밤\s*\d+시"],
}


def extract_time_period(mcq: dict) -> Optional[str]:
    """
    MCQ의 시간대를 추출합니다.
    
    Args:
        mcq: 생성된 MCQ 딕셔너리
    
    Returns:
        시간대 ("새벽", "오전", "오후", "저녁") 또는 None
    
    Examples:
        >>> mcq = {"question": "한겨울 새벽, 60대 여성이..."}
        >>> extract_time_period(mcq)
        '새벽'
    """
    question = mcq.get("question", "")
    
    for period, patterns in TIME_PERIOD_PATTERNS.items():
        for pattern in patterns:
            if re.search(pattern, question, re.IGNORECASE):
                return period
    
    return None


def get_time_period_constraint(time_counter: Dict[str, int], max_per_period: int = 3) -> str:
    """
    시간대 다양성 제약을 생성합니다 (프롬프트 삽입용).
    
    Args:
        time_counter: 시간대별 카운터 (예: {"새벽": 2, "오전": 1})
        max_per_period: 각 시간대 최대 개수 (기본: 3개)
    
    Returns:
        프롬프트에 삽입할 제약 텍스트
    """
    if not time_counter:
        return ""
    
    all_periods = ["새벽", "오전", "오후", "저녁"]
    
    status_lines = []
    forbidden_periods = []
    recommended_periods = []
    
    for period in all_periods:
        count = time_counter.get(period, 0)
        
        if count >= max_per_period:
            status_lines.append(f"- {period}: {count}회 ❌ 최대 도달! 절대 금지")
            forbidden_periods.append(period)
        elif count == 0:
            status_lines.append(f"- {period}: {count}회 ⭐ 아직 미사용! 우선 선택")
            recommended_periods.append(period)
        else:
            remaining = max_per_period - count
            status_lines.append(f"- {period}: {count}회 ✅ {remaining}회 더 가능")
    
    status_text = "\n".join(status_lines)
    
    # 경고 메시지
    warnings = []
    if forbidden_periods:
        warnings.append(f"[절대 금지] {', '.join(forbidden_periods)} 시간대는 더 이상 사용할 수 없습니다!")
    if recommended_periods:
        warnings.append(f"[강력 권장] {', '.join(recommended_periods)} 시간대를 우선 선택하세요!")
    
    warning_text = "\n".join(warnings) if warnings else "[권장] 시간대를 골고루 분산하세요."
    
    return f"""

⚠️ 시간대 현황 (10문제 기준):
{status_text}

{warning_text}
"""


# ============================================================================
# 나이/성별 추출 (향후 확장용)
# ============================================================================

def extract_age_gender(mcq: dict) -> Tuple[Optional[int], Optional[str]]:
    """
    MCQ에서 환자의 나이와 성별을 추출합니다.
    
    Args:
        mcq: 생성된 MCQ 딕셔너리
    
    Returns:
        (나이, 성별) 튜플 (예: (60, "남성"))
        추출 실패 시 (None, None)
    
    Examples:
        >>> mcq = {"question": "60대 여성이 자택 거실에서..."}
        >>> extract_age_gender(mcq)
        (60, '여성')
    """
    question = mcq.get("question", "")
    
    # 나이 추출 (60대, 58세 등)
    age = None
    age_match = re.search(r"(\d+)대|(\d+)세", question)
    if age_match:
        if age_match.group(1):  # "60대"
            age = int(age_match.group(1))
        else:  # "58세"
            age = int(age_match.group(2))
    
    # 성별 추출
    gender = None
    if "남성" in question or "남자" in question:
        gender = "남성"
    elif "여성" in question or "여자" in question:
        gender = "여성"
    
    return age, gender


# ============================================================================
# 통합 다양성 분석
# ============================================================================

def analyze_diversity(mcq_list: list) -> dict:
    """
    생성된 MCQ 목록의 다양성을 분석합니다.
    
    Args:
        mcq_list: MCQ 딕셔너리 리스트
    
    Returns:
        다양성 분석 결과 딕셔너리
        {
            "question_types": {"긍정형": 5, "부정형": 2, ...},
            "time_periods": {"새벽": 2, "오전": 3, ...},
            "ages": [60, 58, 30, ...],
            "genders": {"남성": 6, "여성": 4}
        }
    """
    question_types = {}
    time_periods = {}
    ages = []
    genders = {"남성": 0, "여성": 0}
    
    for mcq in mcq_list:
        # 질문 형식
        qtype = extract_question_type(mcq)
        question_types[qtype] = question_types.get(qtype, 0) + 1
        
        # 시간대
        period = extract_time_period(mcq)
        if period:
            time_periods[period] = time_periods.get(period, 0) + 1
        
        # 나이/성별
        age, gender = extract_age_gender(mcq)
        if age:
            ages.append(age)
        if gender:
            genders[gender] = genders.get(gender, 0) + 1
    
    return {
        "question_types": question_types,
        "time_periods": time_periods,
        "ages": ages,
        "genders": genders,
    }

