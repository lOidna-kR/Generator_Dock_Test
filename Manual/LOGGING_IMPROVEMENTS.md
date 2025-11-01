# 로깅 시스템 개선 가이드

## 📋 개요

프로젝트 전체의 로깅 시스템이 개선되어 더욱 일관성 있고 체계적인 로그 관리가 가능해졌습니다.

**개선 일자**: 2025-01-23  
**버전**: 2.0.0

---

## 🎯 주요 개선 사항

### 1. ✅ RAG 노드에 에러 핸들러 적용

모든 RAG 노드가 표준화된 에러 처리를 사용하도록 개선되었습니다.

**적용된 노드:**
- `Node/RAG/answer.py` - 답변 생성
- `Node/RAG/context.py` - 컨텍스트 포맷팅
- `Node/RAG/output.py` - 출력 포맷팅

**Before:**
```python
try:
    result = do_something()
    logger.info("✅ 성공")
    return {"result": result}
except Exception as e:
    logger.error(f"❌ 실패: {e}")
    return {"error": str(e)}
```

**After:**
```python
from Utils import create_error_handler

error_handler = create_error_handler(logger)

try:
    result = do_something()
    return error_handler.handle_success(
        node_name="my_node",
        message="작업 완료",
        return_fields={"result": result}
    )
except Exception as e:
    return error_handler.handle_error(
        error=e,
        state=state,
        node_name="my_node",
        recoverable=True
    )
```

---

### 2. ✅ 진행 상황 출력을 Logger로 변경

`Core/MCQ_Generator.py`의 `print()` 문이 모두 `logger`로 변경되었습니다.

**개선 효과:**
- 진행 상황이 로그 파일에 기록됨
- 로그 레벨로 제어 가능
- 타임스탬프 자동 추가
- 일관된 로그 포맷

**Before:**
```python
print("━" * 70)
print(f"MCQ 생성 진행 중... ({len(mcqs)}/{count})")
print(f"✓ [{idx}] {category} | {part} - {chapter}")
```

**After:**
```python
self.logger.info("━" * 70)
self.logger.info(f"MCQ 생성 진행 중... ({len(mcqs)}/{count})")
self.logger.info(f"✓ [{idx}] {category} | {part} - {chapter}")
self.logger.debug(f"   질문: {question[:80]}...")  # DEBUG 레벨 추가
```

---

### 3. ✅ 디버그 로깅 추가

모든 주요 노드에 `logger.debug()` 로깅이 추가되었습니다.

**추가된 디버그 로그:**

#### RAG 노드
```python
# Node/RAG/answer.py
logger.debug(f"질문: {question[:100]}...")
logger.debug(f"컨텍스트 길이: {len(context)}자")

# Node/RAG/context.py
logger.debug(f"포맷팅할 문서 수: {len(documents)}개")

# Node/RAG/output.py
logger.debug(f"출처 문서 {len(source_documents)}개 포맷팅 완료")
```

#### MCQ 노드
```python
# Core/MCQ_Generator.py
self.logger.debug(f"   질문: {question[:80]}...")
```

**사용법:**
```bash
# .env 파일에서 DEBUG 레벨 활성화
LOG_LEVEL=DEBUG
```

---

### 4. ✅ 파일 로깅 기본 활성화

파일 로깅이 기본적으로 활성화되도록 변경되었습니다.

**변경 내용:**

#### config.py
```python
# Before
"file_logging": os.getenv("LOG_FILE", "false").lower() == "true"

# After
"file_logging": os.getenv("LOG_FILE", "true").lower() == "true"
```

#### env.example.txt
```bash
# Before
LOG_FILE=false

# After
LOG_FILE=true  # 기본값 활성화

# 로그 파일은 Logs/ 폴더에 저장됩니다
# 예: Logs/generator_20250123.log
```

---

### 5. ✅ 로그 파일 저장 위치 변경

로그 파일이 `Logs/` 폴더에 저장되도록 변경되었습니다.

**변경 내용:**

#### config.py
```python
def get_paths() -> Dict[str, Path]:
    project_root = Path(__file__).parent
    return {
        "project_root": project_root,
        "logs": project_root / "Logs",  # 대문자 Logs
    }
```

#### .gitignore
```gitignore
# ==================== 로그 ====================
*.log
logs/
Logs/  # 추가
*.log.*
```

**로그 파일 예시:**
```
Logs/
  └─ generator_20250123.log
```

---

## 📊 로그 레벨 사용 가이드

### DEBUG (개발 환경)
```python
logger.debug(f"변수 값: {value}")
logger.debug(f"검색 쿼리: {query}")
logger.debug(f"State: {state}")
```

**용도:**
- 변수 값 확인
- 함수 호출 추적
- 상태 디버깅

### INFO (프로덕션 권장)
```python
logger.info("✅ 문서 검색 완료")
logger.info(f"MCQ 생성 진행 중... (5/10)")
logger.info("━" * 70)
```

**용도:**
- 정상 동작 확인
- 진행 상황 표시
- 중요 이벤트 기록

### WARNING
```python
logger.warning("⚠️ 검색 결과 없음")
logger.warning(f"재시도 {retry_count}/{max_retries}")
```

**용도:**
- 경고성 메시지
- 복구 가능한 문제
- 재시도 정보

### ERROR
```python
logger.error("❌ 문서 검색 실패", exc_info=True)
logger.error(f"MCQ 생성 실패: {e}")
```

**용도:**
- 에러 발생
- 예외 정보
- 스택 트레이스

