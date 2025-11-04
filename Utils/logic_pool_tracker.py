"""
논리 풀 추적 시스템
===================

MCQ 생성 시 5H5T 원인의 다양성을 보장하기 위한 동적 추적 시스템

주요 기능:
1. 5H5T 원인 풀 관리
2. 사용된 논리 추적
3. 아직 사용하지 않은 논리를 프롬프트에 동적 제공
4. 논리 패턴 추출 및 검증

사용 예시:
    from Utils.logic_pool_tracker import (
        extract_logic_from_mcq,
        get_available_logic_prompt,
        LOGIC_POOL_5H5T
    )
    
    # 사용된 논리 추적
    used_logics = set()
    logic = extract_logic_from_mcq(mcq)
    if logic:
        used_logics.add(logic)
    
    # 프롬프트 생성
    prompt = get_available_logic_prompt(used_logics)
"""

from typing import Optional, Set, Dict, List
import re

# 5H5T 논리 풀 정의
LOGIC_POOL_5H5T = {
    "5H": {
        "저산소증": ["저산소", "hypoxia", "질식", "익수"],
        "저혈량": ["저혈량", "hypovolemia", "출혈", "실혈", "탈수"],
        "수소이온과다": ["산증", "acidosis", "hydrogen", "산독증"],
        "저체온": ["저체온", "hypothermia", "체온"],
        "고칼륨혈증": ["고칼륨", "hyperkalemia", "칼륨"],
        "저칼륨혈증": ["저칼륨", "hypokalemia"],
    },
    "5T": {
        "심낭압전": ["심낭압전", "tamponade", "심낭천자", "심낭삼출"],
        "긴장성기흉": ["긴장성기흉", "tension pneumothorax", "기흉", "흉부감압"],
        "폐색전증": ["폐색전", "pulmonary embolism", "혈전용해", "PE"],
        "관상동맥혈전": ["관상동맥", "coronary", "심근경색", "STEMI", "MI"],
        "독소": ["독소", "toxin", "중독", "약물"],
    }
}

# 한글 이름 매핑
LOGIC_KOREAN_NAMES = {
    "저산소증": "저산소증 (Hypoxia)",
    "저혈량": "저혈량 (Hypovolemia)",
    "수소이온과다": "산증 (Hydrogen ion/Acidosis)",
    "저체온": "저체온 (Hypothermia)",
    "고칼륨혈증": "고칼륨혈증 (Hyperkalemia)",
    "저칼륨혈증": "저칼륨혈증 (Hypokalemia)",
    "심낭압전": "심낭압전 (Tamponade)",
    "긴장성기흉": "긴장성기흉 (Tension pneumothorax)",
    "폐색전증": "폐색전증 (Pulmonary thrombosis)",
    "관상동맥혈전": "관상동맥혈전 (Coronary thrombosis)",
    "독소": "독소/약물 중독 (Toxins)",
    "일반": "일반 (특별한 원인 없음)",
}


def extract_logic_from_mcq(mcq: dict) -> Optional[str]:
    """
    MCQ에서 핵심 논리(5H5T 원인) 추출
    
    Args:
        mcq: MCQ 딕셔너리 (question, explanation 포함)
    
    Returns:
        str: 추출된 논리 키워드 (예: "폐색전증", "저혈량") 또는 None
    """
    # 해설과 질문 텍스트 결합
    explanation = mcq.get("explanation", "")
    question = mcq.get("question", "")
    
    # explanation이 리스트인 경우 처리
    if isinstance(explanation, list):
        explanation = " ".join(explanation)
    
    combined_text = f"{question} {explanation}"
    
    # 5H와 5T를 순회하며 키워드 매칭
    for category, logics in LOGIC_POOL_5H5T.items():
        for logic_name, keywords in logics.items():
            for keyword in keywords:
                if keyword in combined_text:
                    return logic_name
    
    # 특별한 원인을 찾지 못한 경우
    return "일반"


def get_all_logics() -> List[str]:
    """
    모든 5H5T 논리 목록 반환
    
    Returns:
        List[str]: 논리 이름 리스트
    """
    all_logics = []
    for category in LOGIC_POOL_5H5T.values():
        all_logics.extend(category.keys())
    return all_logics


