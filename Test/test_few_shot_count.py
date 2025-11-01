"""
Few-Shot 개수 설정 테스트

Few-Shot 개수가 3개로 설정되었는지 확인하는 테스트
"""

import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config import get_mcq_generation_config

def test_few_shot_count():
    """Few-Shot 개수 설정 테스트"""
    
    print("=" * 70)
    print("🔢 Few-Shot 개수 설정 테스트")
    print("=" * 70)
    
    # 설정 로드
    config = get_mcq_generation_config()
    few_shot_max_examples = config["few_shot_max_examples"]
    
    print(f"\n📊 현재 Few-Shot 최대 개수: {few_shot_max_examples}")
    
    if few_shot_max_examples == 3:
        print("✅ Few-Shot 개수가 3개로 올바르게 설정되었습니다!")
    else:
        print(f"❌ Few-Shot 개수가 {few_shot_max_examples}개로 설정되어 있습니다. 3개가 아닙니다.")
    
    print("\n" + "=" * 70)
    print("🎉 Few-Shot 개수 설정 테스트 완료!")
    print("=" * 70)

if __name__ == "__main__":
    test_few_shot_count()
