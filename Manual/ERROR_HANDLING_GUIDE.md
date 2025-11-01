# 에러 처리 표준화 가이드

## 📋 개요

모든 LangGraph 노드에서 일관된 에러 처리를 제공하는 `NodeErrorHandler` 클래스가 도입되었습니다.

---

## 🎯 목적

- ✅ **일관성**: 모든 노드에서 동일한 에러 처리 패턴
- ✅ **재시도 로직**: 자동 재시도 관리
- ✅ **로깅**: 표준화된 에러 로깅
- ✅ **유지보수성**: 중앙 집중식 에러 처리

---

## 📦 설치

```python
from Utils import create_error_handler, NodeErrorHandler
```

---

## 🚀 사용법

### 1. 기본 사용 예제

```python
from Utils import create_error_handler

def create_my_node(logger):
    """노드 생성 팩토리 함수"""
    
    # 에러 핸들러 생성
    error_handler = create_error_handler(logger, max_retries=6)
    
    def my_node(state):
        """노드 함수"""
        try:
            # 노드 로직
            result = do_something()
            
            # 성공 처리
            return error_handler.handle_success(
                node_name="my_node",
                message="작업 완료",
                return_fields={"result": result}
            )
            
        except Exception as e:
            # 에러 처리
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="my_node",
                recoverable=True,  # 재시도 가능
                return_fields={"result": None}
            )
    
    return my_node
```

---

## 📚 API 레퍼런스

### `create_error_handler(logger, max_retries=6)`

에러 핸들러 인스턴스를 생성합니다.

**Parameters:**
- `logger` (logging.Logger): 로거 객체
- `max_retries` (int): 최대 재시도 횟수 (기본값: 6)

**Returns:**
- `NodeErrorHandler`: 에러 핸들러 인스턴스

---

### `error_handler.handle_error()`

에러를 표준화된 방식으로 처리합니다.

**Parameters:**
- `error` (Exception): 발생한 예외
- `state` (Dict): 현재 State
- `node_name` (str): 노드 이름
- `recoverable` (bool): 재시도 가능 여부
  - `True`: 재시도 가능한 에러
  - `False`: 즉시 실패 처리
- `custom_message` (str, optional): 사용자 정의 에러 메시지
- `return_fields` (Dict, optional): 추가 반환 필드

**Returns:**
- `Dict`: State 업데이트용 딕셔너리
  - `error`: 에러 메시지
  - `should_retry`: 재시도 여부
  - `retry_count`: 업데이트된 재시도 횟수
  - `(추가 필드들)`

**예제:**
```python
# 복구 가능한 에러
return error_handler.handle_error(
    error=ValueError("검색 결과 없음"),
    state=state,
    node_name="retrieve_documents",
    recoverable=True,
    return_fields={"documents": [], "count": 0}
)

# 복구 불가능한 에러
return error_handler.handle_error(
    error=e,
    state=state,
    node_name="validate",
    recoverable=False,
    custom_message="치명적 검증 오류"
)
```

---

### `error_handler.handle_validation_error()`

검증 에러를 처리합니다 (MCQ 검증 등).

**Parameters:**
- `errors` (List[str]): 검증 오류 목록
- `state` (Dict): 현재 State
- `node_name` (str): 노드 이름 (기본값: "validation")

**Returns:**
- `Dict`: State 업데이트용 딕셔너리
  - `is_valid`: False
  - `validation_errors`: 오류 목록
  - `should_retry`: 재시도 여부
  - `retry_count`: 업데이트된 재시도 횟수

**예제:**
```python
errors = ["필수 필드 누락", "옵션 개수 부족"]
return error_handler.handle_validation_error(
    errors=errors,
    state=state,
    node_name="validate_mcq"
)
```

---

### `error_handler.handle_success()`

성공 케이스를 처리합니다 (로깅 포함).

**Parameters:**
- `node_name` (str): 노드 이름
- `message` (str, optional): 성공 메시지
- `return_fields` (Dict, optional): 반환할 필드들

**Returns:**
- `Dict`: State 업데이트용 딕셔너리
  - `error`: None
  - `(추가 필드들)`

**예제:**
```python
return error_handler.handle_success(
    node_name="retrieve_documents",
    message=f"{len(docs)}개 문서 검색 완료",
    return_fields={
        "documents": docs,
        "count": len(docs)
    }
)
```

---

## 🔄 재시도 로직

### 재시도 조건

1. `recoverable=True`로 설정
2. `retry_count < max_retries`
3. State의 `should_retry=True`

### 재시도 횟수 관리

```python
# State에서 재시도 정보 확인
from Utils import get_retry_info

info = get_retry_info(state)
print(f"재시도 {info['retry_count']}/{info['max_retries']}")
print(f"남은 재시도: {info['remaining_retries']}회")
```

---

## 📊 적용된 노드 목록

