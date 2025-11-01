"""
Few-Shot 선택 방식 상세 테스트

실제로 선택된 카테고리와 Few-Shot 개수를 확인하는 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.few_shot import build_few_shot_prompt, load_few_shot_examples_from_folder
from config import get_mcq_generation_config
import random
import re
from collections import defaultdict

def test_few_shot_selection_detailed():
    """Few-Shot 선택 방식 상세 테스트"""
    
    print("=" * 70)
    print("🔍 Few-Shot 선택 방식 상세 테스트")
    print("=" * 70)
    
    # 1. Few-Shot 예시 로드
    print("\n1️⃣ Few-Shot 예시 로드 중...")
    try:
        config = get_mcq_generation_config()
        folder_path = config["few_shot_folder_path"]
        
        few_shot_dict = load_few_shot_examples_from_folder(folder_path)
        print(f"✅ Few-Shot 로드 완료: {len(few_shot_dict)}개 카테고리")
        
    except Exception as e:
        print(f"❌ Few-Shot 로드 실패: {e}")
        return
    
    # 2. 카테고리별 예시 준비
    file_mapping = {
        "SIMPLE": "Single_Type",
        "MULTIPLE": "Multiple_Type", 
        "CASE_BASED": "Case_Type",
        "IMAGE_BASED": "Image_Type",
        "ECG_BASED": "ECG_Type"
    }
    
    category_examples = {}
    for cat_key, file_name in file_mapping.items():
        if file_name in few_shot_dict:
            category_examples[cat_key] = few_shot_dict[file_name]
    
    # 3. 가중치 설정
    category_weights = {
        "SIMPLE": 0.25,      # 25%
        "MULTIPLE": 0.20,    # 20%
        "CASE_BASED": 0.25,  # 25%
        "IMAGE_BASED": 0.20, # 20%
        "ECG_BASED": 0.10,   # 10%
    }
    
    # 4. 가중치 기반 선택 빈도 테스트
    print("\n2️⃣ 가중치 기반 선택 빈도 테스트 (100회):")
    print("-" * 50)
    
    selection_counts = defaultdict(int)
    
    for i in range(100):
        # Few-Shot 선택 (1개만)
        template = "테스트"
        
        # 출력 캡처를 위해 임시로 print 함수 오버라이드
        import io
        import contextlib
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            prompt = build_few_shot_prompt(
                template=template,
                examples=[],
                max_examples=1,
                randomize=True,
                category_examples=category_examples,
                category_weights=category_weights
            )
        
        output = captured_output.getvalue()
        
        # 출력에서 선택된 카테고리 추출
        if "선택된 카테고리:" in output:
            match = re.search(r"선택된 카테고리: (\w+)", output)
            if match:
                selected_category = match.group(1)
                selection_counts[selected_category] += 1
    
    # 결과 출력
    print("선택 빈도 결과:")
    total_selections = sum(selection_counts.values())
    
    for cat_key in category_weights.keys():
        count = selection_counts.get(cat_key, 0)
        percentage = (count / total_selections * 100) if total_selections > 0 else 0
        expected_percentage = category_weights[cat_key] * 100
        
        print(f"   📊 {cat_key}: {count}/100회 ({percentage:.1f}%) - 예상: {expected_percentage:.1f}%")
    
    # 5. Few-Shot 개수 테스트
    print("\n3️⃣ Few-Shot 개수 테스트:")
    print("-" * 50)
    
    test_counts = [1, 3, 5]
    
    for test_count in test_counts:
        print(f"\n🔍 {test_count}개 Few-Shot 테스트:")
        
        # 5회 반복 테스트
        for i in range(5):
            captured_output = io.StringIO()
            with contextlib.redirect_stdout(captured_output):
                prompt = build_few_shot_prompt(
                    template="테스트",
                    examples=[],
                    max_examples=test_count,
                    randomize=True,
                    category_examples=category_examples,
                    category_weights=category_weights
                )
            
            output = captured_output.getvalue()
            
            # 선택된 카테고리와 개수 추출
            if "선택된 카테고리:" in output:
                match = re.search(r"선택된 카테고리: (\w+) .*? (\d+)개 예시", output)
                if match:
                    selected_category = match.group(1)
                    selected_count = int(match.group(2))
                    print(f"   테스트 {i+1}: {selected_category} 카테고리에서 {selected_count}개 선택")
                else:
                    print(f"   테스트 {i+1}: 패턴 매칭 실패")
            else:
                print(f"   테스트 {i+1}: 선택 정보 없음")
    
    print("\n" + "=" * 70)
    print("🎉 Few-Shot 선택 방식 상세 테스트 완료!")
    print("=" * 70)

def test_single_category_selection():
    """단일 카테고리 선택 테스트"""
    
    print("\n" + "=" * 70)
    print("🎯 단일 카테고리 선택 테스트")
    print("=" * 70)
    
    # Few-Shot 예시 로드
    config = get_mcq_generation_config()
    folder_path = config["few_shot_folder_path"]
    
    few_shot_dict = load_few_shot_examples_from_folder(folder_path)
    
    # 카테고리별 예시 준비
    file_mapping = {
        "SIMPLE": "Single_Type",
        "MULTIPLE": "Multiple_Type", 
        "CASE_BASED": "Case_Type",
        "IMAGE_BASED": "Image_Type",
        "ECG_BASED": "ECG_Type"
    }
    
    category_examples = {}
    for cat_key, file_name in file_mapping.items():
        if file_name in few_shot_dict:
            category_examples[cat_key] = few_shot_dict[file_name]
    
    # 각 카테고리별로 테스트
    for cat_key in category_examples.keys():
        print(f"\n📊 {cat_key} 카테고리 단일 선택 테스트:")
        
        # 해당 카테고리만 가중치 1.0으로 설정
        test_weights = {cat_key: 1.0}
        
        import io
        import contextlib
        
        captured_output = io.StringIO()
        with contextlib.redirect_stdout(captured_output):
            prompt = build_few_shot_prompt(
                template="테스트",
                examples=[],
                max_examples=3,
                randomize=True,
                category_examples=category_examples,
                category_weights=test_weights
            )
        
        output = captured_output.getvalue()
        
        # 결과 확인
        if "선택된 카테고리:" in output and cat_key in output:
            print(f"   ✅ {cat_key} 카테고리 정확히 선택됨")
        else:
            print(f"   ❌ {cat_key} 카테고리 선택 실패")

if __name__ == "__main__":
    # 상세 테스트 실행
    test_few_shot_selection_detailed()
    
    # 단일 카테고리 선택 테스트 실행
    test_single_category_selection()
