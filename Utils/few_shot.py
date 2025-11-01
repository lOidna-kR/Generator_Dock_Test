"""
Few-shot Learning 유틸리티

Few-shot 예시를 프롬프트에 통합하는 헬퍼 함수들을 제공합니다.
"""

import json
import random
from pathlib import Path
from typing import Dict, List, Any, Optional


def load_few_shot_examples_from_json(
    json_file_path: str = "few_shot_examples.json"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    JSON 파일에서 Few-shot 예시 로드 (하위 호환성)
    
    Args:
        json_file_path: JSON 파일 경로
    
    Returns:
        MCQ 유형별 Few-shot 예시 딕셔너리
    
    Raises:
        FileNotFoundError: JSON 파일이 없는 경우
        json.JSONDecodeError: JSON 파싱 실패 시
    """
    file_path = Path(json_file_path)
    
    if not file_path.exists():
        raise FileNotFoundError(f"Few-shot JSON 파일을 찾을 수 없습니다: {file_path}")
    
    with open(file_path, "r", encoding="utf-8") as f:
        examples = json.load(f)
    
    return examples


def load_few_shot_examples_from_folder(
    folder_path: str = "Data/Dock_Exam_2025"
) -> Dict[str, List[Dict[str, Any]]]:
    """
    폴더에서 모든 Few-shot JSON 파일 로드
    
    폴더 내 MCQ_*.json 파일들을 모두 로드하여 통합합니다.
    
    Args:
        folder_path: Few-shot JSON 파일들이 있는 폴더 경로
    
    Returns:
        MCQ 유형별 Few-shot 예시 통합 딕셔너리
        예: {
            "MCQ_GENERAL": [...],  # MCQ_GENERAL.json에서
            "MCQ_ADVANCED": [...], # MCQ_ADVANCED.json에서
        }
    
    Raises:
        FileNotFoundError: 폴더를 찾을 수 없는 경우
    
    예제:
        >>> # Data/Dock_Exam_2025/ 폴더에서 모든 MCQ_*.json 로드
        >>> examples = load_few_shot_examples_from_folder("Data/Dock_Exam_2025")
        >>> print(examples.keys())  # ['MCQ_GENERAL', 'MCQ_ADVANCED', ...]
    """
    folder = Path(folder_path)
    
    if not folder.exists():
        raise FileNotFoundError(f"폴더를 찾을 수 없습니다: {folder}")
    
    if not folder.is_dir():
        raise ValueError(f"파일이 아닌 폴더 경로를 지정해야 합니다: {folder}")
    
    all_examples = {}
    
    # 폴더 내 모든 JSON 파일 로드
    json_files = list(folder.glob("*.json"))
    
    if not json_files:
        raise FileNotFoundError(
            f"폴더에 JSON 파일이 없습니다: {folder}\n"
            f"예: MCQ_GENERAL.json, Dock_Test_2025.json 등"
        )
    
    for json_file in json_files:
        try:
            with open(json_file, "r", encoding="utf-8") as f:
                examples = json.load(f)
            
            # 파일명에서 유형 추출 (MCQ_GENERAL.json → MCQ_GENERAL, MCQ_SIMPLE.json → MCQ_SIMPLE)
            type_name = json_file.stem
            
            # 파일 내용이 리스트면 파일명을 키로 사용 (카테고리별 분리 유지)
            if isinstance(examples, list):
                # 리스트 형태 → 파일명을 키로 저장 (카테고리 독립성 유지)
                all_examples[type_name] = examples
                print(f"   ✓ {json_file.name}: {len(examples)}개 예시 → {type_name}")
            elif isinstance(examples, dict) and type_name in examples:
                all_examples[type_name] = examples[type_name]
                print(f"   ✓ {json_file.name}: {len(examples[type_name])}개 예시 로드됨")
            else:
                # 전체 딕셔너리 병합
                all_examples.update(examples)
                print(f"   ✓ {json_file.name}: 병합됨")
            
        except Exception as e:
            print(f"⚠️  {json_file.name} 로드 실패: {e}")
            continue
    
    return all_examples


def build_few_shot_prompt(
    template: str, 
    examples: List[Dict[str, Any]],
    max_examples: int = 3,
    randomize: bool = True,
    category_examples: Dict[str, List[Dict[str, Any]]] = None,
    category_weights: Dict[str, float] = None,
    recent_few_shot_indices: List[int] = None
) -> tuple[str, List[int]]:
    """
    Few-shot 예시를 프롬프트에 추가
    
    Args:
        template: 원본 프롬프트 템플릿
        examples: Few-shot 예시 리스트 (전체)
        max_examples: 최대 예시 개수 (기본값: 3)
        randomize: 예시를 랜덤으로 선택할지 여부 (기본값: True)
        category_examples: 카테고리별 예시 딕셔너리 (균등 선택용)
        category_weights: 카테고리별 가중치 (예: {"SIMPLE": 0.3, "MULTIPLE": 0.2, ...})
    
    Returns:
        tuple[str, List[int]]: (Few-shot 예시를 포함한 프롬프트, 선택된 예시의 인덱스 리스트)
    
    예제:
        >>> template = "다음 내용을 바탕으로 문제를 만드세요:\\n{context}"
        >>> examples = [
        ...     {
        ...         "question": "응급의료체계란?",
        ...         "options": ["A", "B", "C", "D"],
        ...         "answer_index": 1,
        ...         "explanation": "..."
        ...     }
        ... ]
        >>> prompt = build_few_shot_prompt(template, examples)
    """
    if not examples and not category_examples:
        return template, []
    
    # 최근 사용 인덱스 초기화
    if recent_few_shot_indices is None:
        recent_few_shot_indices = []
    
    # 카테고리 이름 매핑 (새로운 파일 구조에 맞게 수정)
    category_names = {
        "SIMPLE": "단순형",
        "MULTIPLE": "복수선택형",
        "CASE_BASED": "케이스형",
        "IMAGE_BASED": "이미지형",
        "ECG_BASED": "심전도형"
    }
    
    # 카테고리별 가중치 선택 모드
    if category_examples and len(category_examples) > 0:
        # 예시가 있는 카테고리만 선택
        available_categories = [(cat_key, cat_examples) 
                                for cat_key, cat_examples in category_examples.items() 
                                if cat_examples]
        
        if available_categories and max_examples > 0:
            selected_examples = []
            selected_indices = []
            
            # 가중치가 있으면 가중치 기반 선택 (1개 카테고리만 선택)
            if category_weights:
                cat_keys = [cat_key for cat_key, _ in available_categories]
                cat_dict = {cat_key: cat_examples for cat_key, cat_examples in available_categories}
                
                # 가용 카테고리의 가중치만 추출 (없으면 균등)
                weights = [category_weights.get(cat_key, 1.0 / len(cat_keys)) for cat_key in cat_keys]
                
                # 가중치 정규화 (합이 1.0이 되도록)
                weight_sum = sum(weights)
                if weight_sum > 0:
                    weights = [w / weight_sum for w in weights]
                
                # ✅ 1개 카테고리만 선택 (가중치 기반)
                selected_cat = random.choices(cat_keys, weights=weights, k=1)[0]
                selected_cat_examples = cat_dict[selected_cat]
                
                # 최근 사용 예시 제외 후 선택
                available_indices = [i for i in range(len(selected_cat_examples)) 
                                   if i not in recent_few_shot_indices]
                if len(available_indices) < max_examples:
                    # 후보 부족 시 전체에서 재선택
                    available_indices = list(range(len(selected_cat_examples)))
                
                # 선택된 카테고리에서 지정된 개수만큼 Few-Shot 선택
                chosen_indices = random.sample(available_indices, min(max_examples, len(available_indices)))
                for idx in chosen_indices:
                    selected_examples.append(selected_cat_examples[idx])
                    selected_indices.append(idx)
                
                # 선택된 카테고리 로깅
                cat_name = category_names.get(selected_cat, selected_cat)
                weight_pct = category_weights.get(selected_cat, 0) * 100
                print(f"         ✓ 선택된 카테고리: {cat_name} (가중치: {weight_pct:.1f}%) - {max_examples}개 예시")
            else:
                # 균등 선택 (가중치 미설정 시) - 1개 카테고리만 선택
                selected_cat_key, selected_cat_examples = random.choice(available_categories)
                
                # 최근 사용 예시 제외 후 선택
                available_indices = [i for i in range(len(selected_cat_examples)) 
                                   if i not in recent_few_shot_indices]
                if len(available_indices) < max_examples:
                    # 후보 부족 시 전체에서 재선택
                    available_indices = list(range(len(selected_cat_examples)))
                
                # 선택된 카테고리에서 지정된 개수만큼 Few-Shot 선택
                chosen_indices = random.sample(available_indices, min(max_examples, len(available_indices)))
                for idx in chosen_indices:
                    selected_examples.append(selected_cat_examples[idx])
                    selected_indices.append(idx)
                
                # 선택된 카테고리 로깅
                cat_name = category_names.get(selected_cat_key, selected_cat_key)
                print(f"         ✓ 선택된 카테고리: {cat_name} (균등 선택) - {max_examples}개 예시")
        else:
            # Fallback: 일반 선택
            num_examples = min(max_examples, len(examples))
            available_indices = [i for i in range(len(examples)) if i not in recent_few_shot_indices]
            if len(available_indices) < num_examples:
                available_indices = list(range(len(examples)))
            chosen_indices = random.sample(available_indices, min(num_examples, len(available_indices)))
            selected_examples = [examples[i] for i in chosen_indices]
            selected_indices = chosen_indices
    else:
        # 일반 선택 모드 (카테고리 구분 없이 전체에서 선택)
        num_examples = min(max_examples, len(examples))
        available_indices = [i for i in range(len(examples)) if i not in recent_few_shot_indices]
        if len(available_indices) < num_examples:
            available_indices = list(range(len(examples)))
        if randomize and len(examples) > num_examples:
            chosen_indices = random.sample(available_indices, min(num_examples, len(available_indices)))
            selected_examples = [examples[i] for i in chosen_indices]
            selected_indices = chosen_indices
        else:
            selected_examples = examples[:num_examples]
            selected_indices = list(range(num_examples))
    
    # 예시를 텍스트 형식으로 포맷팅
    examples_text = "\n\n**⚠️ 반드시 아래 예시와 동일한 형식으로 문제를 생성하세요:**\n\n"
    for i, example in enumerate(selected_examples, 1):
        examples_text += format_single_example(example, index=i)
    
    examples_text += (
        "\n**필수 준수 사항:**\n"
        "- 위 예시의 질문 구조를 정확히 따라하세요 (시작 방식, 문장 구조, 종결 표현)\n"
        "- 질문 형식이 '다음 중 ~'이면 동일하게, '㉠㉡㉢'이면 동일하게, '<보기>'이면 동일하게 작성하세요\n"
        "- 보기 구성 방식과 해설 스타일도 예시와 같게 하세요\n"
        "- ⚠️ 단, 내용은 반드시 제공된 교재에서 가져와야 합니다 (예시 내용 복사 금지)\n"
    )
    
    # 원본 템플릿에 예시 추가
    return template + "\n" + examples_text, selected_indices


def format_single_example(example: Dict[str, Any], index: int = 1) -> str:
    """
    단일 Few-shot 예시를 포맷팅
    
    Args:
        example: 예시 딕셔너리
        index: 예시 번호
    
    Returns:
        포맷팅된 예시 텍스트
    """
    text = f"예시 {index}:\n"
    text += f"질문: {example['question']}\n"
    text += f"보기:\n"
    
    for j, option in enumerate(example['options'], 1):
        text += f"  {j}. {option}\n"
    
    text += f"정답: {example['answer_index']}\n"
    
    # 해설 처리 (문자열/배열 형식 모두 지원)
    explanation = example.get('explanation', example.get('explanations'))
    
    if isinstance(explanation, list):
        # 배열 형식: 각 보기별 해설
        text += f"해설:\n"
        for j, expl in enumerate(explanation, 1):
            status = "✅ 정답" if j == example['answer_index'] else "❌ 오답"
            text += f"  {j}번 ({status}): {expl}\n"
    elif isinstance(explanation, str):
        # 문자열 형식: 전체 해설 (하위 호환성)
        text += f"해설: {explanation}\n"
    
    text += "\n"
    
    return text


def validate_few_shot_example(example: Dict[str, Any]) -> bool:
    """
    Few-shot 예시의 유효성 검증
    
    Args:
        example: 검증할 예시
    
    Returns:
        유효성 검증 결과 (True/False)
    """
    # 필수 필드 확인
    required_fields = ["question", "options", "answer_index"]
    for field in required_fields:
        if field not in example:
            return False
    
    # options 개수 확인
    if len(example["options"]) != 4:
        return False
    
    # answer_index 범위 확인
    if not (1 <= example["answer_index"] <= 4):
        return False
    
    return True


def filter_valid_examples(examples: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    유효한 Few-shot 예시만 필터링
    
    Args:
        examples: 예시 리스트
    
    Returns:
        유효한 예시만 포함된 리스트
    """
    return [ex for ex in examples if validate_few_shot_example(ex)]


# ==================== JSON 파일 생성 헬퍼 ====================


def create_few_shot_template(
    output_path: str = "few_shot_examples.json",
    num_examples: int = 3
) -> None:
    """
    Few-shot 예시 JSON 템플릿 파일 생성
    
    Args:
        output_path: 저장할 파일 경로
        num_examples: 생성할 예시 개수
    """
    template = {
        "MCQ_GENERAL": []
    }
    
    for i in range(num_examples):
        template["MCQ_GENERAL"].append({
            "question": f"예시 질문 {i+1}을 여기에 작성하세요",
            "options": [
                f"보기 1 - {i+1}",
                f"보기 2 - {i+1}",
                f"보기 3 - {i+1}",
                f"보기 4 - {i+1}"
            ],
            "answer_index": 1,
            "explanation": f"예시 {i+1}의 해설을 여기에 작성하세요"
        })
    
    with open(output_path, "w", encoding="utf-8") as f:
        json.dump(template, f, ensure_ascii=False, indent=2)
    
    print(f"✅ Few-shot 템플릿 파일 생성 완료: {output_path}")

