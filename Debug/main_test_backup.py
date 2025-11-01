"""
LangGraph Generator 실행 예제

Core.Generator를 사용한 간단한 실행 예제입니다.

사용법:
    python main.py
"""

import asyncio
import logging

from Core import Generator
from Utils import setup_logging


def test_basic_usage():
    """기본 사용법 테스트"""
    logger = setup_logging("main")
    
    try:
        logger.info("=" * 60)
        logger.info("LangGraph Generator 기본 사용 테스트")
        logger.info("=" * 60)
        
        # Generator 생성 (config.py 설정 사용)
        generator = Generator(
            vector_store=None,  # config.py 설정으로 자동 생성
            logger=logger,
        )
        
        # 시스템 정보 출력
        system_info = generator.get_system_info()
        logger.info(f"시스템 정보: {system_info}")
        
        # 테스트 질문
        test_questions = [
            "응급의료기관의 종류는 무엇인가요?",
            "119 구급대의 역할은 무엇인가요?",
        ]
        
        for question in test_questions:
            logger.info(f"\n{'='*60}")
            logger.info(f"질문: {question}")
            logger.info(f"{'='*60}")
            
            # 질문 처리
            result = generator.process(question, return_sources=True)
            
            # 결과 출력
            print(f"\n질문: {result['question']}")
            print(f"\n답변:\n{result['answer']}")
            print(f"\n출처 문서 수: {result['num_sources']}")
            
            if result.get('source_documents'):
                print("\n출처 문서:")
                for i, doc in enumerate(result['source_documents'], 1):
                    print(f"\n[{i}] {doc['content'][:100]}...")
                    print(f"    메타데이터: {doc['metadata']}")
        
        logger.info("\n✅ 기본 사용 테스트 완료")
        
    except Exception as e:
        logger.error(f"실행 중 오류 발생: {e}", exc_info=True)
        raise


async def test_streaming():
    """스트리밍 사용법 테스트"""
    logger = setup_logging("main_stream")
    
    try:
        logger.info("=" * 60)
        logger.info("LangGraph Generator 스트리밍 테스트")
        logger.info("=" * 60)
        
        # Generator 생성
        generator = Generator(vector_store=None, logger=logger)
        
        # 테스트 질문
        question = "응급의료기관의 종류는 무엇인가요?"
        
        print(f"\n질문: {question}\n")
        print("스트리밍 응답:")
        print("-" * 60)
        
        # 스트리밍 처리
        async for event in generator.process_stream(question):
            node = event.get("node")
            output = event.get("output", {})
            
            print(f"\n[노드: {node}]")
            
            if node == "retrieve_documents":
                num_sources = output.get("num_sources", 0)
                print(f"  → {num_sources}개 문서 검색 완료")
            
            elif node == "format_context":
                formatted = output.get("formatted_context", "")
                print(f"  → 컨텍스트 포맷팅 완료 ({len(formatted)}자)")
            
            elif node == "generate_answer":
                answer = output.get("answer", "")
                print(f"  → 답변 생성 완료:")
                print(f"     {answer[:200]}...")
            
            elif node == "format_output":
                sources = output.get("source_documents", [])
                print(f"  → 출력 포맷팅 완료 ({len(sources)}개 출처)")
        
        logger.info("\n✅ 스트리밍 테스트 완료")
        
    except Exception as e:
        logger.error(f"스트리밍 테스트 실패: {e}", exc_info=True)
        raise


if __name__ == "__main__":
    print("\n" + "=" * 60)
    print("LangGraph Generator 테스트")
    print("=" * 60 + "\n")
    
    # 1. 기본 사용법 테스트
    print("1️⃣  기본 사용법 테스트")
    print("-" * 60)
    test_basic_usage()
    
    # 2. 스트리밍 테스트 (선택사항)
    print("\n\n2️⃣  스트리밍 테스트 (선택)")
    print("-" * 60)
    response = input("\n스트리밍 테스트를 실행하시겠습니까? (y/n): ")
    
    if response.lower() == 'y':
        asyncio.run(test_streaming())
    else:
        print("스트리밍 테스트를 건너뜁니다.")
    
    print("\n" + "=" * 60)
    print("✅ 모든 테스트 완료!")
    print("=" * 60 + "\n")
