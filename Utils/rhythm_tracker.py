"""
리듬 추적 및 추출 유틸리티

MCQ에서 심전도 리듬을 추출하고, 중복을 추적합니다.
"""

import re
from typing import Dict, Optional


# 리듬 정규화 매핑 (다양한 표현 → 표준명)
RHYTHM_NORMALIZATION = {
    # 심실세동
    "심실세동": "VF",
    "VF": "VF",
    "Ventricular Fibrillation": "VF",
    
    # 무맥성 심실빈맥
    "무맥성 심실빈맥": "Pulseless VT",
    "pulseless VT": "Pulseless VT",
    "무맥성심실빈맥": "Pulseless VT",
    
    # 무수축
    "무수축": "Asystole",
    "Asystole": "Asystole",
    
    # 무맥성 전기활동
    "무맥성 전기활동": "PEA",
    "무맥성전기활동": "PEA",
    "PEA": "PEA",
    "고칼륨혈증 PEA": "PEA",
    
    # 발작성 상심실성 빈맥
    "발작성 상심실성 빈맥": "PSVT",
    "PSVT": "PSVT",
    "발작성상심실성빈맥": "PSVT",
    
    # 심방세동
    "심방세동": "AF",
    "AF": "AF",
    "Atrial Fibrillation": "AF",
    
    # 심실상성 빈맥
    "심실상성 빈맥": "SVT",
    "심실상빈맥": "SVT",
    "SVT": "SVT",
    
    # 방실차단
    "방실차단": "AV Block",
    "1도 방실차단": "AV Block",
    "2도 방실차단": "AV Block",
    "3도 방실차단": "AV Block",
    
    # 동서맥
    "동서맥": "Sinus Bradycardia",
    "Sinus Bradycardia": "Sinus Bradycardia",
    "저체온증에 의한 동서맥": "Sinus Bradycardia",
    
    # 급성 심근경색
    "급성 심근경색": "STEMI",
    "STEMI": "STEMI",
    "ST분절 상승": "STEMI",
    "ST 상승": "STEMI",
    
    # 폐색전증
    "폐색전증": "Pulmonary Embolism",
    "Pulmonary Embolism": "Pulmonary Embolism",
    
    # 자발순환 회복 후
    "자발순환회복 후": "ROSC",
    "자발순환 회복": "ROSC",
    "ROSC": "ROSC",
    "소생 후": "ROSC",
}


def extract_rhythm_from_mcq(mcq: dict) -> Optional[str]:
    """
    MCQ에서 심전도 리듬을 추출합니다.
    
    Args:
        mcq: 생성된 MCQ 딕셔너리
    
    Returns:
        정규화된 리듬명 (예: "VF", "Asystole", "PEA")
        추출 실패 시 None
    
    Examples:
        >>> mcq = {"question": '... [Image: "불규칙한 파형" - "심실세동"] ...'}
        >>> extract_rhythm_from_mcq(mcq)
        'VF'
    """
    question = mcq.get("question", "")
    
    # 1. [Image: "..." - "리듬명"] 패턴 매칭 (가장 명확한 방법)
    # 예: [Image: "불규칙하고 미세한 파형" - "심실세동"]
    match = re.search(r'\[Image:.*?-\s*"([^"]+)"\s*\]', question, re.IGNORECASE)
    if match:
        rhythm_raw = match.group(1).strip()
        return normalize_rhythm_name(rhythm_raw)
    
    # 2. 자발순환 회복 후 (ROSC) 감지
    if any(keyword in question for keyword in ["자발순환", "ROSC", "소생 후", "제세동 후 자발순환"]):
        return "ROSC"
    
    # 3. 기타 명시적 표현 감지
    for keyword, rhythm in RHYTHM_NORMALIZATION.items():
        if keyword in question:
            return rhythm
    
    # 4. 추출 실패
    return None


def normalize_rhythm_name(rhythm_raw: str) -> str:
    """
    다양한 리듬 표현을 표준명으로 정규화합니다.
    
    Args:
        rhythm_raw: 원본 리듬명 (예: "심실세동", "무수축")
    
    Returns:
        정규화된 리듬명 (예: "VF", "Asystole")
        매핑이 없으면 원본 그대로 반환
    
    Examples:
        >>> normalize_rhythm_name("심실세동")
        'VF'
        >>> normalize_rhythm_name("무수축")
        'Asystole'
    """
    rhythm_clean = rhythm_raw.strip()
    return RHYTHM_NORMALIZATION.get(rhythm_clean, rhythm_clean)


