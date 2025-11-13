#!/usr/bin/env python3
"""
ISO/IEC 24759 검증 시스템 데모

이 스크립트는 구현된 ISO24759 검증 시스템의 핵심 기능을 보여줍니다.
실제 JSONValidator와 ISO24759Validator를 사용하여 검증을 수행합니다.
"""

import json
import os
import sys
from datetime import datetime
from typing import List, Optional, Dict, Any

# 실제 검증 시스템 모듈 임포트
from validator import JSONValidator
from iso24759_validator import (
    ISO24759Validator,
    ValidationResult,
    ValidationStatus,
    TestItemNotFoundError,
    ValidationError
)


def demo_validation_system(json_file_path: Optional[str] = None, te_numbers: Optional[List[str]] = None) -> List[ValidationResult]:
    """
    ISO24759 검증 시스템 데모를 실행하고 검증 결과를 반환합니다.

    Args:
        json_file_path: 검증할 JSON 파일 경로 (None일 경우 샘플 파일 사용)
        te_numbers: 검증할 TE 번호 목록 (None일 경우 기본 TE 목록 사용)

    Returns:
        검증 결과 목록 (List[ValidationResult])
    """
    print("=" * 60)
    print("ISO/IEC 24759 검증 시스템 데모")
    print("=" * 60)

    # 1. 시스템 개요
    print("\n1. 시스템 개요:")
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

    # 3. JSON 파일 결정
    if json_file_path is None:
        # 현재 디렉토리에서 JSON 파일 찾기
        json_files = [f for f in os.listdir('.') if f.endswith('.json') and not f.startswith('config')]
        if json_files:
            json_file_path = json_files[0]
            print(f"\n3. 기본 JSON 파일 사용: {json_file_path}")
        else:
            print("\n3. 경고: JSON 파일을 찾을 수 없습니다. 샘플 결과만 표시합니다.")
            return _generate_sample_results()
    else:
        print(f"\n3. JSON 파일: {json_file_path}")

    # 4. TE 번호 결정
    if te_numbers is None:
        # config.txt에서 TE 번호 읽기 시도
        if os.path.exists("config.txt"):
            try:
                from config_reader import read_config
                te_numbers = read_config("config.txt")
                print(f"4. config.txt에서 {len(te_numbers)}개 TE 번호 로드")
            except Exception as e:
                print(f"4. config.txt 읽기 실패: {str(e)}")
                te_numbers = ["TE02.03.01", "TE02.03.02"]
        else:
            te_numbers = ["TE02.03.01", "TE02.03.02"]
            print(f"4. 기본 TE 번호 사용: {te_numbers}")
    else:
        print(f"4. TE 번호: {te_numbers}")

    # 5. 검증 시스템 초기화
    print("\n5. 검증 시스템 초기화 중...")
    try:
        # JSONValidator 생성 및 JSON 파일 로드
        json_validator = JSONValidator()
        if not json_validator.load_json_file(json_file_path):
            print(f"   오류: JSON 파일 로드 실패 - {json_file_path}")
            return _generate_sample_results()

        print(f"   ✓ JSON 파일 로드 완료")

        # ISO24759Validator 생성
        validator = ISO24759Validator(json_validator)
        print(f"   ✓ ISO24759 검증기 초기화 완료")

        # 시스템 상태 확인
        status = validator.get_system_status()
        print(f"   ✓ 사용 가능한 TE 번호: {status.get('available_te_count', 0)}개")

    except Exception as e:
        print(f"   오류: 검증 시스템 초기화 실패 - {str(e)}")
        print(f"   상세: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        return _generate_sample_results()

    # 6. 검증 수행
    print("\n6. 검증 수행 중...")
    results = []

    for te_number in te_numbers:
        try:
            print(f"   - {te_number} 검증 중...")
            result = validator.validate_test_item(te_number)
            results.append(result)

            status_icon = "✅" if result.status == ValidationStatus.PASS else "❌"
            print(f"     {status_icon} {result.status.value}")

        except TestItemNotFoundError as e:
            print(f"     ⚠️  시험항목을 찾을 수 없습니다: {str(e)}")
        except ValidationError as e:
            print(f"     ❌ 검증 오류: {str(e)}")
        except Exception as e:
            print(f"     ❌ 예상치 못한 오류: {str(e)}")

    # 7. 결과가 없으면 샘플 결과 반환
    if not results:
        print("\n   경고: 실제 검증 결과가 없습니다. 샘플 결과를 생성합니다.")
        return _generate_sample_results()

    # 8. 결과 요약
    print("\n7. 검증 결과 요약:")
    _print_validation_summary(results)

    # 9. 상세 결과 표시
    print("\n8. 상세 검증 결과:")
    for i, result in enumerate(results, 1):
        _print_detailed_result(i, result)

    # 10. 출력 형식 예시
    print("\n9. 다양한 출력 형식 지원:")
    print("   ✓ 텍스트 형식 (콘솔 출력)")
    print("   ✓ JSON 형식 (API 연동)")
    print("   ✓ HTML 형식 (웹 보고서)")
    print("   ✓ Markdown 형식 (문서화)")

    print("\n" + "=" * 60)
    print("데모 완료!")
    print("=" * 60)

    return results


def _generate_sample_results() -> List[ValidationResult]:
    """샘플 검증 결과 생성"""
    print("\n   샘플 검증 결과를 생성합니다...")

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

    return sample_results


def _print_validation_summary(results: List[ValidationResult]):
    """검증 결과 요약 출력"""
    total_items = len(results)
    pass_count = sum(1 for r in results if r.status == ValidationStatus.PASS)
    fail_count = total_items - pass_count
    pass_rate = (pass_count / total_items) * 100 if total_items > 0 else 0

    print(f"   - 총 검증 항목: {total_items}개")
    print(f"   - 통과: {pass_count}개")
    print(f"   - 실패: {fail_count}개")
    print(f"   - 통과율: {pass_rate:.1f}%")


def _print_detailed_result(index: int, result: ValidationResult):
    """상세 검증 결과 출력"""
    status_icon = "✅" if result.status == ValidationStatus.PASS else "❌"
    print(f"\n   [{index}] {status_icon} {result.test_item_name} ({result.te_number})")
    print(f"       상태: {result.status.value}")

    if result.reasons:
        print("       이유:")
        for reason in result.reasons:
            print(f"         • {reason}")

    if result.evidence:
        print("       증거:")
        for evidence in result.evidence[:3]:  # 처음 3개만 표시
            print(f"         • {evidence}")

    if result.iso_references:
        print("       ISO 참조:")
        for ref in result.iso_references[:2]:  # 처음 2개만 표시
            print(f"         • {ref}")


def main():
    """메인 함수 - 커맨드라인에서 실행 시 호출"""
    import argparse

    parser = argparse.ArgumentParser(
        description='ISO/IEC 24759 검증 시스템 데모',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
사용 예시:
  # 기본 실행 (자동으로 JSON 파일과 TE 번호 찾기)
  python demo_iso24759.py

  # 특정 JSON 파일 지정
  python demo_iso24759.py -f sample_report.json

  # 특정 TE 번호만 검증
  python demo_iso24759.py -t TE02.03.01 TE02.03.02

  # JSON 파일과 TE 번호 모두 지정
  python demo_iso24759.py -f sample_report.json -t TE02.03.01
        '''
    )

    parser.add_argument(
        '-f', '--file',
        type=str,
        help='검증할 JSON 파일 경로'
    )

    parser.add_argument(
        '-t', '--te-numbers',
        nargs='+',
        help='검증할 TE 번호 목록 (예: TE02.03.01 TE02.03.02)'
    )

    args = parser.parse_args()

    # 데모 실행
    try:
        results = demo_validation_system(
            json_file_path=args.file,
            te_numbers=args.te_numbers
        )

        # 종료 코드 결정 (모든 검증이 통과하면 0, 아니면 1)
        if results:
            all_passed = all(r.status == ValidationStatus.PASS for r in results)
            sys.exit(0 if all_passed else 1)
        else:
            sys.exit(1)

    except KeyboardInterrupt:
        print("\n\n검증이 사용자에 의해 중단되었습니다.")
        sys.exit(130)
    except Exception as e:
        print(f"\n\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