### MCQ 노드
- ✅ `format_context.py` - 컨텍스트 포맷팅
- ✅ `validate.py` - MCQ 검증
- ✅ `generate.py` - MCQ 생성
- ✅ `retrieve_documents.py` - 문서 검색
- ✅ `format_output.py` - 출력 포맷팅

### RAG 노드
- ✅ `retrieve.py` - 문서 검색

---

## 🎨 에러 로깅 형식

### 재시도 가능한 에러
```
❌ retrieve_documents 실패: 검색 결과 없음 (재시도 1/6)
```

### 재시도 불가능한 에러
```
❌ validate_mcq 실패: 치명적 검증 오류 (재시도 불가)
```

### 검증 에러
```
⚠️  validate_mcq 검증 실패: 필수 필드 누락; 옵션 개수 부족 (재시도 2/6)
```

### 성공
```
✅ retrieve_documents: 5개 문서 검색 완료
```

---

## 💡 Best Practices

### 1. 복구 가능 vs 불가능 에러 구분

```python
# ✅ 복구 가능: 네트워크 오류, 일시적 문제
return error_handler.handle_error(
    error=e,
    state=state,
    node_name="retrieve",
    recoverable=True  # 재시도 가능
)

# ✅ 복구 불가능: 데이터 손상, 치명적 오류
return error_handler.handle_error(
    error=e,
    state=state,
    node_name="validate",
    recoverable=False  # 즉시 종료
)
```

### 2. 커스텀 메시지 활용

```python
# ✅ 명확한 메시지
return error_handler.handle_error(
    error=e,
    state=state,
    node_name="retrieve_documents",
    recoverable=True,
    custom_message=f"'{query}' 검색 실패"  # 구체적
)
```

### 3. 추가 필드 반환

```python
# ✅ 필요한 필드 모두 포함
return error_handler.handle_error(
    error=e,
    state=state,
    node_name="retrieve",
    recoverable=True,
    return_fields={
        "documents": [],
        "count": 0,
        "selected_query": query  # 디버깅용 정보
    }
)
```

---

## 🧪 테스트 예제

```python
# 노드 테스트
def test_my_node():
    from Utils import create_error_handler
    import logging
    
    logger = logging.getLogger("test")
    error_handler = create_error_handler(logger, max_retries=3)
    
    # 성공 케이스
    state = {"retry_count": 0, "max_retries": 3}
    result = error_handler.handle_success(
        node_name="test_node",
        message="테스트 성공",
        return_fields={"data": "test"}
    )
    assert result["error"] is None
    assert result["data"] == "test"
    
    # 에러 케이스
    result = error_handler.handle_error(
        error=ValueError("테스트 에러"),
        state=state,
        node_name="test_node",
        recoverable=True
    )
    assert "에러" in result["error"]
    assert result["should_retry"] is True
    assert result["retry_count"] == 1
```

---

## 📈 마이그레이션 가이드

### 기존 코드 (Before)

```python
def my_node(state):
    try:
        result = do_something()
        logger.info("✅ 성공")
        return {"result": result, "error": None}
    except Exception as e:
        logger.error(f"❌ 실패: {e}", exc_info=True)
        retry_count = state.get("retry_count", 0) + 1
        return {
            "error": f"실패: {e}",
            "should_retry": True,
            "retry_count": retry_count,
            "result": None
        }
```

### 새 코드 (After)

```python
def create_my_node(logger):
    error_handler = create_error_handler(logger)
    
    def my_node(state):
        try:
            result = do_something()
            
            return error_handler.handle_success(
                node_name="my_node",
                message="성공",
                return_fields={"result": result}
            )
        except Exception as e:
            return error_handler.handle_error(
                error=e,
                state=state,
                node_name="my_node",
                recoverable=True,
                return_fields={"result": None}
            )
    
    return my_node
```

---

## 🔗 관련 문서

- [프로젝트 구조](PROJECT_README.md)
- [LangGraph 워크플로우](MCQ_LANGGRAPH_README.md)
- [Few-shot 가이드](FEW_SHOT_GUIDE.md)

---

## 📝 변경 이력

### 2025-01-23
- ✨ `NodeErrorHandler` 클래스 추가
- ✅ 모든 MCQ 노드에 적용
- ✅ RAG 노드에 적용
- 📖 문서 작성

---

## 💬 FAQ

**Q: 재시도 횟수를 변경하려면?**
```python
error_handler = create_error_handler(logger, max_retries=10)
```

**Q: 로그에 스택 트레이스를 표시하지 않으려면?**
```python
error_handler = create_error_handler(logger, log_traceback=False)
```

**Q: 특정 에러만 재시도하려면?**
```python
try:
    result = do_something()
except NetworkError as e:
    # 네트워크 오류는 재시도
    return error_handler.handle_error(e, state, "node", recoverable=True)
except DataError as e:
    # 데이터 오류는 즉시 종료
    return error_handler.handle_error(e, state, "node", recoverable=False)
```

---

**마지막 업데이트**: 2025-01-23  
**버전**: 1.0.0

