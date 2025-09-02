#!/usr/bin/env python3
"""
ISO/IEC 24759 검증 시스템 테스트 스크립트

이 스크립트는 구현된 ISO24759Validator 시스템을 테스트합니다.
"""

import sys
import os

# 현재 디렉토리를 Python 경로에 추가
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from validator import JSONValidator
from iso24759_validator import ISO24759Validator, ValidationError, TestItemNotFoundError

def test_basic_functionality():
    """기본 기능 테스트"""
    print("=" * 60)
    print("ISO/IEC 24759 검증 시스템 테스트")
    print("=" * 60)
    
    try:
        # 1. JSONValidator 초기화
        print("1. JSONValidator 초기화 중...")
        json_validator = JSONValidator()
        
        # 2. 샘플 JSON 파일 로드
        json_file = "20250630_test_report_sample(TE02.03.01).json"
        if os.path.exists(json_file):
            print(f"2. JSON 파일 로드 중: {json_file}")
            success = json_validator.load_json_file(json_file)
            if not success:
                print("   JSON 파일 로드 실패!")
                return False
        else:
            print(f"   경고: JSON 파일을 찾을 수 없습니다: {json_file}")
            print("   시스템 초기화만 테스트합니다.")
        
        # 3. ISO24759Validator 초기화
        print("3. ISO24759Validator 초기화 중...")
        validator = ISO24759Validator(json_validator)
        
        # 4. 시스템 상태 확인
        print("4. 시스템 상태 확인:")
        status = validator.get_system_status()
        print(f"   - 초기화 상태: {status['initialized']}")
        print(f"   - JSON 데이터: {status['json_data_status']}")
        print(f"   - 사용 가능한 TE 번호: {status['available_te_count']}개")
        
        if status['available_te_numbers']:
            print(f"   - TE 번호 목록: {', '.join(status['available_te_numbers'][:5])}")
            if len(status['available_te_numbers']) > 5:
                print(f"     (총 {len(status['available_te_numbers'])}개 중 5개만 표시)")
        
        # 5. 검증 규칙 정보 확인
        print("5. 검증 규칙 정보:")
        rule_status = status['rule_engine_status']
        print(f"   - 로드된 규칙: {rule_status['rules_count']}개")
        print(f"   - 캐시 활성화: {rule_status['cache_enabled']}")
        
        # 6. 단일 항목 검증 테스트 (TE02.03.01)
        test_te_number = "TE02.03.01"
        print(f"\n6. 단일 항목 검증 테스트: {test_te_number}")
        
        try:
            # 검증 상세 정보 조회
            details = validator.get_validation_details(test_te_number)
            if 'error' not in details:
                print(f"   - 규칙명: {details['rule_info']['name']}")
                print(f"   - 데이터 사용 가능: {details['data_available']}")
                
                if details['data_available']:
                    # 실제 검증 수행
                    print("   - 검증 실행 중...")
                    result = validator.validate_test_item(test_te_number)
                    
                    print(f"   - 검증 결과: {result.status.value}")
                    print(f"   - 시험항목명: {result.test_item_name}")
                    
                    if result.reasons:
                        print("   - 이유:")
                        for reason in result.reasons[:3]:  # 처음 3개만 표시
                            print(f"     • {reason}")
                    
                    if result.evidence:
                        print("   - 증거:")
                        for evidence in result.evidence[:3]:  # 처음 3개만 표시
                            print(f"     • {evidence}")
                else:
                    print("   - 시험항목 데이터를 찾을 수 없습니다.")
            else:
                print(f"   - 오류: {details['error']}")
                
        except TestItemNotFoundError as e:
            print(f"   - 시험항목 미발견: {e.message}")
        except ValidationError as e:
            print(f"   - 검증 오류: {e.message}")
        
        # 7. 다중 항목 검증 테스트
        print("\n7. 다중 항목 검증 테스트:")
        available_te_numbers = validator.get_available_te_numbers()
        
        if available_te_numbers:
            # 처음 3개 항목만 테스트
            test_items = available_te_numbers[:3]
            print(f"   - 테스트 항목: {', '.join(test_items)}")
            
            try:
                results = validator.validate_multiple_items(test_items, parallel=False)
                print(f"   - 검증 완료: {len(results)}개 결과")
                
                pass_count = sum(1 for r in results if r.status.value == "통과")
                fail_count = len(results) - pass_count
                print(f"   - 통과: {pass_count}개, 실패: {fail_count}개")
                
                # 요약 보고서 생성
                summary = validator.get_validation_summary(results)
                print(f"   - 통과율: {summary.get('pass_rate', 0)}%")
                
            except Exception as e:
                print(f"   - 다중 검증 오류: {str(e)}")
        else:
            print("   - 검증 가능한 항목이 없습니다.")
        
        # 8. 검증 이력 확인
        print("\n8. 검증 이력:")
        history = validator.get_validation_history(5)  # 최근 5개
        if history:
            for item in history:
                print(f"   - {item['te_number']}: {item['status']} ({item['timestamp'][:19]})")
        else:
            print("   - 검증 이력이 없습니다.")
        
        print("\n" + "=" * 60)
        print("테스트 완료!")
        print("=" * 60)
        return True
        
    except Exception as e:
        print(f"\n오류 발생: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

def test_configuration():
    """설정 시스템 테스트"""
    print("\n설정 시스템 테스트:")
    
    try:
        from iso24759_validator import ValidationConfig, RuleConfigLoader
        
        # 설정 로더 테스트
        loader = RuleConfigLoader()
        config_info = loader.get_config_info()
        
        print(f"- 설정 버전: {config_info.get('version')}")
        print(f"- ISO 표준 버전: {config_info.get('iso_standard_version')}")
        print(f"- 규칙 개수: {config_info.get('rules_count')}")
        
        # 규칙 유효성 검증
        rules = loader.get_all_rules()
        print(f"- 로드된 규칙: {len(rules)}개")
        
        for te_number, rule in list(rules.items())[:3]:  # 처음 3개만 표시
            print(f"  • {te_number}: {rule.name}")
        
        return True
        
    except Exception as e:
        print(f"설정 테스트 오류: {str(e)}")
        return False

if __name__ == "__main__":
    print("ISO/IEC 24759 검증 시스템 테스트 시작\n")
    
    # 기본 기능 테스트
    basic_success = test_basic_functionality()
    
    # 설정 시스템 테스트
    config_success = test_configuration()
    
    print(f"\n테스트 결과:")
    print(f"- 기본 기능: {'성공' if basic_success else '실패'}")
    print(f"- 설정 시스템: {'성공' if config_success else '실패'}")
    
    if basic_success and config_success:
        print("\n모든 테스트가 성공적으로 완료되었습니다! ✅")
        sys.exit(0)
    else:
        print("\n일부 테스트가 실패했습니다. ❌")
        sys.exit(1)