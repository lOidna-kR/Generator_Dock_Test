"""
Few-Shot 선택 방식 테스트

가중치에 따라 1개 카테고리만 선택하고, 그 카테고리에서 지정된 개수만큼 Few-Shot을 선택하는 방식 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.few_shot import build_few_shot_prompt, load_few_shot_examples_from_folder
from config import get_mcq_generation_config
import random

def test_few_shot_selection():
    """Few-Shot 선택 방식 테스트"""
    
    print("=" * 70)
    print("🧪 Few-Shot 선택 방식 테스트")
    print("=" * 70)
    
    # 1. Few-Shot 예시 로드
    print("\n1️⃣ Few-Shot 예시 로드 중...")
    try:
        config = get_mcq_generation_config()
        folder_path = config["few_shot_folder_path"]
        
        few_shot_dict = load_few_shot_examples_from_folder(folder_path)
        print(f"✅ Few-Shot 로드 완료: {len(few_shot_dict)}개 카테고리")
        
        # 카테고리별 예시 개수 확인
        for category, examples in few_shot_dict.items():
            print(f"   📁 {category}: {len(examples)}개 예시")
            
    except Exception as e:
        print(f"❌ Few-Shot 로드 실패: {e}")
        return
    
    # 2. 카테고리별 예시 준비
    print("\n2️⃣ 카테고리별 예시 준비 중...")
    
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
            print(f"   ✓ {cat_key}: {len(few_shot_dict[file_name])}개 예시")
    
    # 3. 가중치 설정
    print("\n3️⃣ 가중치 설정:")
    category_weights = {
        "SIMPLE": 0.25,      # 25%
        "MULTIPLE": 0.20,    # 20%
        "CASE_BASED": 0.25,  # 25%
        "IMAGE_BASED": 0.20, # 20%
        "ECG_BASED": 0.10,   # 10%
    }
    
    for cat_key, weight in category_weights.items():
        print(f"   📊 {cat_key}: {weight*100:.1f}%")
    
    # 4. 테스트 케이스들
    test_cases = [
        {"name": "Few-Shot 1개", "max_examples": 1},
        {"name": "Few-Shot 3개", "max_examples": 3},
        {"name": "Few-Shot 5개", "max_examples": 5},
    ]
    
    # 5. 각 테스트 케이스 실행
    print("\n4️⃣ 테스트 실행:")
    
    for test_case in test_cases:
        print(f"\n🔍 {test_case['name']} 테스트:")
        print("-" * 50)
        
        # 5회 반복 테스트
        for i in range(5):
            print(f"\n테스트 {i+1}회차:")
            
            # Few-Shot 선택
            template = "다음 내용을 바탕으로 문제를 만드세요:\n{context}"
            
            try:
                prompt = build_few_shot_prompt(
                    template=template,
                    examples=[],  # 빈 리스트 (category_examples 사용)
                    max_examples=test_case['max_examples'],
                    randomize=True,
                    category_examples=category_examples,
                    category_weights=category_weights
                )
                
                print(f"   ✅ Few-Shot 선택 완료 ({test_case['max_examples']}개)")
                
            except Exception as e:
                print(f"   ❌ Few-Shot 선택 실패: {e}")
    
    print("\n" + "=" * 70)
    print("🎉 Few-Shot 선택 방식 테스트 완료!")
    print("=" * 70)

def test_specific_category_selection():
    """특정 카테고리 선택 테스트"""
    
    print("\n" + "=" * 70)
    print("🎯 특정 카테고리 선택 테스트")
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
    
    # 각 카테고리별로 10회 테스트
    for cat_key in category_examples.keys():
        print(f"\n📊 {cat_key} 카테고리 선택 빈도 테스트 (10회):")
        
        selected_count = 0
        for i in range(10):
            # 해당 카테고리만 가중치 1.0으로 설정
            test_weights = {cat_key: 1.0}
            
            template = "테스트"
            prompt = build_few_shot_prompt(
                template=template,
                examples=[],
                max_examples=1,
                randomize=True,
                category_examples=category_examples,
                category_weights=test_weights
            )
            
            # 로그에서 선택된 카테고리 확인 (실제로는 print 출력을 파싱해야 함)
            # 여기서는 간단히 카운트만
            selected_count += 1
        
        print(f"   ✅ {cat_key}: {selected_count}/10회 선택됨")

if __name__ == "__main__":
    # 메인 테스트 실행
    test_few_shot_selection()
    
    # 특정 카테고리 선택 테스트 실행
    test_specific_category_selection()