def get_available_logic_prompt(used_logics: Set[str], max_show: int = 5) -> str:
    """
    아직 사용하지 않은 논리를 프롬프트에 추가할 텍스트 생성
    
    Args:
        used_logics: 이미 사용된 논리들의 집합
        max_show: 표시할 최대 논리 수
    
    Returns:
        str: 프롬프트에 추가할 텍스트
    """
    if not used_logics:
        # 처음 생성하는 경우
        prompt = "\n\n💡 **5H5T 원인 선택 가이드:**\n"
        prompt += "이번 문제는 5H5T 중 **아무거나** 자유롭게 선택하세요!\n"
        prompt += "✅ 선택 가능한 원인:\n"
        
        all_logics = get_all_logics()
        for i, logic in enumerate(all_logics[:max_show], 1):
            korean_name = LOGIC_KOREAN_NAMES.get(logic, logic)
            prompt += f"   {i}. {korean_name}\n"
        
        if len(all_logics) > max_show:
            prompt += f"   ... 외 {len(all_logics) - max_show}개\n"
        
        return prompt
    
    # 사용 가능한 논리와 이미 사용된 논리 분류
    all_logics = get_all_logics()
    available_logics = [logic for logic in all_logics if logic not in used_logics]
    used_logic_list = [logic for logic in all_logics if logic in used_logics]
    
    # 프롬프트 생성
    prompt = "\n\n🎨 **창의적 논리 선택 가이드 (5H5T 기반):**\n"
    
    # 아직 사용하지 않은 원인 (우선 추천)
    if available_logics:
        prompt += "✅ **아직 사용하지 않은 원인 (우선 선택!):**\n"
        for i, logic in enumerate(available_logics[:max_show], 1):
            korean_name = LOGIC_KOREAN_NAMES.get(logic, logic)
            prompt += f"   {i}. {korean_name}\n"
        
        if len(available_logics) > max_show:
            prompt += f"   ... 외 {len(available_logics) - max_show}개\n"
    
    # 이미 사용한 원인 (회피 권장)
    if used_logic_list:
        prompt += "\n⚠️ **이미 사용한 원인 (가급적 회피):**\n"
        for i, logic in enumerate(used_logic_list[:3], 1):
            korean_name = LOGIC_KOREAN_NAMES.get(logic, logic)
            prompt += f"   {i}. {korean_name}\n"
    
    # 지시사항
    prompt += "\n🎯 **중요:** 위의 ✅ 목록에서 선택하여 **완전히 새로운 시나리오**를 만드세요!\n"
    prompt += "💡 같은 원인이라도 환자 배경, 발견 상황, 병력 등을 다르게 설정하면 독창적인 문제가 됩니다.\n"
    
    return prompt


def get_logic_statistics(used_logics: Set[str]) -> Dict[str, int]:
    """
    논리 사용 통계 반환
    
    Args:
        used_logics: 사용된 논리들의 집합
    
    Returns:
        Dict[str, int]: {"5H": 사용된 5H 개수, "5T": 사용된 5T 개수, "total": 전체}
    """
    stats = {"5H": 0, "5T": 0, "일반": 0, "total": len(used_logics)}
    
    for logic in used_logics:
        if logic == "일반":
            stats["일반"] += 1
            continue
        
        for category, logics in LOGIC_POOL_5H5T.items():
            if logic in logics:
                stats[category] += 1
                break
    
    return stats


def print_logic_distribution(used_logics: Set[str]) -> None:
    """
    논리 분포를 콘솔에 출력
    
    Args:
        used_logics: 사용된 논리들의 집합
    """
    print("\n" + "="*50)
    print("📊 논리 원인 분포 (5H5T):")
    print("="*50)
    
    stats = get_logic_statistics(used_logics)
    
    # 카테고리별 통계
    print(f"\n카테고리별:")
    print(f"  5H (저산소, 저혈량, 산증, 저체온, 전해질): {stats['5H']}개")
    print(f"  5T (심낭압전, 기흉, 폐색전, 관상동맥, 독소): {stats['5T']}개")
    if stats['일반'] > 0:
        print(f"  일반 (특별한 원인 없음): {stats['일반']}개")
    print(f"  합계: {stats['total']}개")
    
    # 개별 논리 목록
    if used_logics:
        print(f"\n사용된 원인 목록:")
        for i, logic in enumerate(sorted(used_logics), 1):
            korean_name = LOGIC_KOREAN_NAMES.get(logic, logic)
            print(f"  {i}. {korean_name}")
    
    print("="*50)


# 리듬과 논리의 조합 추적
def get_rhythm_logic_combination(rhythm: str, logic: str) -> str:
    """
    리듬과 논리를 조합한 키 생성
    
    Args:
        rhythm: 심전도 리듬 (예: "VF", "PEA")
        logic: 논리 원인 (예: "폐색전증")
    
    Returns:
        str: 조합 키 (예: "VF+저체온", "PEA+폐색전증")
    """
    return f"{rhythm}+{logic}"


def should_reject_rhythm_logic_combo(
    combo_counter: Dict[str, int],
    rhythm: str,
    logic: str,
    max_count: int = 1
) -> bool:
    """
    특정 (리듬, 논리) 조합이 이미 max_count회 사용되었는지 확인
    
    Args:
        combo_counter: {조합: 사용횟수} 딕셔너리
        rhythm: 심전도 리듬
        logic: 논리 원인
        max_count: 최대 허용 횟수
    
    Returns:
        bool: True면 거부해야 함
    """
    combo_key = get_rhythm_logic_combination(rhythm, logic)
    current_count = combo_counter.get(combo_key, 0)
    return current_count >= max_count

