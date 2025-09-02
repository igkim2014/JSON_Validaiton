#!/usr/bin/env python3
"""
ISO/IEC 24759 검증 시스템 데모

이 스크립트는 구현된 ISO24759 검증 시스템의 핵심 기능을 보여줍니다.
"""

import json
import os
from datetime import datetime
from enum import Enum
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

## add: code rabbit comments


# 기본 데이터 모델들
class ValidationStatus(Enum):
    """검증 결과 상태"""

    PASS = "통과"
    FAIL = "실패"


@dataclass
class ValidationResult:
    """검증 결과를 담는 데이터 클래스"""

    test_item_name: str
    te_number: str
    status: ValidationStatus
    reasons: List[str] = field(default_factory=list)
    evidence: List[str] = field(default_factory=list)
    iso_references: List[str] = field(default_factory=list)
    timestamp: datetime = field(default_factory=datetime.now)


def demo_validation_system():
    """ISO24759 검증 시스템 데모"""
    print("=" * 60)
    print("ISO/IEC 24759 검증 시스템 데모")
    print("=" * 60)

    # 1. 시스템 개요
    print("1. 시스템 개요:")
    print("   - ISO/IEC 24759 표준 기반 CMVP 시험결과보고서 검증")
    print("   - MR(Machine Readable) 보고서 자동 검증")
    print("   - 표준 준수 여부 확인 및 상세 보고서 생성")

    # 2. 구현된 주요 컴포넌트
    print("\n2. 구현된 주요 컴포넌트:")
    components = [
        "ValidationRuleEngine - 검증 규칙 관리",
        "ComplianceChecker - 표준 준수 검사",
        "TestItemExtractor - 시험항목 데이터 추출",
        "ValidationResultFormatter - 결과 포맷팅",
        "ISO24759Validator - 메인 검증기",
    ]

    for component in components:
        print(f"   ✓ {component}")

    # 3. 검증 규칙 예시
    print("\n3. 검증 규칙 예시 (TE02.03.01):")

    # 설정 파일에서 규칙 로드 시도
    config_file = "config/validation_rules.json"
    if os.path.exists(config_file):
        try:
            with open(config_file, "r", encoding="utf-8") as f:
                config = json.load(f)

            te_rule = config.get("rules", {}).get("TE02.03.01", {})
            if te_rule:
                print(f"   - 규칙명: {te_rule.get('name', 'N/A')}")
                print(
                    f"   - 필수 메타데이터: {', '.join(te_rule.get('required_metadata', []))}"
                )
                print(
                    f"   - 필수 테이블 필드: {', '.join(te_rule.get('required_table_fields', []))}"
                )
                print(
                    f"   - 이미지 필요: {'예' if te_rule.get('required_images') else '아니오'}"
                )
                print(f"   - ISO 참조: {len(te_rule.get('iso_references', []))}개")
            else:
                print("   - 규칙 정보를 찾을 수 없습니다.")

        except Exception as e:
            print(f"   - 설정 파일 읽기 오류: {str(e)}")
    else:
        print("   - 설정 파일을 찾을 수 없습니다.")

    # 4. 검증 프로세스 시뮬레이션
    print("\n4. 검증 프로세스 시뮬레이션:")

    # 샘플 검증 결과 생성
    sample_results = [
        ValidationResult(
            test_item_name="암호모듈 시험",
            te_number="TE02.03.01",
            status=ValidationStatus.PASS,
            reasons=["모든 검증 항목을 통과했습니다 (점수: 0.85/0.70)"],
            evidence=[
                "metadata_completeness: CM_name, version, date, test_organization 확인",
                "table_structure: 테이블 구조 2행 × 3열",
                "content_accuracy: 시험 결과 통과 (1개 항목)",
            ],
            iso_references=["ISO/IEC 24759:2017 Section 7.2.1"],
        ),
        ValidationResult(
            test_item_name="암호모듈 인터페이스 시험",
            te_number="TE02.03.02",
            status=ValidationStatus.FAIL,
            reasons=[
                "검증 점수가 기준에 미달했습니다 (점수: 0.60/0.75)",
                "required_elements: 필수 이미지 자료가 없습니다",
            ],
            evidence=[
                "metadata_completeness: 인터페이스 정보 누락",
                "table_structure: 테이블 구조 확인됨",
            ],
            iso_references=["ISO/IEC 24759:2017 Section 7.2.2"],
        ),
    ]

    # 검증 결과 표시
    for i, result in enumerate(sample_results, 1):
        status_icon = "✅" if result.status == ValidationStatus.PASS else "❌"
        print(f"\n   [{i}] {status_icon} {result.test_item_name} ({result.te_number})")
        print(f"       상태: {result.status.value}")

        if result.reasons:
            print("       이유:")
            for reason in result.reasons:
                print(f"         • {reason}")

        if result.evidence:
            print("       증거:")
            for evidence in result.evidence[:2]:  # 처음 2개만 표시
                print(f"         • {evidence}")

    # 5. 요약 통계
    print("\n5. 검증 요약:")
    total_items = len(sample_results)
    pass_count = sum(1 for r in sample_results if r.status == ValidationStatus.PASS)
    fail_count = total_items - pass_count
    pass_rate = (pass_count / total_items) * 100 if total_items > 0 else 0

    print(f"   - 총 검증 항목: {total_items}개")
    print(f"   - 통과: {pass_count}개")
    print(f"   - 실패: {fail_count}개")
    print(f"   - 통과율: {pass_rate:.1f}%")

    # 6. 출력 형식 예시
    print("\n6. 다양한 출력 형식 지원:")
    print("   ✓ 텍스트 형식 (콘솔 출력)")
    print("   ✓ JSON 형식 (API 연동)")
    print("   ✓ HTML 형식 (웹 보고서)")
    print("   ✓ Markdown 형식 (문서화)")

    # 7. JSON 형식 예시
    print("\n7. JSON 출력 예시:")
    json_example = {
        "test_item_name": sample_results[0].test_item_name,
        "te_number": sample_results[0].te_number,
        "status": sample_results[0].status.value,
        "reasons": sample_results[0].reasons,
        "timestamp": sample_results[0].timestamp.isoformat(),
    }

    print(json.dumps(json_example, ensure_ascii=False, indent=2))

    print("\n" + "=" * 60)
    print("데모 완료!")
    print("=" * 60)

    return True


def show_implementation_status():
    """구현 상태 표시"""
    print("\n구현 상태:")
    print("=" * 40)

    completed_tasks = [
        "✅ 기본 데이터 모델 및 예외 클래스",
        "✅ 검증 규칙 설정 시스템",
        "✅ ValidationRuleEngine 클래스",
        "✅ ComplianceChecker 클래스",
        "✅ TestItemExtractor 클래스",
        "✅ ValidationResultFormatter 클래스",
        "✅ ISO24759Validator 메인 클래스",
    ]

    for task in completed_tasks:
        print(f"  {task}")

    print(f"\n총 {len(completed_tasks)}개 주요 컴포넌트 구현 완료")


print("code rabbit test: demo_iso24759.py loaded")

if __name__ == "__main__":
    print("ISO/IEC 24759 검증 시스템 데모 시작\n")

    # 데모 실행
    success = demo_validation_system()

    # 구현 상태 표시
    show_implementation_status()

    if success:
        print("\n✅ 데모가 성공적으로 완료되었습니다!")
        print("\n다음 단계:")
        print("- 단위 테스트 구현")
        print("- CLI 인터페이스 구현")
        print("- GUI 통합")
        print("- 성능 최적화")
    else:
        print("\n❌ 데모 실행 중 오류가 발생했습니다.")
