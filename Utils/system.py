"""
시스템 정보 수집 유틸리티 모듈

주요 기능:
- SystemInfoCollector: 시스템 정보 수집 및 상태 확인
"""

from typing import Dict, Any, Optional
from datetime import datetime

# logging import
from .logging import setup_logging


class SystemInfoCollector:
    """시스템 정보 수집 유틸리티 클래스"""

    def __init__(self):
        """SystemInfoCollector 초기화"""
        self.logger = setup_logging(__name__)

    def get_system_info(
        self,
        vector_store=None,
        workflow=None,
        llm_model: Optional[str] = None,
        config: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        """
        시스템 정보를 수집합니다.

        Args:
            vector_store: 벡터 스토어 객체
            workflow: LangGraph 워크플로우 객체
            llm_model: LLM 모델명
            config: 설정 딕셔너리

        Returns:
            시스템 정보 딕셔너리
        """
        try:
            info = {
                "vector_store_status": (
                    "available" if vector_store else "not available"
                ),
                "workflow_status": "ready" if workflow else "not ready",
                "llm_model": llm_model or "unknown",
                "timestamp": datetime.now().isoformat(),
            }

            # 설정 정보 추가
            if config:
                info["config"] = config
            else:
                info["config"] = {}

            # 벡터 스토어 상세 정보
            if vector_store:
                try:
                    # 간단한 테스트 검색으로 상태 확인
                    test_results = vector_store.similarity_search("test", k=1)
                    info["vector_store_test"] = "passed"
                except Exception as e:
                    info["vector_store_test"] = f"failed: {str(e)}"

            return info

        except Exception as e:
            self.logger.error(f"시스템 정보 수집 실패: {e}")
            return {
                "error": str(e),
                "timestamp": datetime.now().isoformat(),
            }

    def get_component_status(self, components: Dict[str, Any]) -> Dict[str, str]:
        """
        여러 컴포넌트의 상태를 확인합니다.

        Args:
            components: 컴포넌트 이름과 객체의 딕셔너리

        Returns:
            컴포넌트별 상태 딕셔너리
        """
        status = {}

        for name, component in components.items():
            if component is None:
                status[name] = "not initialized"
            elif hasattr(component, "__call__"):
                # 함수나 메서드인 경우
                status[name] = "available"
            else:
                # 객체인 경우
                status[name] = "available"

        return status

    def format_system_info(
        self, info: Dict[str, Any], include_details: bool = True
    ) -> str:
        """
        시스템 정보를 사람이 읽기 쉬운 형태로 포맷팅합니다.

        Args:
            info: 시스템 정보 딕셔너리
            include_details: 상세 정보 포함 여부

        Returns:
            포맷팅된 시스템 정보 문자열
        """
        try:
            lines = ["🔧 시스템 상태"]
            lines.append("=" * 50)

            # 기본 정보
            lines.append(
                f"📊 벡터 스토어: {info.get('vector_store_status', 'unknown')}"
            )
            lines.append(f"🔗 워크플로우: {info.get('workflow_status', 'unknown')}")
            lines.append(f"🤖 LLM 모델: {info.get('llm_model', 'unknown')}")

            # 타임스탬프
            if "timestamp" in info:
                lines.append(f"⏰ 확인 시간: {info['timestamp']}")

            # 상세 정보
            if include_details and "config" in info and info["config"]:
                lines.append("\n📋 설정 정보:")
                for key, value in info["config"].items():
                    lines.append(f"  • {key}: {value}")

            # 벡터 스토어 테스트 결과
            if "vector_store_test" in info:
                lines.append(
                    f"\n🧪 벡터 스토어 테스트: {info['vector_store_test']}"
                )

            return "\n".join(lines)

        except Exception as e:
            self.logger.error(f"시스템 정보 포맷팅 실패: {e}")
            return f"시스템 정보 포맷팅 실패: {e}"