### CRITICAL
```python
logger.critical("💥 데이터베이스 연결 실패")
logger.critical(f"치명적 오류: {e}")
```

**용도:**
- 시스템 종료 수준
- 치명적 오류
- 복구 불가능

---

## 🚀 사용 방법

### 1. 환경 변수 설정

`.env` 파일 생성:
```bash
# 개발 환경
LOG_LEVEL=DEBUG
LOG_CONSOLE=true
LOG_FILE=true

# 프로덕션 환경
LOG_LEVEL=INFO
LOG_CONSOLE=false
LOG_FILE=true
```

### 2. 로그 확인

#### 콘솔 로그 (컬러)
```bash
python MCQ_main.py
```

출력 예시:
```
[32mINFO[0m - 2025-01-23 14:30:00 - Core.Generator - ✅ Generator 초기화 완료
[32mINFO[0m - 2025-01-23 14:30:01 - Core.Generator - 문서 검색 시작
[33mWARNING[0m - 2025-01-23 14:30:02 - Node.retrieve - ⚠️ 검색 결과 없음
```

#### 파일 로그
```bash
# 로그 파일 확인
cat Logs/generator_20250123.log

# 실시간 모니터링
tail -f Logs/generator_20250123.log
```

### 3. 로그 레벨 변경

```bash
# DEBUG 레벨 활성화 (상세 로그)
export LOG_LEVEL=DEBUG
python MCQ_main.py

# INFO 레벨 (일반)
export LOG_LEVEL=INFO
python MCQ_main.py

# ERROR만 표시
export LOG_LEVEL=ERROR
python MCQ_main.py
```

---

## 📈 로그 분석

### 로그 필터링

```bash
# 에러만 추출
grep "ERROR" Logs/generator_20250123.log

# 특정 노드 로그만
grep "retrieve_documents" Logs/generator_20250123.log

# 재시도 로그만
grep "재시도" Logs/generator_20250123.log
```

### 로그 통계

```bash
# 에러 개수
grep -c "ERROR" Logs/generator_20250123.log

# 경고 개수
grep -c "WARNING" Logs/generator_20250123.log

# 성공 개수
grep -c "✅" Logs/generator_20250123.log
```

---

## 🔧 문제 해결

### Q: 로그 파일이 생성되지 않아요

**A: 다음을 확인하세요:**
1. `.env` 파일에 `LOG_FILE=true` 설정
2. `Logs/` 폴더 쓰기 권한 확인
3. `config.py`의 `get_paths()` 확인

```python
# config.py
paths = get_paths()
print(f"로그 경로: {paths['logs']}")  # Logs/ 확인
```

### Q: 콘솔에 로그가 너무 많이 나와요

**A: 로그 레벨을 높이세요:**
```bash
# .env
LOG_LEVEL=WARNING  # WARNING 이상만 표시
LOG_CONSOLE=false  # 콘솔 로깅 비활성화
```

### Q: 디버그 로그가 안 보여요

**A: DEBUG 레벨을 활성화하세요:**
```bash
# .env
LOG_LEVEL=DEBUG
```

### Q: 로그 파일이 너무 커져요

**A: 로그 로테이션을 설정하세요 (향후 개선 예정):**
```python
# Utils/logging.py에 추가 (향후)
from logging.handlers import RotatingFileHandler

handler = RotatingFileHandler(
    log_file,
    maxBytes=10*1024*1024,  # 10MB
    backupCount=5
)
```

---

## 📝 변경 이력

### 2025-01-23 (v2.0.0)
- ✨ RAG 노드에 에러 핸들러 적용
- ✨ MCQ_Generator의 print()를 logger로 변경
- ✨ 디버그 로깅 추가
- ✨ 파일 로깅 기본 활성화
- ✨ 로그 파일 위치 변경 (Logs/)
- 📖 로깅 가이드 작성

---

## 🔗 관련 문서

- [에러 처리 가이드](ERROR_HANDLING_GUIDE.md)
- [프로젝트 구조](PROJECT_README.md)
- [환경 설정](ENVIRONMENT_SETUP.md)

---

## 💡 Best Practices

### 1. 로그 레벨 선택

```python
# ✅ 좋은 예
logger.debug(f"변수: {var}")  # 디버깅 정보
logger.info("작업 완료")       # 일반 정보
logger.warning("재시도")       # 경고
logger.error("실패", exc_info=True)  # 에러 + 스택

# ❌ 나쁜 예
logger.info(f"변수: {var}")    # 너무 상세 (DEBUG 사용)
logger.error("작업 완료")       # 에러가 아님 (INFO 사용)
```

### 2. 로그 메시지 작성

```python
# ✅ 좋은 예
logger.info(f"문서 검색 완료: {count}개 발견")
logger.error(f"검색 실패: {e}", exc_info=True)
logger.debug(f"쿼리: {query}, k={k}")

# ❌ 나쁜 예
logger.info("완료")  # 불명확
logger.error(str(e))  # 컨텍스트 부족
logger.debug(query)   # 설명 없음
```

### 3. 에러 핸들러 사용

```python
# ✅ 좋은 예
error_handler = create_error_handler(logger)
return error_handler.handle_error(
    error=e,
    state=state,
    node_name="my_node",
    recoverable=True
)

# ❌ 나쁜 예 (표준화 안 됨)
logger.error(f"에러: {e}")
return {"error": str(e)}
```

---

**마지막 업데이트**: 2025-01-23  
**작성자**: AI Assistant  
**버전**: 2.0.0

