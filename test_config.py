"""설정 확인 스크립트"""
from config import get_retriever_config, get_mcq_generation_config

r = get_retriever_config()
m = get_mcq_generation_config()

print("=" * 60)
print("현재 설정 확인")
print("=" * 60)
print(f"✓ initial_k (초기 검색): {r['initial_k']}")
print(f"✓ k (리랭킹 후): {r['k']}")
print(f"✓ max_context_docs (LLM 전달): {m['max_context_docs']}")
print(f"✓ Temperature: {r['llm_temperature']}")
print(f"✓ Few-shot 예시 개수: {m['few_shot_max_examples']}")
print("=" * 60)

# 검증
expected = {
    'initial_k': 20,
    'k': 7,
    'max_context_docs': 7,
    'temperature': 0.85,
}

actual = {
    'initial_k': r['initial_k'],
    'k': r['k'],
    'max_context_docs': m['max_context_docs'],
    'temperature': r['llm_temperature'],
}

all_ok = True
print("\n검증 결과:")
for key in expected:
    exp = expected[key]
    act = actual[key]
    if act == exp:
        print(f"  ✅ {key}: {act} (OK)")
    else:
        print(f"  ⚠️  {key}: {act} (기대값: {exp})")
        all_ok = False

if all_ok:
    print("\n🎉 모든 설정이 최적화되었습니다!")
else:
    print("\n⚠️  일부 설정이 기대값과 다릅니다. .env 파일을 확인하세요.")

