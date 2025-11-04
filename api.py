"""
FastAPI 백엔드 - 프론트엔드 연동용 REST API

프론트엔드: UI_Dock_Test (React + TypeScript)
백엔드: Generator_Dock_Test (Python + LangChain + LangGraph)

사용법:
    uvicorn api:app --reload --port 8000
    
엔드포인트:
    GET  /                  : API 상태 확인
    GET  /api/health        : 헬스 체크
    POST /api/ask           : Ask Mode (RAG 기반 질문 응답)
    POST /api/forge         : Forge Mode (MCQ 생성)
    GET  /api/textbook      : 교재 구조 반환
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional, Dict, Any
from datetime import datetime
import traceback

# 프로젝트 모듈
from Core import AskMode, ForgeMode
from config import (
    validate_config, 
    get_textbook_structure,
    get_category_weights_by_topic,
    get_mcq_generation_config
)
from Utils import setup_logging

# ==================== FastAPI 앱 초기화 ====================

app = FastAPI(
    title="Generator Dock API",
    description="RAG 기반 MCQ 생성 및 질문 응답 API",
    version="1.0.0",
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS 설정 (프론트엔드 연결 허용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",      # Vite 기본 포트
        "http://localhost:5176",      # Vite 포트
        "http://localhost:5177",      # Vite 포트
        "http://localhost:5178",      # Vite 포트 (현재 사용 중)
        "http://localhost:3000",      # React 기본 포트
        "http://127.0.0.1:5173",
        "http://127.0.0.1:5176",
        "http://127.0.0.1:5177",
        "http://127.0.0.1:5178",
        "http://127.0.0.1:3000",
        "http://localhost:5174",      # Vite 대체 포트
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 전역 컴포넌트
ask_mode: Optional[AskMode] = None
forge_mode: Optional[ForgeMode] = None
logger = None

# ==================== 데이터 모델 (Pydantic) ====================

class Source(BaseModel):
    """참조 문서 정보 (프론트엔드 Source 타입과 일치)"""
    title: str
    snippet: str
    url: Optional[str] = None

class AskRequest(BaseModel):
    """Ask Mode 요청"""
    content: str  # 사용자 질문

class AskResponse(BaseModel):
    """Ask Mode 응답 (프론트엔드 Message 타입과 호환)"""
    id: str
    role: str  # "assistant"
    content: str
    timestamp: str  # ISO 8601 형식
    sources: List[Source] = []

class ForgeRequest(BaseModel):
    """Forge Mode 요청"""
    topic: str  # "총론", "각론", "전문심장소생술" 등
    count: int = 1  # 생성할 MCQ 개수 (기본 1개, 최대 50개)

class MCQ(BaseModel):
    """생성된 MCQ"""
    question: str
    options: List[str]
    answer_index: int
    explanation: List[str]
    doc_title: str
    selected_part: str
    selected_chapter: str
    timestamp: str

class ForgeResponse(BaseModel):
    """Forge Mode 응답"""
    mcqs: List[MCQ]
    count: int
    topic: str
    timestamp: str

class TextbookStructure(BaseModel):
    """교재 구조"""
    structure: Dict[str, List[str]]

class HealthResponse(BaseModel):
    """헬스 체크 응답"""
    status: str
    ask_mode: str
    forge_mode: str
    timestamp: str

# ==================== 초기화 ====================

@app.on_event("startup")
async def startup_event():
    """앱 시작 시 초기화"""
    global ask_mode, forge_mode, logger
    
    # 콘솔 출력 강제 (flush=True)
    print("\n" + "=" * 70, flush=True)
    print("⚙️  컴포넌트 초기화 중...", flush=True)
    print("=" * 70, flush=True)
    
    logger = setup_logging("API")
    logger.info("=" * 70)
    logger.info("🚀 FastAPI 서버 시작")
    logger.info("=" * 70)
    
    try:
        # 설정 검증
        print("🔍 설정 검증 중...", flush=True)
        logger.info("🔍 설정 검증 중...")
        if not validate_config():
            raise RuntimeError("환경 변수 설정 오류. .env 파일을 확인하세요.")
        print("✅ 설정 검증 완료", flush=True)
        logger.info("✅ 설정 검증 완료")
        
        # AskMode 초기화
        print("⚙️  AskMode 초기화 중...", flush=True)
        logger.info("⚙️  AskMode 초기화 중...")
        ask_mode = AskMode(logger=logger)
        print("✅ AskMode 초기화 완료", flush=True)
        logger.info("✅ AskMode 초기화 완료")
        
        # ForgeMode 초기화
        print("⚙️  ForgeMode 초기화 중...", flush=True)
        logger.info("⚙️  ForgeMode 초기화 중...")
        forge_mode = ForgeMode(
            vector_store=ask_mode.vector_store,
            llm=ask_mode.llm,
            logger=logger,
        )
        print("✅ ForgeMode 초기화 완료", flush=True)
        logger.info("✅ ForgeMode 초기화 완료")
        
        print("\n" + "=" * 70, flush=True)
        print("✅ API 서버 준비 완료!", flush=True)
        print("📍 API 문서: http://localhost:8000/docs", flush=True)
        print("📍 프론트엔드와 연결 대기 중...", flush=True)
        print("=" * 70 + "\n", flush=True)
        
        logger.info("=" * 70)
        logger.info("✅ API 서버 준비 완료!")
        logger.info("📍 API 문서: http://localhost:8000/docs")
        logger.info("=" * 70)
        
    except Exception as e:
        print(f"\n❌ 초기화 실패: {e}\n", flush=True)
        logger.error(f"❌ 초기화 실패: {e}", exc_info=True)
        raise

# ==================== API 엔드포인트 ====================

@app.get("/")
async def root():
    """API 상태 확인"""
    return {
        "status": "ok",
        "message": "Generator Dock API is running",
        "version": "1.0.0",
        "docs": "/docs",
        "endpoints": {
            "health": "/api/health",
            "ask": "/api/ask",
            "forge": "/api/forge",
            "textbook": "/api/textbook"
        }
    }

@app.get("/api/health", response_model=HealthResponse)
async def health_check():
    """헬스 체크"""
    return HealthResponse(
        status="healthy",
        ask_mode="initialized" if ask_mode else "not initialized",
        forge_mode="initialized" if forge_mode else "not initialized",
        timestamp=datetime.now().isoformat()
    )

@app.post("/api/ask", response_model=AskResponse)
async def ask_endpoint(request: AskRequest):
    """
    Ask Mode - RAG 기반 질문 응답
    
    프론트엔드의 Message 타입과 호환됩니다.
    
    Args:
        request.content: 사용자 질문
    
    Returns:
        AskResponse: AI 답변 및 참조 문서
    
    Example:
        POST /api/ask
        {
            "content": "심폐소생술 방법을 알려주세요"
        }
    """
    if not ask_mode:
        logger.error("[Ask] AskMode가 초기화되지 않았습니다")
        raise HTTPException(status_code=500, detail="AskMode가 초기화되지 않았습니다")
    
    try:
        print(f"\n💬 [Ask] 질문: {request.content[:80]}...", flush=True)
        logger.info(f"[Ask] 질문: {request.content[:100]}...")
        
        # AskMode 실행
        result = ask_mode.process(request.content)
        print(f"✅ [Ask] 답변 생성 완료\n", flush=True)
        
        # 응답 데이터 추출
        answer = result.get("answer", "")
        source_documents = result.get("source_documents", [])
        
        # Source 변환 (프론트엔드 타입과 일치)
        sources = []
        for doc in source_documents[:5]:  # 최대 5개만
            try:
                metadata = doc.get("metadata", {})
                page_content = doc.get("page_content", "")
                
                # 제목 추출 (우선순위: doc_title > title > source)
                title = (
                    metadata.get("doc_title") or 
                    metadata.get("title") or 
                    metadata.get("source") or 
                    "문서"
                )
                
                # Part/Chapter 정보 추가
                part = metadata.get("part", "")
                chapter = metadata.get("chapter", "")
                if part and chapter:
                    title = f"{title} - {part} - {chapter}"
                elif part:
                    title = f"{title} - {part}"
                
                # Snippet 생성 (200자 제한)
                snippet = page_content[:200]
                if len(page_content) > 200:
                    snippet += "..."
                
                sources.append(Source(
                    title=title,
                    snippet=snippet,
                    url=None  # 추후 문서 링크 추가 가능
                ))
            except Exception as e:
                logger.warning(f"Source 변환 실패: {e}")
                continue
        
        logger.info(f"[Ask] 응답 생성 완료 (답변 길이: {len(answer)}자, 참조 문서: {len(sources)}개)")
        
        return AskResponse(
            id=f"msg_{int(datetime.now().timestamp() * 1000)}",
            role="assistant",
            content=answer,
            timestamp=datetime.now().isoformat(),
            sources=sources
        )
        
    except Exception as e:
        logger.error(f"[Ask] 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500, 
            detail=f"질문 처리 중 오류가 발생했습니다: {str(e)}"
        )

@app.post("/api/forge", response_model=ForgeResponse)
async def forge_endpoint(request: ForgeRequest):
    """
    Forge Mode - MCQ 생성
    
    Args:
        request.topic: "총론", "법령", "각론", "전문심장소생술", "전문외상처치술", "내과응급", "특수응급"
        request.count: 생성할 문제 개수 (1-50)
    
    Returns:
        ForgeResponse: 생성된 MCQ 리스트
    
    Example:
        POST /api/forge
        {
            "topic": "전문심장소생술",
            "count": 5
        }
    """
    if not forge_mode:
        logger.error("[Forge] ForgeMode가 초기화되지 않았습니다")
        raise HTTPException(status_code=500, detail="ForgeMode가 초기화되지 않았습니다")
    
    # 개수 제한 (1-50)
    count = max(1, min(50, request.count))
    topic = request.topic.strip()
    
    try:
        print(f"\n🔨 [Forge] 요청 받음: {topic} {count}개", flush=True)
        logger.info(f"[Forge Batch] 주제: {topic}, 개수: {count}")
        
        # 교재 구조 가져오기
        textbook_structure = get_textbook_structure()
        
        # 범위별 필터링
        filtered_structure = create_filtered_structure(topic, textbook_structure)
        
        # 카테고리 가중치 가져오기
        category_weights = get_category_weights_by_topic(topic)
        logger.info(f"[Forge Batch] 카테고리 가중치: {category_weights}")
        
        # 특정 Chapter인지 확인
        is_specific_chapter = topic in ["전문심장소생술", "전문외상처치술", "내과응급", "특수응급"]
        
        # MCQ 생성 (배치 또는 개별)
        if is_specific_chapter and count > 1:
            # 특정 Chapter + 여러 개: 개별 생성 (user_topic 지정 필요)
            print(f"📋 [Forge] 특정 주제 모드: {topic} (다양성 추적)", flush=True)
            logger.info(f"[Forge Batch] 특정 주제 개별 생성 모드: {topic}")
            generated_mcqs = []
            
            # 리듬/다양성 추적을 위한 카운터
            rhythm_counter = {}
            question_type_counter = {}
            time_counter = {}
            logic_counter = {}
            
            for i in range(count):
                try:
                    print(f"   [{i+1}/{count}] 생성 중...", flush=True)
                    logger.info(f"[Forge Batch] MCQ {i+1}/{count} 생성 중...")
                    
                    mcq = forge_mode.generate_mcq(
                        topics_hierarchical=filtered_structure,
                        topics_nested=None,
                        user_topic=topic,
                        max_retries=6,
                        category_weights=category_weights,
                        rhythm_counter=rhythm_counter,
                        question_type_counter=question_type_counter,
                        time_counter=time_counter,
                        logic_counter=logic_counter
                    )
                    generated_mcqs.append(mcq)
                    print(f"   [{i+1}/{count}] ✓ 완료", flush=True)
                    logger.info(f"[Forge Batch] MCQ {i+1}/{count} 생성 완료")
                    
                except Exception as e:
                    print(f"   [{i+1}/{count}] ✗ 실패: {str(e)[:50]}", flush=True)
                    logger.error(f"[Forge Batch] MCQ {i+1}/{count} 생성 실패: {e}")
                    continue
        else:
            # 일반 주제 또는 단일 생성: 배치 메서드 활용 (더 효율적)
            print(f"📋 [Forge] 배치 생성 모드 (중복 방지, 풀 관리)", flush=True)
            logger.info(f"[Forge Batch] 배치 생성 모드 (중복 방지, 풀 관리)")
            generated_mcqs = forge_mode.generate_mcq_batch(
                topics_hierarchical=filtered_structure,
                count=count,
                max_retries=6
            )
            print(f"   ✓ 배치 생성 완료: {len(generated_mcqs)}개", flush=True)
        
        if not generated_mcqs:
            raise ValueError("MCQ 생성에 실패했습니다")
        
        # MCQ 변환 (프론트엔드 타입과 일치)
        mcqs = []
        for mcq in generated_mcqs:
            try:
                mcqs.append(MCQ(
                    question=mcq.get("question", ""),
                    options=mcq.get("options", []),
                    answer_index=mcq.get("answer_index", 0),
                    explanation=mcq.get("explanation", []),
                    doc_title=mcq.get("doc_title", ""),
                    selected_part=mcq.get("selected_part", ""),
                    selected_chapter=mcq.get("selected_chapter", ""),
                    timestamp=datetime.now().isoformat()
                ))
            except Exception as e:
                logger.warning(f"[Forge] MCQ 변환 실패: {e}")
                continue
        
        print(f"✅ [Forge] 완료: {len(mcqs)}개 생성 (요청: {count}개)\n", flush=True)
        logger.info(f"[Forge Batch] 완료: {len(mcqs)}개 생성 (요청: {count}개)")
        
        return ForgeResponse(
            mcqs=mcqs,
            count=len(mcqs),
            topic=topic,
            timestamp=datetime.now().isoformat()
        )
        
    except Exception as e:
        logger.error(f"[Forge Batch] 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"MCQ 배치 생성 중 오류가 발생했습니다: {str(e)}"
        )

@app.get("/api/textbook", response_model=TextbookStructure)
async def get_textbook_structure_endpoint():
    """
    교재 구조 반환
    
    Returns:
        TextbookStructure: 교재의 Part와 Chapter 구조
    
    Example:
        GET /api/textbook
        {
            "structure": {
                "총론": ["응급의료체계의개요", ...],
                "법령": ["구조구급에관한법률", ...],
                "각론": ["전문심장소생술", ...]
            }
        }
    """
    try:
        structure = get_textbook_structure()
        return TextbookStructure(structure=structure)
    except Exception as e:
        logger.error(f"[Textbook] 오류: {e}", exc_info=True)
        raise HTTPException(
            status_code=500,
            detail=f"교재 구조 조회 중 오류가 발생했습니다: {str(e)}"
        )

# ==================== 유틸리티 함수 ====================

def create_filtered_structure(topic: str, textbook_structure: Dict[str, List[str]]) -> Dict[str, List[str]]:
    """
    주제에 맞는 필터링된 교재 구조 반환
    
    Args:
        topic: 주제 이름 (예: "총론", "전문심장소생술")
        textbook_structure: 전체 교재 구조
    
    Returns:
        필터링된 교재 구조
    """
    # Part 선택 (총론, 법령, 각론)
    if topic in textbook_structure:
        return {topic: textbook_structure[topic]}
    
    # Chapter 선택 (전문심장소생술, 전문외상처치술, 내과응급, 특수응급)
    for part, chapters in textbook_structure.items():
        if topic in chapters:
            return {part: [topic]}
    
    # 전체 반환 (기본값)
    logger.warning(f"주제 '{topic}'을 찾을 수 없어 전체 구조를 반환합니다")
    return textbook_structure

# ==================== 에러 핸들러 ====================

@app.exception_handler(Exception)
async def global_exception_handler(request, exc):
    """전역 에러 핸들러"""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return {
        "error": "Internal Server Error",
        "detail": str(exc),
        "traceback": traceback.format_exc() if logger.level == 10 else None  # DEBUG 모드일 때만
    }

# ==================== 실행 ====================

if __name__ == "__main__":
    import uvicorn
    import sys
    
    # 출력 버퍼 비활성화 (즉시 출력)
    sys.stdout.reconfigure(line_buffering=True)
    
    print("\n" + "=" * 70, flush=True)
    print("🚀 Generator Dock API Server", flush=True)
    print("=" * 70, flush=True)
    print("", flush=True)
    print("📍 서버 시작 중...", flush=True)
    print("📍 포트: 8000", flush=True)
    print("📍 API 문서: http://localhost:8000/docs", flush=True)
    print("📍 헬스 체크: http://localhost:8000/api/health", flush=True)
    print("", flush=True)
    print("⏱️  초기화 중 (약 20-30초 소요)...", flush=True)
    print("   - Vertex AI 연결", flush=True)
    print("   - Vector Store 초기화", flush=True)
    print("   - LangGraph 워크플로우 빌드", flush=True)
    print("", flush=True)
    print("=" * 70, flush=True)
    print("", flush=True)
    
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=8000,
        reload=True,
        log_level="info",
        access_log=True
    )

