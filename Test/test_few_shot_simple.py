"""
Few-Shot 선택 방식 간단 테스트

직접적으로 선택된 카테고리와 개수를 확인하는 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from Utils.few_shot import load_few_shot_examples_from_folder
from config import get_mcq_generation_config
import random
from collections import defaultdict

def test_category_selection():
    """카테고리 선택 테스트"""
    
    print("=" * 70)
    print("🎯 Few-Shot 카테고리 선택 테스트")
    print("=" * 70)
    
    # 1. Few-Shot 예시 로드
    config = get_mcq_generation_config()
    folder_path = config["few_shot_folder_path"]
    
    few_shot_dict = load_few_shot_examples_from_folder(folder_path)
    
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
    
    print(f"\n📊 카테고리별 예시 개수:")
    for cat_key, examples in category_examples.items():
        weight_pct = category_weights.get(cat_key, 0) * 100
        print(f"   {cat_key}: {len(examples)}개 예시 (가중치: {weight_pct:.1f}%)")
    
    # 4. 가중치 기반 선택 테스트
    print(f"\n🎲 가중치 기반 선택 테스트 (100회):")
    print("-" * 50)
    
    selection_counts = defaultdict(int)
    
    # 가용 카테고리와 가중치 준비
    available_categories = [(cat_key, cat_examples) 
                           for cat_key, cat_examples in category_examples.items() 
                           if cat_examples]
    
    cat_keys = [cat_key for cat_key, _ in available_categories]
    weights = [category_weights.get(cat_key, 1.0 / len(cat_keys)) for cat_key in cat_keys]
    
    # 가중치 정규화
    weight_sum = sum(weights)
    if weight_sum > 0:
        weights = [w / weight_sum for w in weights]
    
    # 100회 선택 테스트
    for i in range(100):
        # 가중치 기반 카테고리 선택
        selected_cat = random.choices(cat_keys, weights=weights, k=1)[0]
        selection_counts[selected_cat] += 1
    
    # 결과 출력
    total_selections = sum(selection_counts.values())
    print("선택 빈도 결과:")
    
    for cat_key in category_weights.keys():
        count = selection_counts.get(cat_key, 0)
        percentage = (count / total_selections * 100) if total_selections > 0 else 0
        expected_percentage = category_weights[cat_key] * 100
        
        print(f"   📊 {cat_key}: {count}/100회 ({percentage:.1f}%) - 예상: {expected_percentage:.1f}%")
    
    # 5. Few-Shot 개수 테스트
    print(f"\n🔢 Few-Shot 개수 테스트:")
    print("-" * 50)
    
    test_counts = [1, 3, 5]
    
    for test_count in test_counts:
        print(f"\n🔍 {test_count}개 Few-Shot 테스트:")
        
        # 5회 반복 테스트
        for i in range(5):
            # 카테고리 선택
            selected_cat = random.choices(cat_keys, weights=weights, k=1)[0]
            selected_cat_examples = category_examples[selected_cat]
            
            # 선택된 카테고리에서 Few-Shot 선택
            selected_examples = []
            for _ in range(test_count):
                example = random.choice(selected_cat_examples)
                selected_examples.append(example)
            
            print(f"   테스트 {i+1}: {selected_cat} 카테고리에서 {len(selected_examples)}개 선택")
    
    print("\n" + "=" * 70)
    print("🎉 Few-Shot 카테고리 선택 테스트 완료!")
    print("=" * 70)

def test_single_category():
    """단일 카테고리 테스트"""
    
    print("\n" + "=" * 70)
    print("🎯 단일 카테고리 테스트")
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
        print(f"\n📊 {cat_key} 카테고리 테스트:")
        
        examples = category_examples[cat_key]
        
        # 3개 Few-Shot 선택
        selected_examples = []
        for _ in range(3):
            example = random.choice(examples)
            selected_examples.append(example)
        
        print(f"   ✅ {cat_key} 카테고리에서 {len(selected_examples)}개 선택")
        print(f"   📝 첫 번째 예시 질문: {selected_examples[0]['question'][:50]}...")

if __name__ == "__main__":
    # 카테고리 선택 테스트 실행
    test_category_selection()
    
    # 단일 카테고리 테스트 실행
    test_single_category()