def get_rhythm_status_text(rhythm_counter: Dict[str, int], max_count: int = 2) -> str:
    """
    현재 리듬 사용 현황을 텍스트로 생성합니다 (프롬프트 삽입용).
    
    Args:
        rhythm_counter: 리듬별 사용 횟수 (예: {"VF": 2, "Asystole": 1})
        max_count: 최대 허용 횟수 (기본값: 2)
    
    Returns:
        프롬프트에 삽입할 텍스트
    
    Examples:
        >>> get_rhythm_status_text({"VF": 2, "Asystole": 1})
        '''
        ⚠️ 이미 생성된 문제의 리듬 현황:
        - VF (심실세동): 2회 ⚠️ 최대 도달! 절대 사용 금지
        - Asystole (무수축): 1회 ✅ 1회 더 가능
        
        [절대 준수] 2회 표시된 리듬은 절대 사용하지 마세요!
        '''
    """
    if not rhythm_counter:
        return ""
    
    # 리듬별 상태 생성
    status_lines = []
    forbidden_rhythms = []
    
    for rhythm, count in sorted(rhythm_counter.items(), key=lambda x: -x[1]):  # 많이 사용된 순
        korean_name = get_korean_rhythm_name(rhythm)
        
        if count >= max_count:
            status_lines.append(f"- {rhythm} ({korean_name}): {count}회 ⚠️ 최대 도달! 절대 사용 금지")
            forbidden_rhythms.append(rhythm)
        else:
            remaining = max_count - count
            status_lines.append(f"- {rhythm} ({korean_name}): {count}회 ✅ {remaining}회 더 가능")
    
    # 프롬프트 텍스트 생성
    status_text = "\n".join(status_lines)
    
    if forbidden_rhythms:
        forbidden_list = ", ".join(forbidden_rhythms)
        warning = f"\n\n[절대 준수] 다음 리듬은 절대 사용하지 마세요: {forbidden_list}"
    else:
        warning = "\n\n[권장] 아직 사용하지 않은 리듬을 우선 선택하세요."
    
    return f"""

⚠️ 이미 생성된 문제의 리듬 현황:
{status_text}{warning}
"""


def get_korean_rhythm_name(rhythm: str) -> str:
    """
    영문 리듬명을 한글명으로 변환합니다.
    
    Args:
        rhythm: 정규화된 리듬명 (예: "VF", "Asystole")
    
    Returns:
        한글 리듬명 (예: "심실세동", "무수축")
    """
    reverse_map = {v: k for k, v in RHYTHM_NORMALIZATION.items() if k == k}  # 한글 키만
    
    # 직접 매핑
    korean_names = {
        "VF": "심실세동",
        "Pulseless VT": "무맥성 심실빈맥",
        "Asystole": "무수축",
        "PEA": "무맥성 전기활동",
        "PSVT": "발작성 상심실성 빈맥",
        "AF": "심방세동",
        "SVT": "심실상성 빈맥",
        "AV Block": "방실차단",
        "Sinus Bradycardia": "동서맥",
        "STEMI": "급성 심근경색",
        "Pulmonary Embolism": "폐색전증",
        "ROSC": "자발순환 회복 후",
    }
    
    return korean_names.get(rhythm, rhythm)


def should_reject_rhythm(rhythm_counter: Dict[str, int], new_rhythm: str, max_count: int = 2) -> bool:
    """
    새로운 리듬이 허용 한도를 초과하는지 확인합니다.
    
    Args:
        rhythm_counter: 현재 리듬 카운터
        new_rhythm: 새로 생성된 리듬
        max_count: 최대 허용 횟수 (기본값: 2)
    
    Returns:
        True: 거부해야 함 (3회 이상)
        False: 허용 가능
    
    Examples:
        >>> should_reject_rhythm({"VF": 2}, "VF", max_count=2)
        True  # 이미 2회, 3회째는 거부
        >>> should_reject_rhythm({"VF": 1}, "VF", max_count=2)
        False  # 1회, 2회째는 허용
    """
    current_count = rhythm_counter.get(new_rhythm, 0)
    return current_count >= max_count

