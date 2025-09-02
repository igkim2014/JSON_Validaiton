"""
ISO/IEC 24759 표준 기반 CMVP 시험결과보고서 검증 시스템

이 모듈은 MR(Machine Readable) 시험결과보고서의 정확성과 완전성을
ISO/IEC 24759 국제표준에 따라 자동으로 검증하는 기능을 제공합니다.
"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any
import json
import logging


# ============================================================================
# 열거형 정의
# ============================================================================

class ValidationStatus(Enum):
    """검증 결과 상태"""
    PASS = "통과"
    FAIL = "실패"


# ============================================================================
# 예외 클래스 계층 구조
# ============================================================================

class ValidationError(Exception):
    """기본 검증 오류 클래스"""
    def __init__(self, message: str, details: Optional[Dict[str, Any]] = None):
        super().__init__(message)
        self.message = message
        self.details = details or {}
        self.timestamp = datetime.now()


class TestItemNotFoundError(ValidationError):
    """시험항목을 찾을 수 없을 때 발생하는 오류"""
    def __init__(self, te_number: str, message: Optional[str] = None):
        self.te_number = te_number
        default_message = f"시험항목 '{te_number}'을(를) MR 보고서에서 찾을 수 없습니다."
        super().__init__(message or default_message, {"te_number": te_number})


class InvalidRuleConfigError(ValidationError):
    """검증 규칙 설정이 잘못되었을 때 발생하는 오류"""
    def __init__(self, rule_name: str, message: Optional[str] = None):
        self.rule_name = rule_name
        default_message = f"검증 규칙 '{rule_name}' 설정에 오류가 있습니다."
        super().__init__(message or default_message, {"rule_name": rule_name})


class ComplianceCheckError(ValidationError):
    """표준 준수 검사 중 발생하는 오류"""
    def __init__(self, check_type: str, message: Optional[str] = None):
        self.check_type = check_type
        default_message = f"표준 준수 검사 '{check_type}' 중 오류가 발생했습니다."
        super().__init__(message or default_message, {"check_type": check_type})


# ============================================================================
# 데이터 모델 클래스
# ============================================================================

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
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "test_item_name": self.test_item_name,
            "te_number": self.te_number,
            "status": self.status.value,
            "reasons": self.reasons,
            "evidence": self.evidence,
            "iso_references": self.iso_references,
            "timestamp": self.timestamp.isoformat()
        }
    
    def to_json(self) -> str:
        """JSON 문자열로 변환"""
        return json.dumps(self.to_dict(), ensure_ascii=False, indent=2)


@dataclass
class ComplianceResult:
    """개별 준수 검사 결과를 담는 데이터 클래스"""
    rule_name: str
    passed: bool
    message: str
    iso_reference: str
    evidence: Optional[str] = None
    weight: float = 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "rule_name": self.rule_name,
            "passed": self.passed,
            "message": self.message,
            "iso_reference": self.iso_reference,
            "evidence": self.evidence,
            "weight": self.weight
        }


@dataclass
class TestItemData:
    """시험항목 데이터를 담는 데이터 클래스"""
    te_number: str
    page_number: int
    table_data: Dict[str, Any]
    metadata: Dict[str, Any]
    has_image: bool
    image_data: Optional[Dict[str, Any]] = None
    cells: Optional[List[Dict[str, Any]]] = None
    caption: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "te_number": self.te_number,
            "page_number": self.page_number,
            "table_data": self.table_data,
            "metadata": self.metadata,
            "has_image": self.has_image,
            "image_data": self.image_data,
            "cells": self.cells,
            "caption": self.caption
        }


@dataclass
class ValidationRule:
    """검증 규칙을 정의하는 데이터 클래스"""
    name: str
    te_number: str
    required_metadata: List[str] = field(default_factory=list)
    required_table_fields: List[str] = field(default_factory=list)
    required_images: bool = False
    iso_references: List[str] = field(default_factory=list)
    validation_checks: List[Dict[str, Any]] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """딕셔너리 형태로 변환"""
        return {
            "name": self.name,
            "te_number": self.te_number,
            "required_metadata": self.required_metadata,
            "required_table_fields": self.required_table_fields,
            "required_images": self.required_images,
            "iso_references": self.iso_references,
            "validation_checks": self.validation_checks
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'ValidationRule':
        """딕셔너리에서 ValidationRule 객체 생성"""
        return cls(
            name=data.get("name", ""),
            te_number=data.get("te_number", ""),
            required_metadata=data.get("required_metadata", []),
            required_table_fields=data.get("required_table_fields", []),
            required_images=data.get("required_images", False),
            iso_references=data.get("iso_references", []),
            validation_checks=data.get("validation_checks", [])
        )


# ============================================================================
# 로깅 설정
# ============================================================================

def setup_logging(level: str = "INFO") -> logging.Logger:
    """로깅 설정"""
    logger = logging.getLogger("iso24759_validator")
    logger.setLevel(getattr(logging, level.upper()))
    
    if not logger.handlers:
        handler = logging.StreamHandler()
        formatter = logging.Formatter(
            '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
        )
        handler.setFormatter(formatter)
        logger.addHandler(handler)
    
    return logger


# 기본 로거 인스턴스
logger = setup_logging()


# ============================================================================
# 설정 관리 클래스
# ============================================================================

class ValidationConfig:
    """검증 시스템 설정 관리"""
    RULES_FILE_PATH = "config/validation_rules.json"
    LOG_LEVEL = "INFO"
    MAX_CONCURRENT_VALIDATIONS = 5
    CACHE_ENABLED = True
    CACHE_TTL = 3600  # 1 hour
    
    @classmethod
    def load_from_file(cls, config_path: str = None) -> Dict[str, Any]:
        """설정 파일에서 설정 로드"""
        path = config_path or cls.RULES_FILE_PATH
        try:
            with open(path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except FileNotFoundError:
            raise InvalidRuleConfigError(
                "config_file", 
                f"설정 파일을 찾을 수 없습니다: {path}"
            )
        except json.JSONDecodeError as e:
            raise InvalidRuleConfigError(
                "config_parse", 
                f"설정 파일 파싱 오류: {str(e)}"
            )


class RuleConfigLoader:
    """검증 규칙 설정 로더 및 파서"""
    
    def __init__(self, config_path: str = None):
        self.config_path = config_path or ValidationConfig.RULES_FILE_PATH
        self.config_data = None
        self.rules_cache = {}
        self.last_loaded = None
        
    def load_rules(self) -> Dict[str, ValidationRule]:
        """검증 규칙을 로드하고 ValidationRule 객체로 변환"""
        try:
            self.config_data = ValidationConfig.load_from_file(self.config_path)
            self.last_loaded = datetime.now()
            
            # 설정 유효성 검증
            self._validate_config_structure()
            
            # 규칙 객체 생성
            rules = {}
            for te_number, rule_data in self.config_data.get("rules", {}).items():
                rule_data["te_number"] = te_number
                rules[te_number] = ValidationRule.from_dict(rule_data)
                
            self.rules_cache = rules
            logger.info(f"검증 규칙 {len(rules)}개를 성공적으로 로드했습니다.")
            return rules
            
        except Exception as e:
            logger.error(f"검증 규칙 로드 실패: {str(e)}")
            raise InvalidRuleConfigError("rule_loading", str(e))
    
    def _validate_config_structure(self):
        """설정 파일 구조 유효성 검증"""
        if not isinstance(self.config_data, dict):
            raise InvalidRuleConfigError("config_structure", "설정 파일이 올바른 JSON 객체가 아닙니다.")
        
        required_fields = ["version", "iso_standard_version", "rules"]
        for field in required_fields:
            if field not in self.config_data:
                raise InvalidRuleConfigError("config_structure", f"필수 필드 '{field}'가 없습니다.")
        
        # 규칙 구조 검증
        rules = self.config_data.get("rules", {})
        for te_number, rule_data in rules.items():
            self._validate_rule_structure(te_number, rule_data)
    
    def _validate_rule_structure(self, te_number: str, rule_data: Dict[str, Any]):
        """개별 규칙 구조 유효성 검증"""
        required_fields = ["name", "required_metadata", "required_table_fields", "validation_checks"]
        for field in required_fields:
            if field not in rule_data:
                raise InvalidRuleConfigError(
                    te_number, 
                    f"규칙 '{te_number}'에 필수 필드 '{field}'가 없습니다."
                )
        
        # validation_checks 구조 검증
        checks = rule_data.get("validation_checks", [])
        if not isinstance(checks, list) or len(checks) == 0:
            raise InvalidRuleConfigError(
                te_number,
                f"규칙 '{te_number}'의 validation_checks가 비어있거나 올바르지 않습니다."
            )
        
        for check in checks:
            if not isinstance(check, dict) or "type" not in check or "weight" not in check:
                raise InvalidRuleConfigError(
                    te_number,
                    f"규칙 '{te_number}'의 validation_check 구조가 올바르지 않습니다."
                )
    
    def get_rule(self, te_number: str) -> Optional[ValidationRule]:
        """특정 TE 번호에 대한 규칙 반환"""
        if not self.rules_cache:
            self.load_rules()
        return self.rules_cache.get(te_number)
    
    def get_all_rules(self) -> Dict[str, ValidationRule]:
        """모든 규칙 반환"""
        if not self.rules_cache:
            self.load_rules()
        return self.rules_cache.copy()
    
    def get_config_info(self) -> Dict[str, Any]:
        """설정 정보 반환"""
        if not self.config_data:
            self.load_rules()
        
        return {
            "version": self.config_data.get("version"),
            "iso_standard_version": self.config_data.get("iso_standard_version"),
            "last_updated": self.config_data.get("last_updated"),
            "rules_count": len(self.config_data.get("rules", {})),
            "last_loaded": self.last_loaded.isoformat() if self.last_loaded else None
        }
    
    def reload_if_needed(self) -> bool:
        """필요시 규칙 재로드 (파일 변경 감지)"""
        try:
            import os
            if os.path.exists(self.config_path):
                file_mtime = datetime.fromtimestamp(os.path.getmtime(self.config_path))
                if not self.last_loaded or file_mtime > self.last_loaded:
                    logger.info("설정 파일이 변경되어 규칙을 재로드합니다.")
                    self.load_rules()
                    return True
            return False
        except Exception as e:
            logger.warning(f"파일 변경 감지 실패: {str(e)}")
            return False


class RuleValidator:
    """검증 규칙 자체의 유효성을 검증하는 클래스"""
    
    VALID_CHECK_TYPES = {
        "metadata_completeness",
        "table_structure", 
        "content_accuracy",
        "required_elements"
    }
    
    @classmethod
    def validate_rule(cls, rule: ValidationRule) -> List[str]:
        """규칙의 유효성을 검증하고 오류 목록 반환"""
        errors = []
        
        # 기본 필드 검증
        if not rule.name or not rule.name.strip():
            errors.append("규칙 이름이 비어있습니다.")
        
        if not rule.te_number or not rule.te_number.strip():
            errors.append("TE 번호가 비어있습니다.")
        
        # TE 번호 형식 검증
        if rule.te_number and not cls._is_valid_te_number(rule.te_number):
            errors.append(f"TE 번호 형식이 올바르지 않습니다: {rule.te_number}")
        
        # validation_checks 검증
        total_weight = 0
        for check in rule.validation_checks:
            check_type = check.get("type")
            weight = check.get("weight", 0)
            
            if check_type not in cls.VALID_CHECK_TYPES:
                errors.append(f"알 수 없는 검증 타입: {check_type}")
            
            if not isinstance(weight, (int, float)) or weight <= 0:
                errors.append(f"검증 가중치가 올바르지 않습니다: {weight}")
            
            total_weight += weight
        
        # 가중치 합계 검증
        if abs(total_weight - 1.0) > 0.01:  # 부동소수점 오차 허용
            errors.append(f"검증 가중치 합계가 1.0이 아닙니다: {total_weight}")
        
        return errors
    
    @staticmethod
    def _is_valid_te_number(te_number: str) -> bool:
        """TE 번호 형식 유효성 검증"""
        import re
        # TE02.03.01 형식 검증
        pattern = r'^TE\d{2}\.\d{2}\.\d{2}$'
        return bool(re.match(pattern, te_number))


# ============================================================================
# 검증 규칙 엔진
# ============================================================================

class ValidationRuleEngine:
    """검증 규칙 엔진 - 규칙 로딩, 캐싱, 관리를 담당"""
    
    def __init__(self, config_path: str = None):
        self.config_loader = RuleConfigLoader(config_path)
        self.rules_cache = {}
        self.cache_enabled = ValidationConfig.CACHE_ENABLED
        self.cache_ttl = ValidationConfig.CACHE_TTL
        self.last_cache_update = None
        self.rule_validator = RuleValidator()
        self.change_history = []  # 규칙 변경 이력
        
    def get_rules_for_test_item(self, te_number: str) -> Optional[ValidationRule]:
        """특정 시험항목에 적용할 검증 규칙 반환"""
        try:
            # 캐시 유효성 확인 및 필요시 재로드
            if self._should_reload_cache():
                self._reload_rules()
            
            # 규칙 조회
            rule = self.rules_cache.get(te_number)
            if rule is None:
                logger.warning(f"시험항목 '{te_number}'에 대한 검증 규칙을 찾을 수 없습니다.")
                return None
            
            # 규칙 유효성 재검증
            validation_errors = self.rule_validator.validate_rule(rule)
            if validation_errors:
                logger.error(f"규칙 '{te_number}' 유효성 검증 실패: {validation_errors}")
                raise InvalidRuleConfigError(te_number, f"규칙 유효성 오류: {', '.join(validation_errors)}")
            
            logger.debug(f"시험항목 '{te_number}'에 대한 규칙을 성공적으로 반환했습니다.")
            return rule
            
        except Exception as e:
            logger.error(f"규칙 조회 중 오류 발생: {str(e)}")
            raise
    
    def get_all_rules(self) -> Dict[str, ValidationRule]:
        """모든 검증 규칙 반환"""
        try:
            if self._should_reload_cache():
                self._reload_rules()
            return self.rules_cache.copy()
        except Exception as e:
            logger.error(f"전체 규칙 조회 중 오류 발생: {str(e)}")
            raise
    
    def reload_rules(self) -> bool:
        """규칙 강제 재로드"""
        try:
            logger.info("검증 규칙을 강제로 재로드합니다.")
            return self._reload_rules()
        except Exception as e:
            logger.error(f"규칙 재로드 실패: {str(e)}")
            raise
    
    def _reload_rules(self) -> bool:
        """내부 규칙 재로드 메서드"""
        try:
            old_rules_count = len(self.rules_cache)
            
            # 새 규칙 로드
            new_rules = self.config_loader.load_rules()
            
            # 변경 사항 추적
            self._track_rule_changes(self.rules_cache, new_rules)
            
            # 캐시 업데이트
            self.rules_cache = new_rules
            self.last_cache_update = datetime.now()
            
            new_rules_count = len(self.rules_cache)
            logger.info(f"규칙 재로드 완료: {old_rules_count} -> {new_rules_count}개")
            
            return True
            
        except Exception as e:
            logger.error(f"규칙 재로드 중 오류: {str(e)}")
            raise InvalidRuleConfigError("reload", f"규칙 재로드 실패: {str(e)}")
    
    def _should_reload_cache(self) -> bool:
        """캐시 재로드 필요 여부 판단"""
        if not self.cache_enabled:
            return True
        
        if not self.rules_cache:
            return True
        
        if self.last_cache_update is None:
            return True
        
        # TTL 확인
        cache_age = (datetime.now() - self.last_cache_update).total_seconds()
        if cache_age > self.cache_ttl:
            logger.debug("캐시 TTL 만료로 재로드가 필요합니다.")
            return True
        
        # 파일 변경 확인
        if self.config_loader.reload_if_needed():
            return True
        
        return False
    
    def _track_rule_changes(self, old_rules: Dict[str, ValidationRule], new_rules: Dict[str, ValidationRule]):
        """규칙 변경 사항 추적"""
        timestamp = datetime.now()
        changes = []
        
        # 새로 추가된 규칙
        for te_number in new_rules:
            if te_number not in old_rules:
                changes.append({
                    "type": "added",
                    "te_number": te_number,
                    "rule_name": new_rules[te_number].name,
                    "timestamp": timestamp
                })
        
        # 삭제된 규칙
        for te_number in old_rules:
            if te_number not in new_rules:
                changes.append({
                    "type": "removed", 
                    "te_number": te_number,
                    "rule_name": old_rules[te_number].name,
                    "timestamp": timestamp
                })
        
        # 수정된 규칙 (간단한 비교)
        for te_number in old_rules:
            if te_number in new_rules:
                old_rule = old_rules[te_number]
                new_rule = new_rules[te_number]
                
                if (old_rule.name != new_rule.name or 
                    old_rule.required_metadata != new_rule.required_metadata or
                    old_rule.required_table_fields != new_rule.required_table_fields or
                    old_rule.validation_checks != new_rule.validation_checks):
                    
                    changes.append({
                        "type": "modified",
                        "te_number": te_number,
                        "rule_name": new_rule.name,
                        "timestamp": timestamp
                    })
        
        # 변경 이력에 추가
        if changes:
            self.change_history.extend(changes)
            # 이력 크기 제한 (최근 100개만 유지)
            if len(self.change_history) > 100:
                self.change_history = self.change_history[-100:]
            
            logger.info(f"규칙 변경 사항 {len(changes)}개를 감지했습니다.")
    
    def get_change_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """규칙 변경 이력 반환"""
        return self.change_history[-limit:] if limit > 0 else self.change_history
    
    def get_engine_status(self) -> Dict[str, Any]:
        """엔진 상태 정보 반환"""
        return {
            "rules_count": len(self.rules_cache),
            "cache_enabled": self.cache_enabled,
            "cache_ttl": self.cache_ttl,
            "last_cache_update": self.last_cache_update.isoformat() if self.last_cache_update else None,
            "change_history_count": len(self.change_history),
            "config_info": self.config_loader.get_config_info()
        }
    
    def validate_all_rules(self) -> Dict[str, List[str]]:
        """모든 규칙의 유효성 검증"""
        validation_results = {}
        
        try:
            if self._should_reload_cache():
                self._reload_rules()
            
            for te_number, rule in self.rules_cache.items():
                errors = self.rule_validator.validate_rule(rule)
                if errors:
                    validation_results[te_number] = errors
            
            if validation_results:
                logger.warning(f"{len(validation_results)}개 규칙에서 유효성 오류가 발견되었습니다.")
            else:
                logger.info("모든 규칙이 유효성 검증을 통과했습니다.")
            
            return validation_results
            
        except Exception as e:
            logger.error(f"규칙 유효성 검증 중 오류: {str(e)}")
            raise
    
    def clear_cache(self):
        """캐시 강제 클리어"""
        self.rules_cache.clear()
        self.last_cache_update = None
        logger.info("규칙 캐시가 클리어되었습니다.")
    
    def set_cache_config(self, enabled: bool = True, ttl: int = 3600):
        """캐시 설정 변경"""
        self.cache_enabled = enabled
        self.cache_ttl = ttl
        logger.info(f"캐시 설정 변경: enabled={enabled}, ttl={ttl}")
        
        if not enabled:
            self.clear_cache()


# ============================================================================
# 표준 준수 검사기
# ============================================================================

class ComplianceChecker:
    """ISO/IEC 24759 표준 준수 검사를 수행하는 클래스"""
    
    def __init__(self):
        self.metadata_validator = MetadataValidator()
        self.table_validator = TableValidator()
        self.content_validator = ContentValidator()
        self.element_validator = ElementValidator()
    
    def check_metadata_completeness(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """메타데이터 완전성 검사"""
        try:
            return self.metadata_validator.validate_completeness(test_data, rule)
        except Exception as e:
            logger.error(f"메타데이터 완전성 검사 중 오류: {str(e)}")
            raise ComplianceCheckError("metadata_completeness", str(e))
    
    def check_table_structure(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """시험결과판정근거 테이블 구조 검사"""
        try:
            return self.table_validator.validate_structure(test_data, rule)
        except Exception as e:
            logger.error(f"테이블 구조 검사 중 오류: {str(e)}")
            raise ComplianceCheckError("table_structure", str(e))
    
    def check_content_accuracy(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """내용 정확성 검사"""
        try:
            return self.content_validator.validate_accuracy(test_data, rule)
        except Exception as e:
            logger.error(f"내용 정확성 검사 중 오류: {str(e)}")
            raise ComplianceCheckError("content_accuracy", str(e))
    
    def check_required_elements(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """필수 요소 존재 여부 검사"""
        try:
            return self.element_validator.validate_required_elements(test_data, rule)
        except Exception as e:
            logger.error(f"필수 요소 검사 중 오류: {str(e)}")
            raise ComplianceCheckError("required_elements", str(e))


class MetadataValidator:
    """메타데이터 검증을 담당하는 클래스"""
    
    def __init__(self):
        self.required_patterns = {
            "version": r"^\d+\.\d+(\.\d+)?$",
            "date": r"^\d{4}-\d{2}-\d{2}$"
        }
    
    def validate_completeness(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """메타데이터 완전성 검증"""
        missing_fields = []
        invalid_fields = []
        evidence_details = []
        
        metadata = test_data.metadata
        required_metadata = rule.required_metadata
        
        # 필수 메타데이터 존재 여부 확인
        for field in required_metadata:
            if field not in metadata or not metadata[field]:
                missing_fields.append(field)
            else:
                # 필드별 형식 검증
                validation_result = self._validate_field_format(field, metadata[field])
                if not validation_result["valid"]:
                    invalid_fields.append({
                        "field": field,
                        "value": metadata[field],
                        "error": validation_result["error"]
                    })
                else:
                    evidence_details.append(f"{field}: {metadata[field]}")
        
        # 결과 판정
        passed = len(missing_fields) == 0 and len(invalid_fields) == 0
        
        # 메시지 생성
        if passed:
            message = f"모든 필수 메타데이터({len(required_metadata)}개)가 올바르게 제공되었습니다."
        else:
            error_parts = []
            if missing_fields:
                error_parts.append(f"누락된 필드: {', '.join(missing_fields)}")
            if invalid_fields:
                invalid_details = [f"{item['field']}({item['error']})" for item in invalid_fields]
                error_parts.append(f"형식 오류: {', '.join(invalid_details)}")
            message = "; ".join(error_parts)
        
        # 증거 자료 생성
        evidence = "; ".join(evidence_details) if evidence_details else None
        
        return ComplianceResult(
            rule_name="metadata_completeness",
            passed=passed,
            message=message,
            iso_reference="ISO/IEC 24759:2017 Section 7.1 - Test Report Metadata",
            evidence=evidence
        )
    
    def _validate_field_format(self, field_name: str, field_value: str) -> Dict[str, Any]:
        """개별 필드 형식 검증"""
        if not isinstance(field_value, str):
            return {"valid": False, "error": "문자열이 아님"}
        
        field_value = field_value.strip()
        if not field_value:
            return {"valid": False, "error": "빈 값"}
        
        # 패턴 검증
        if field_name in self.required_patterns:
            import re
            pattern = self.required_patterns[field_name]
            if not re.match(pattern, field_value):
                return {"valid": False, "error": f"형식 불일치 (예상: {pattern})"}
        
        # 특별한 검증 규칙
        if field_name == "CM_name":
            if len(field_value) < 2:
                return {"valid": False, "error": "암호모듈명이 너무 짧음"}
        
        elif field_name == "test_organization":
            if len(field_value) < 3:
                return {"valid": False, "error": "시험기관명이 너무 짧음"}
        
        elif field_name == "date":
            # 날짜 유효성 추가 검증
            try:
                from datetime import datetime
                datetime.strptime(field_value, "%Y-%m-%d")
            except ValueError:
                return {"valid": False, "error": "유효하지 않은 날짜"}
        
        return {"valid": True, "error": None}
    
    def get_metadata_summary(self, metadata: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 요약 정보 생성"""
        return {
            "total_fields": len(metadata),
            "non_empty_fields": len([v for v in metadata.values() if v]),
            "field_names": list(metadata.keys()),
            "has_required_basic": all(
                field in metadata and metadata[field] 
                for field in ["CM_name", "version", "date"]
            )
        }

class TableValidator:
    """테이블 구조 검증을 담당하는 클래스"""
    
    def __init__(self):
        self.required_cell_types = ["header", "data"]
        self.min_table_rows = 2  # 최소 헤더 + 1개 데이터 행
    
    def validate_structure(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """테이블 구조 검증"""
        table_data = test_data.table_data
        required_fields = rule.required_table_fields
        
        structure_issues = []
        evidence_details = []
        
        # 기본 테이블 존재 확인
        if not table_data:
            return ComplianceResult(
                rule_name="table_structure",
                passed=False,
                message="시험결과판정근거 테이블이 존재하지 않습니다.",
                iso_reference="ISO/IEC 24759:2017 Section 7.2 - Test Results Table"
            )
        
        # 테이블 셀 구조 검증
        cells = test_data.cells or []
        if not cells:
            structure_issues.append("테이블 셀 데이터가 없습니다")
        else:
            cell_validation = self._validate_cell_structure(cells)
            if not cell_validation["valid"]:
                structure_issues.extend(cell_validation["errors"])
            else:
                evidence_details.extend(cell_validation["evidence"])
        
        # 필수 필드 존재 확인
        field_validation = self._validate_required_fields(table_data, required_fields)
        if not field_validation["valid"]:
            structure_issues.extend(field_validation["errors"])
        else:
            evidence_details.extend(field_validation["evidence"])
        
        # 테이블 내용 일관성 검증
        consistency_validation = self._validate_table_consistency(table_data, cells)
        if not consistency_validation["valid"]:
            structure_issues.extend(consistency_validation["errors"])
        else:
            evidence_details.extend(consistency_validation["evidence"])
        
        # 결과 판정
        passed = len(structure_issues) == 0
        
        if passed:
            message = f"테이블 구조가 ISO/IEC 24759 표준을 준수합니다. (필수 필드 {len(required_fields)}개 확인)"
        else:
            message = f"테이블 구조 오류: {'; '.join(structure_issues)}"
        
        evidence = "; ".join(evidence_details) if evidence_details else None
        
        return ComplianceResult(
            rule_name="table_structure",
            passed=passed,
            message=message,
            iso_reference="ISO/IEC 24759:2017 Section 7.2 - Test Results Table Structure",
            evidence=evidence
        )
    
    def _validate_cell_structure(self, cells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """테이블 셀 구조 검증"""
        errors = []
        evidence = []
        
        if len(cells) < self.min_table_rows:
            errors.append(f"테이블 행 수가 부족합니다 (최소 {self.min_table_rows}행 필요, 현재 {len(cells)}행)")
            return {"valid": False, "errors": errors, "evidence": evidence}
        
        # 셀 타입 분포 확인
        cell_types = {}
        for cell in cells:
            cell_type = cell.get("type", "unknown")
            cell_types[cell_type] = cell_types.get(cell_type, 0) + 1
        
        # 필수 셀 타입 확인
        for required_type in self.required_cell_types:
            if required_type not in cell_types:
                errors.append(f"필수 셀 타입 '{required_type}'이 없습니다")
            else:
                evidence.append(f"{required_type} 셀 {cell_types[required_type]}개")
        
        # 헤더 행 검증
        header_cells = [cell for cell in cells if cell.get("type") == "header"]
        if header_cells:
            header_validation = self._validate_header_cells(header_cells)
            if not header_validation["valid"]:
                errors.extend(header_validation["errors"])
            else:
                evidence.extend(header_validation["evidence"])
        
        # 데이터 행 검증
        data_cells = [cell for cell in cells if cell.get("type") == "data"]
        if data_cells:
            data_validation = self._validate_data_cells(data_cells)
            if not data_validation["valid"]:
                errors.extend(data_validation["errors"])
            else:
                evidence.extend(data_validation["evidence"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_header_cells(self, header_cells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """헤더 셀 검증"""
        errors = []
        evidence = []
        
        if not header_cells:
            errors.append("헤더 셀이 없습니다")
            return {"valid": False, "errors": errors, "evidence": evidence}
        
        # 헤더 텍스트 검증
        header_texts = []
        for cell in header_cells:
            text = cell.get("text", "").strip()
            if not text:
                errors.append("빈 헤더 셀이 있습니다")
            else:
                header_texts.append(text)
        
        if header_texts:
            evidence.append(f"헤더: {', '.join(header_texts)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_data_cells(self, data_cells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """데이터 셀 검증"""
        errors = []
        evidence = []
        
        if not data_cells:
            errors.append("데이터 셀이 없습니다")
            return {"valid": False, "errors": errors, "evidence": evidence}
        
        # 데이터 셀 내용 검증
        empty_cells = 0
        total_cells = len(data_cells)
        
        for cell in data_cells:
            text = cell.get("text", "").strip()
            if not text:
                empty_cells += 1
        
        # 빈 셀 비율 확인 (50% 이상이면 문제)
        empty_ratio = empty_cells / total_cells if total_cells > 0 else 0
        if empty_ratio > 0.5:
            errors.append(f"빈 데이터 셀이 너무 많습니다 ({empty_cells}/{total_cells}, {empty_ratio:.1%})")
        else:
            evidence.append(f"데이터 셀 {total_cells}개 (빈 셀 {empty_cells}개, {empty_ratio:.1%})")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_required_fields(self, table_data: Dict[str, Any], required_fields: List[str]) -> Dict[str, Any]:
        """필수 필드 존재 확인"""
        errors = []
        evidence = []
        
        # 테이블 데이터에서 필드 추출 (다양한 형태 지원)
        available_fields = set()
        
        # 직접 키로 존재하는 경우
        available_fields.update(table_data.keys())
        
        # 중첩된 구조에서 필드 추출
        for key, value in table_data.items():
            if isinstance(value, dict):
                available_fields.update(value.keys())
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, dict):
                        available_fields.update(item.keys())
        
        # 필수 필드 확인
        missing_fields = []
        found_fields = []
        
        for field in required_fields:
            # 정확한 매칭 또는 부분 매칭 확인
            field_found = False
            for available_field in available_fields:
                if field in available_field or available_field in field:
                    field_found = True
                    found_fields.append(field)
                    break
            
            if not field_found:
                missing_fields.append(field)
        
        if missing_fields:
            errors.append(f"필수 필드 누락: {', '.join(missing_fields)}")
        
        if found_fields:
            evidence.append(f"필수 필드 확인: {', '.join(found_fields)}")
        
        return {
            "valid": len(missing_fields) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_table_consistency(self, table_data: Dict[str, Any], cells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """테이블 내용 일관성 검증"""
        errors = []
        evidence = []
        
        # 행-열 일관성 확인
        if cells:
            rows = {}
            cols = {}
            
            for cell in cells:
                row = cell.get("row", 0)
                col = cell.get("col", 0)
                
                if row not in rows:
                    rows[row] = []
                rows[row].append(col)
                
                if col not in cols:
                    cols[col] = []
                cols[col].append(row)
            
            # 행별 열 수 일관성 확인
            if len(rows) > 1:
                col_counts = [len(cols) for cols in rows.values()]
                if len(set(col_counts)) > 1:
                    errors.append(f"행별 열 수가 일치하지 않습니다: {col_counts}")
                else:
                    evidence.append(f"테이블 구조: {len(rows)}행 × {col_counts[0]}열")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }


class ContentValidator:
    """내용 정확성 검증을 담당하는 클래스"""
    
    def __init__(self):
        self.valid_test_results = {"통과", "PASS", "성공", "OK", "적합"}
        self.valid_fail_results = {"실패", "FAIL", "부적합", "NG", "오류"}
        self.test_method_keywords = {"시험", "검증", "확인", "측정", "분석", "평가"}
    
    def validate_accuracy(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """내용 정확성 검증"""
        accuracy_issues = []
        evidence_details = []
        
        # 시험 결과 논리적 일관성 검증
        result_validation = self._validate_test_results_consistency(test_data)
        if not result_validation["valid"]:
            accuracy_issues.extend(result_validation["errors"])
        else:
            evidence_details.extend(result_validation["evidence"])
        
        # 시험 방법 적절성 검증
        method_validation = self._validate_test_methods(test_data)
        if not method_validation["valid"]:
            accuracy_issues.extend(method_validation["errors"])
        else:
            evidence_details.extend(method_validation["evidence"])
        
        # 판정 근거 완전성 검증
        evidence_validation = self._validate_judgment_evidence(test_data)
        if not evidence_validation["valid"]:
            accuracy_issues.extend(evidence_validation["errors"])
        else:
            evidence_details.extend(evidence_validation["evidence"])
        
        # ISO/IEC 24759 표준 요구사항 일치성 확인
        standard_validation = self._validate_standard_compliance(test_data, rule)
        if not standard_validation["valid"]:
            accuracy_issues.extend(standard_validation["errors"])
        else:
            evidence_details.extend(standard_validation["evidence"])
        
        # 결과 판정
        passed = len(accuracy_issues) == 0
        
        if passed:
            message = "시험 결과 내용이 논리적으로 일관되고 ISO/IEC 24759 표준 요구사항을 만족합니다."
        else:
            message = f"내용 정확성 오류: {'; '.join(accuracy_issues)}"
        
        evidence = "; ".join(evidence_details) if evidence_details else None
        
        return ComplianceResult(
            rule_name="content_accuracy",
            passed=passed,
            message=message,
            iso_reference="ISO/IEC 24759:2017 Section 8 - Test Result Content Requirements",
            evidence=evidence
        )
    
    def _validate_test_results_consistency(self, test_data: TestItemData) -> Dict[str, Any]:
        """시험 결과 논리적 일관성 검증"""
        errors = []
        evidence = []
        
        table_data = test_data.table_data
        cells = test_data.cells or []
        
        # 시험 결과 값 추출
        result_values = []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in self.valid_test_results | self.valid_fail_results):
                result_values.append(text)
        
        if not result_values:
            errors.append("명확한 시험 결과 값을 찾을 수 없습니다")
            return {"valid": False, "errors": errors, "evidence": evidence}
        
        # 결과 일관성 확인
        pass_count = sum(1 for result in result_values if any(keyword in result for keyword in self.valid_test_results))
        fail_count = sum(1 for result in result_values if any(keyword in result for keyword in self.valid_fail_results))
        
        if pass_count > 0 and fail_count > 0:
            errors.append(f"시험 결과가 일관되지 않습니다 (통과: {pass_count}, 실패: {fail_count})")
        else:
            if pass_count > 0:
                evidence.append(f"시험 결과: 통과 ({pass_count}개 항목)")
            elif fail_count > 0:
                evidence.append(f"시험 결과: 실패 ({fail_count}개 항목)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_test_methods(self, test_data: TestItemData) -> Dict[str, Any]:
        """시험 방법 적절성 검증"""
        errors = []
        evidence = []
        
        table_data = test_data.table_data
        cells = test_data.cells or []
        
        # 시험 방법 관련 내용 추출
        method_contents = []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in self.test_method_keywords):
                method_contents.append(text)
        
        if not method_contents:
            errors.append("시험 방법에 대한 설명을 찾을 수 없습니다")
        else:
            # 시험 방법 내용 품질 확인
            total_length = sum(len(content) for content in method_contents)
            if total_length < 20:  # 너무 짧은 설명
                errors.append("시험 방법 설명이 너무 간략합니다")
            else:
                evidence.append(f"시험 방법 설명 {len(method_contents)}개 항목 (총 {total_length}자)")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_judgment_evidence(self, test_data: TestItemData) -> Dict[str, Any]:
        """판정 근거 완전성 검증"""
        errors = []
        evidence = []
        
        table_data = test_data.table_data
        cells = test_data.cells or []
        
        # 판정 근거 관련 키워드
        evidence_keywords = {"근거", "이유", "판정", "결론", "분석", "평가"}
        
        # 판정 근거 내용 추출
        evidence_contents = []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in evidence_keywords):
                evidence_contents.append(text)
        
        if not evidence_contents:
            errors.append("시험결과 판정 근거를 찾을 수 없습니다")
        else:
            # 판정 근거 품질 확인
            substantial_evidence = [content for content in evidence_contents if len(content) > 10]
            if len(substantial_evidence) == 0:
                errors.append("실질적인 판정 근거가 부족합니다")
            else:
                evidence.append(f"판정 근거 {len(substantial_evidence)}개 항목")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_standard_compliance(self, test_data: TestItemData, rule: ValidationRule) -> Dict[str, Any]:
        """ISO/IEC 24759 표준 요구사항 일치성 확인"""
        errors = []
        evidence = []
        
        # TE 번호별 특별한 검증 규칙
        te_number = test_data.te_number
        
        if te_number.startswith("TE02.03"):
            # 암호모듈 시험 관련 특별 검증
            crypto_validation = self._validate_crypto_module_requirements(test_data)
            if not crypto_validation["valid"]:
                errors.extend(crypto_validation["errors"])
            else:
                evidence.extend(crypto_validation["evidence"])
        
        # 일반적인 표준 준수 확인
        general_validation = self._validate_general_standard_requirements(test_data, rule)
        if not general_validation["valid"]:
            errors.extend(general_validation["errors"])
        else:
            evidence.extend(general_validation["evidence"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_crypto_module_requirements(self, test_data: TestItemData) -> Dict[str, Any]:
        """암호모듈 시험 특별 요구사항 검증"""
        errors = []
        evidence = []
        
        # 암호모듈 관련 키워드 확인
        crypto_keywords = {"암호", "모듈", "알고리즘", "키", "보안", "인증"}
        
        table_data = test_data.table_data
        cells = test_data.cells or []
        
        crypto_content_found = False
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in crypto_keywords):
                crypto_content_found = True
                break
        
        if not crypto_content_found:
            errors.append("암호모듈 시험에 필요한 암호학적 내용을 찾을 수 없습니다")
        else:
            evidence.append("암호모듈 관련 내용 확인됨")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_general_standard_requirements(self, test_data: TestItemData, rule: ValidationRule) -> Dict[str, Any]:
        """일반적인 표준 요구사항 검증"""
        errors = []
        evidence = []
        
        # 테이블 캡션 확인
        caption = test_data.caption
        if not caption or len(caption.strip()) < 5:
            errors.append("테이블 캡션이 없거나 너무 짧습니다")
        else:
            evidence.append(f"테이블 캡션: {caption[:50]}...")
        
        # 페이지 번호 확인
        if test_data.page_number <= 0:
            errors.append("유효하지 않은 페이지 번호입니다")
        else:
            evidence.append(f"페이지 번호: {test_data.page_number}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }clas
s ElementValidator:
    """필수 요소 존재 여부 검증을 담당하는 클래스"""
    
    def __init__(self):
        self.image_extensions = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".svg"}
        self.diagram_keywords = {"그림", "도표", "다이어그램", "차트", "도식", "Figure"}
    
    def validate_required_elements(self, test_data: TestItemData, rule: ValidationRule) -> ComplianceResult:
        """필수 요소 존재 여부 검증"""
        element_issues = []
        evidence_details = []
        
        # 이미지 및 그림 자료 검증
        if rule.required_images:
            image_validation = self._validate_image_requirements(test_data)
            if not image_validation["valid"]:
                element_issues.extend(image_validation["errors"])
            else:
                evidence_details.extend(image_validation["evidence"])
        else:
            evidence_details.append("이미지 요구사항 없음")
        
        # 시험항목별 필수 구성 요소 검증
        component_validation = self._validate_required_components(test_data, rule)
        if not component_validation["valid"]:
            element_issues.extend(component_validation["errors"])
        else:
            evidence_details.extend(component_validation["evidence"])
        
        # 참조 문서 및 표준 인용 검증
        reference_validation = self._validate_references(test_data, rule)
        if not reference_validation["valid"]:
            element_issues.extend(reference_validation["errors"])
        else:
            evidence_details.extend(reference_validation["evidence"])
        
        # 결과 판정
        passed = len(element_issues) == 0
        
        if passed:
            message = "모든 필수 요소가 적절히 제공되었습니다."
        else:
            message = f"필수 요소 누락: {'; '.join(element_issues)}"
        
        evidence = "; ".join(evidence_details) if evidence_details else None
        
        return ComplianceResult(
            rule_name="required_elements",
            passed=passed,
            message=message,
            iso_reference="ISO/IEC 24759:2017 Section 7.3 - Required Test Documentation Elements",
            evidence=evidence
        )
    
    def _validate_image_requirements(self, test_data: TestItemData) -> Dict[str, Any]:
        """이미지 및 그림 자료 요구사항 검증"""
        errors = []
        evidence = []
        
        # 이미지 데이터 존재 확인
        has_image_data = test_data.has_image and test_data.image_data
        
        if not has_image_data:
            errors.append("필수 이미지 자료가 없습니다")
            return {"valid": False, "errors": errors, "evidence": evidence}
        
        # 이미지 데이터 품질 확인
        image_data = test_data.image_data
        image_validation = self._validate_image_data_quality(image_data)
        
        if not image_validation["valid"]:
            errors.extend(image_validation["errors"])
        else:
            evidence.extend(image_validation["evidence"])
        
        # 테이블 내 이미지 참조 확인
        reference_validation = self._validate_image_references(test_data)
        if not reference_validation["valid"]:
            errors.extend(reference_validation["errors"])
        else:
            evidence.extend(reference_validation["evidence"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_image_data_quality(self, image_data: Dict[str, Any]) -> Dict[str, Any]:
        """이미지 데이터 품질 검증"""
        errors = []
        evidence = []
        
        if not image_data:
            errors.append("이미지 데이터가 비어있습니다")
            return {"valid": False, "errors": errors, "evidence": evidence}
        
        # 이미지 파일 정보 확인
        image_files = image_data.get("files", [])
        if not image_files:
            errors.append("이미지 파일 정보가 없습니다")
        else:
            valid_images = 0
            for img_file in image_files:
                if isinstance(img_file, str):
                    # 파일 확장자 확인
                    if any(img_file.lower().endswith(ext) for ext in self.image_extensions):
                        valid_images += 1
                elif isinstance(img_file, dict):
                    # 이미지 메타데이터 확인
                    if img_file.get("type") in ["image", "figure", "diagram"]:
                        valid_images += 1
            
            if valid_images == 0:
                errors.append("유효한 이미지 파일이 없습니다")
            else:
                evidence.append(f"유효한 이미지 {valid_images}개")
        
        # 이미지 설명 확인
        descriptions = image_data.get("descriptions", [])
        if descriptions:
            evidence.append(f"이미지 설명 {len(descriptions)}개")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_image_references(self, test_data: TestItemData) -> Dict[str, Any]:
        """테이블 내 이미지 참조 검증"""
        errors = []
        evidence = []
        
        cells = test_data.cells or []
        
        # 이미지 참조 키워드 검색
        image_references = []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in self.diagram_keywords):
                image_references.append(text)
        
        if not image_references:
            errors.append("테이블에서 이미지 참조를 찾을 수 없습니다")
        else:
            evidence.append(f"이미지 참조 {len(image_references)}개")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_required_components(self, test_data: TestItemData, rule: ValidationRule) -> Dict[str, Any]:
        """시험항목별 필수 구성 요소 검증"""
        errors = []
        evidence = []
        
        te_number = test_data.te_number
        
        # TE 번호별 특별 요구사항
        if te_number == "TE02.03.01":
            # 암호모듈 기본 시험 요구사항
            basic_validation = self._validate_basic_crypto_components(test_data)
            if not basic_validation["valid"]:
                errors.extend(basic_validation["errors"])
            else:
                evidence.extend(basic_validation["evidence"])
        
        elif te_number == "TE02.03.02":
            # 인터페이스 시험 요구사항
            interface_validation = self._validate_interface_components(test_data)
            if not interface_validation["valid"]:
                errors.extend(interface_validation["errors"])
            else:
                evidence.extend(interface_validation["evidence"])
        
        elif te_number == "TE02.03.03":
            # 역할 및 서비스 시험 요구사항
            service_validation = self._validate_service_components(test_data)
            if not service_validation["valid"]:
                errors.extend(service_validation["errors"])
            else:
                evidence.extend(service_validation["evidence"])
        
        # 공통 요구사항 검증
        common_validation = self._validate_common_components(test_data)
        if not common_validation["valid"]:
            errors.extend(common_validation["errors"])
        else:
            evidence.extend(common_validation["evidence"])
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_basic_crypto_components(self, test_data: TestItemData) -> Dict[str, Any]:
        """기본 암호모듈 구성 요소 검증"""
        errors = []
        evidence = []
        
        required_components = ["암호모듈", "알고리즘", "키", "보안"]
        found_components = []
        
        cells = test_data.cells or []
        all_text = " ".join([cell.get("text", "") for cell in cells])
        
        for component in required_components:
            if component in all_text:
                found_components.append(component)
        
        missing_components = set(required_components) - set(found_components)
        if missing_components:
            errors.append(f"필수 암호모듈 구성 요소 누락: {', '.join(missing_components)}")
        else:
            evidence.append(f"암호모듈 구성 요소 확인: {', '.join(found_components)}")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_interface_components(self, test_data: TestItemData) -> Dict[str, Any]:
        """인터페이스 구성 요소 검증"""
        errors = []
        evidence = []
        
        interface_keywords = ["인터페이스", "API", "포트", "연결", "통신"]
        found_interfaces = []
        
        cells = test_data.cells or []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in interface_keywords):
                found_interfaces.append(text[:30])  # 처음 30자만
        
        if not found_interfaces:
            errors.append("인터페이스 관련 내용을 찾을 수 없습니다")
        else:
            evidence.append(f"인터페이스 관련 내용 {len(found_interfaces)}개")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_service_components(self, test_data: TestItemData) -> Dict[str, Any]:
        """서비스 구성 요소 검증"""
        errors = []
        evidence = []
        
        service_keywords = ["서비스", "역할", "인증", "권한", "기능"]
        found_services = []
        
        cells = test_data.cells or []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in service_keywords):
                found_services.append(text[:30])  # 처음 30자만
        
        if not found_services:
            errors.append("서비스/역할 관련 내용을 찾을 수 없습니다")
        else:
            evidence.append(f"서비스/역할 관련 내용 {len(found_services)}개")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_common_components(self, test_data: TestItemData) -> Dict[str, Any]:
        """공통 구성 요소 검증"""
        errors = []
        evidence = []
        
        # 테이블 기본 구조 확인
        if not test_data.table_data:
            errors.append("테이블 데이터가 없습니다")
        else:
            evidence.append("테이블 데이터 존재")
        
        # 셀 데이터 확인
        cells = test_data.cells or []
        if len(cells) < 2:
            errors.append("테이블 셀이 부족합니다")
        else:
            evidence.append(f"테이블 셀 {len(cells)}개")
        
        return {
            "valid": len(errors) == 0,
            "errors": errors,
            "evidence": evidence
        }
    
    def _validate_references(self, test_data: TestItemData, rule: ValidationRule) -> Dict[str, Any]:
        """참조 문서 및 표준 인용 검증"""
        errors = []
        evidence = []
        
        # ISO 표준 참조 확인
        iso_references = rule.iso_references
        if iso_references:
            evidence.append(f"ISO 참조 {len(iso_references)}개")
        
        # 테이블 내 참조 문헌 확인
        cells = test_data.cells or []
        reference_keywords = ["참조", "표준", "규격", "ISO", "IEC", "FIPS"]
        
        found_references = []
        for cell in cells:
            text = cell.get("text", "").strip()
            if text and any(keyword in text for keyword in reference_keywords):
                found_references.append(text[:50])  # 처음 50자만
        
        if found_references:
            evidence.append(f"참조 문헌 {len(found_references)}개")
        
        return {
            "valid": True,  # 참조는 선택사항으로 처리
            "errors": errors,
            "evidence": evidence
        }#
 ============================================================================
# 시험항목 데이터 추출기
# ============================================================================

class TestItemExtractor:
    """시험항목 데이터 추출을 담당하는 클래스"""
    
    def __init__(self, json_validator):
        """
        TestItemExtractor 초기화
        
        Args:
            json_validator (JSONValidator): 기존 JSONValidator 인스턴스
        """
        if json_validator is None:
            raise ValueError("JSONValidator 인스턴스가 필요합니다.")
        
        self.json_validator = json_validator
        self.logger = logger
    
    def extract_test_item_data(self, te_number: str) -> TestItemData:
        """
        TE 번호로 시험항목 데이터 추출
        
        Args:
            te_number (str): 시험항목 번호 (예: "TE02.03.01")
            
        Returns:
            TestItemData: 추출된 시험항목 데이터
            
        Raises:
            TestItemNotFoundError: 시험항목을 찾을 수 없는 경우
            ValidationError: 데이터 추출 중 오류 발생
        """
        try:
            if not te_number or not isinstance(te_number, str):
                raise TestItemNotFoundError(te_number, "유효하지 않은 TE 번호입니다.")
            
            te_number = te_number.strip()
            self.logger.info(f"시험항목 데이터 추출 시작: {te_number}")
            
            # JSONValidator를 사용하여 테이블 정보 검색
            table_info = self.json_validator.find_test_result_table(te_number)
            if not table_info:
                raise TestItemNotFoundError(
                    te_number, 
                    f"시험항목 '{te_number}'에 해당하는 시험결과판정근거 테이블을 찾을 수 없습니다."
                )
            
            # 테이블 데이터 추출
            table_data_info = self.json_validator.get_test_result_table_data(te_number)
            if not table_data_info:
                raise TestItemNotFoundError(
                    te_number,
                    f"시험항목 '{te_number}'의 테이블 데이터를 추출할 수 없습니다."
                )
            
            # TestItemData 객체 생성
            test_item_data = self._create_test_item_data(te_number, table_info, table_data_info)
            
            self.logger.info(f"시험항목 데이터 추출 완료: {te_number}")
            return test_item_data
            
        except TestItemNotFoundError:
            raise
        except Exception as e:
            self.logger.error(f"시험항목 데이터 추출 중 오류: {str(e)}")
            raise ValidationError(f"시험항목 '{te_number}' 데이터 추출 실패: {str(e)}")
    
    def _create_test_item_data(self, te_number: str, table_info: Dict[str, Any], table_data_info: Dict[str, Any]) -> TestItemData:
        """TestItemData 객체 생성"""
        try:
            # 기본 정보 추출
            page_number = table_info.get("page_number", 0)
            table_data = table_info.get("table_data", {})
            
            # 메타데이터 추출
            metadata = self._extract_metadata(table_data, table_data_info)
            
            # 이미지 정보 확인
            has_image = table_data_info.get("has_image", False)
            image_data = table_data_info.get("image_data") if has_image else None
            
            # 셀 데이터 추출
            cells = self._extract_cells_data(table_data_info)
            
            # 캡션 추출
            caption = table_data_info.get("caption", "") or table_data.get("caption", "")
            
            return TestItemData(
                te_number=te_number,
                page_number=page_number,
                table_data=table_data,
                metadata=metadata,
                has_image=has_image,
                image_data=image_data,
                cells=cells,
                caption=caption
            )
            
        except Exception as e:
            self.logger.error(f"TestItemData 생성 중 오류: {str(e)}")
            raise ValidationError(f"TestItemData 생성 실패: {str(e)}")
    
    def _extract_metadata(self, table_data: Dict[str, Any], table_data_info: Dict[str, Any]) -> Dict[str, Any]:
        """메타데이터 추출"""
        metadata = {}
        
        try:
            # JSON 데이터에서 전역 메타데이터 추출
            if hasattr(self.json_validator, 'json_data') and self.json_validator.json_data:
                json_data = self.json_validator.json_data
                
                # 파일 경로에서 정보 추출
                file_path = json_data.get("file_path", "")
                if file_path:
                    metadata["source_file"] = file_path
                
                # 문서 메타데이터 추출
                doc_metadata = json_data.get("metadata", {})
                if doc_metadata:
                    metadata.update(doc_metadata)
                
                # 페이지별 메타데이터 추출
                pages = json_data.get("pages", [])
                if pages and len(pages) > 0:
                    first_page = pages[0]
                    if isinstance(first_page, dict):
                        page_metadata = first_page.get("metadata", {})
                        if page_metadata:
                            metadata.update(page_metadata)
            
            # 테이블 데이터에서 메타데이터 추출
            if table_data:
                table_metadata = table_data.get("metadata", {})
                if table_metadata:
                    metadata.update(table_metadata)
            
            # 셀 데이터에서 메타데이터 추출 시도
            cells = table_data_info.get("cells", [])
            if cells:
                extracted_metadata = self._extract_metadata_from_cells(cells)
                metadata.update(extracted_metadata)
            
            # 기본값 설정
            if "CM_name" not in metadata:
                metadata["CM_name"] = self._extract_cm_name_from_cells(cells) or ""
            
            if "version" not in metadata:
                metadata["version"] = self._extract_version_from_cells(cells) or ""
            
            if "date" not in metadata:
                metadata["date"] = self._extract_date_from_cells(cells) or ""
            
            if "test_organization" not in metadata:
                metadata["test_organization"] = self._extract_test_org_from_cells(cells) or ""
            
            return metadata
            
        except Exception as e:
            self.logger.warning(f"메타데이터 추출 중 오류: {str(e)}")
            return {}
    
    def _extract_metadata_from_cells(self, cells: List[Dict[str, Any]]) -> Dict[str, Any]:
        """셀 데이터에서 메타데이터 추출"""
        metadata = {}
        
        if not cells:
            return metadata
        
        # 셀 텍스트를 하나의 문자열로 결합
        all_text = " ".join([cell.get("text", "") for cell in cells if cell.get("text")])
        
        # 정규식을 사용한 패턴 매칭
        patterns = {
            "CM_name": [
                r"암호모듈명?\s*[:：]\s*([^\s\n]+)",
                r"모듈명?\s*[:：]\s*([^\s\n]+)",
                r"제품명?\s*[:：]\s*([^\s\n]+)"
            ],
            "version": [
                r"버전\s*[:：]\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
                r"Version\s*[:：]\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)",
                r"v\.?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)"
            ],
            "date": [
                r"시험일자?\s*[:：]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})",
                r"날짜\s*[:：]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})",
                r"Date\s*[:：]\s*([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})"
            ],
            "test_organization": [
                r"시험기관\s*[:：]\s*([^\n]+)",
                r"검증기관\s*[:：]\s*([^\n]+)",
                r"Test\s+Organization\s*[:：]\s*([^\n]+)"
            ]
        }
        
        import re
        for key, pattern_list in patterns.items():
            for pattern in pattern_list:
                match = re.search(pattern, all_text)
                if match:
                    metadata[key] = match.group(1).strip()
                    break
        
        return metadata
    
    def _extract_cm_name_from_cells(self, cells: List[Dict[str, Any]]) -> Optional[str]:
        """셀에서 암호모듈명 추출"""
        if not cells:
            return None
        
        for cell in cells:
            text = cell.get("text", "").strip()
            if "암호모듈" in text and len(text) > 5:
                # 암호모듈명이 포함된 셀에서 실제 이름 추출
                parts = text.split()
                for part in parts:
                    if len(part) > 3 and "암호모듈" not in part:
                        return part
        
        return None
    
    def _extract_version_from_cells(self, cells: List[Dict[str, Any]]) -> Optional[str]:
        """셀에서 버전 정보 추출"""
        if not cells:
            return None
        
        import re
        version_pattern = r"[vV]?\.?\s*([0-9]+\.[0-9]+(?:\.[0-9]+)?)"
        
        for cell in cells:
            text = cell.get("text", "").strip()
            match = re.search(version_pattern, text)
            if match:
                return match.group(1)
        
        return None
    
    def _extract_date_from_cells(self, cells: List[Dict[str, Any]]) -> Optional[str]:
        """셀에서 날짜 정보 추출"""
        if not cells:
            return None
        
        import re
        date_pattern = r"([0-9]{4}[-/][0-9]{1,2}[-/][0-9]{1,2})"
        
        for cell in cells:
            text = cell.get("text", "").strip()
            match = re.search(date_pattern, text)
            if match:
                # 날짜 형식 정규화 (YYYY-MM-DD)
                date_str = match.group(1).replace("/", "-")
                return date_str
        
        return None
    
    def _extract_test_org_from_cells(self, cells: List[Dict[str, Any]]) -> Optional[str]:
        """셀에서 시험기관 정보 추출"""
        if not cells:
            return None
        
        org_keywords = ["시험기관", "검증기관", "기관", "연구소", "센터"]
        
        for cell in cells:
            text = cell.get("text", "").strip()
            if any(keyword in text for keyword in org_keywords) and len(text) > 5:
                # 기관명이 포함된 셀에서 실제 기관명 추출
                for keyword in org_keywords:
                    if keyword in text:
                        parts = text.split(keyword)
                        if len(parts) > 1:
                            org_name = parts[1].strip().split()[0] if parts[1].strip() else ""
                            if org_name:
                                return org_name + keyword
        
        return None
    
    def _extract_cells_data(self, table_data_info: Dict[str, Any]) -> List[Dict[str, Any]]:
        """셀 데이터 추출 및 정규화"""
        cells = table_data_info.get("cells", [])
        if not cells:
            return []
        
        normalized_cells = []
        
        for cell in cells:
            if not isinstance(cell, dict):
                continue
            
            # 셀 데이터 정규화
            normalized_cell = {
                "row": cell.get("row_idx", cell.get("row", 0)),
                "col": cell.get("col_idx", cell.get("col", 0)),
                "text": cell.get("text", "").strip(),
                "type": self._determine_cell_type(cell)
            }
            
            # 추가 속성 보존
            for key in ["colspan", "rowspan", "style", "alignment"]:
                if key in cell:
                    normalized_cell[key] = cell[key]
            
            normalized_cells.append(normalized_cell)
        
        return normalized_cells
    
    def _determine_cell_type(self, cell: Dict[str, Any]) -> str:
        """셀 타입 결정 (header, data, etc.)"""
        text = cell.get("text", "").strip()
        row = cell.get("row_idx", cell.get("row", 0))
        
        # 첫 번째 행은 일반적으로 헤더
        if row == 0:
            return "header"
        
        # 특정 키워드가 있으면 헤더로 판단
        header_keywords = ["시험결과판정근거", "시험방법", "시험결과", "항목", "내용"]
        if any(keyword in text for keyword in header_keywords):
            return "header"
        
        # 그 외는 데이터 셀
        return "data"
    
    def get_available_te_numbers(self) -> List[str]:
        """사용 가능한 TE 번호 목록 반환"""
        try:
            if not hasattr(self.json_validator, 'json_data') or not self.json_validator.json_data:
                return []
            
            te_numbers = []
            pages = self.json_validator.json_data.get("pages", [])
            
            import re
            te_pattern = r"TE\d{2}\.\d{2}\.\d{2}"
            
            for page in pages:
                if not isinstance(page, dict):
                    continue
                
                # 테이블에서 TE 번호 검색
                tables = page.get("tables", [])
                for table in tables:
                    if not isinstance(table, dict):
                        continue
                    
                    # 캡션에서 검색
                    caption = table.get("caption", "")
                    if caption:
                        matches = re.findall(te_pattern, caption)
                        te_numbers.extend(matches)
                    
                    # 셀에서 검색
                    cells = table.get("cells", [])
                    for cell in cells:
                        if isinstance(cell, dict):
                            text = cell.get("text", "")
                            if text:
                                matches = re.findall(te_pattern, text)
                                te_numbers.extend(matches)
                
                # 텍스트 블록에서 검색
                text_blocks = page.get("text_blocks", [])
                for block in text_blocks:
                    if isinstance(block, dict):
                        text = block.get("text", "")
                        if text:
                            matches = re.findall(te_pattern, text)
                            te_numbers.extend(matches)
            
            # 중복 제거 및 정렬
            unique_te_numbers = sorted(list(set(te_numbers)))
            self.logger.info(f"발견된 TE 번호: {unique_te_numbers}")
            
            return unique_te_numbers
            
        except Exception as e:
            self.logger.error(f"TE 번호 목록 추출 중 오류: {str(e)}")
            return []
    
    def validate_te_number_format(self, te_number: str) -> bool:
        """TE 번호 형식 유효성 검증"""
        if not te_number or not isinstance(te_number, str):
            return False
        
        import re
        pattern = r"^TE\d{2}\.\d{2}\.\d{2}$"
        return bool(re.match(pattern, te_number.strip()))# =====
=======================================================================
# 검증 결과 포맷터
# ============================================================================

class ValidationResultFormatter:
    """검증 결과를 다양한 형식으로 포맷팅하는 클래스"""
    
    def __init__(self):
        self.logger = logger
    
    def format_single_result(self, result: ValidationResult, format_type: str = "text") -> str:
        """
        단일 검증 결과를 지정된 형식으로 포맷팅
        
        Args:
            result (ValidationResult): 검증 결과
            format_type (str): 출력 형식 ("text", "json", "html", "markdown")
            
        Returns:
            str: 포맷팅된 결과
        """
        try:
            if format_type.lower() == "json":
                return self._format_json(result)
            elif format_type.lower() == "html":
                return self._format_html(result)
            elif format_type.lower() == "markdown":
                return self._format_markdown(result)
            else:  # default to text
                return self._format_text(result)
                
        except Exception as e:
            self.logger.error(f"결과 포맷팅 중 오류: {str(e)}")
            return f"포맷팅 오류: {str(e)}"
    
    def format_multiple_results(self, results: List[ValidationResult], format_type: str = "text") -> str:
        """
        다중 검증 결과를 지정된 형식으로 포맷팅
        
        Args:
            results (List[ValidationResult]): 검증 결과 목록
            format_type (str): 출력 형식
            
        Returns:
            str: 포맷팅된 결과
        """
        try:
            if not results:
                return "검증 결과가 없습니다."
            
            if format_type.lower() == "json":
                return self._format_multiple_json(results)
            elif format_type.lower() == "html":
                return self._format_multiple_html(results)
            elif format_type.lower() == "markdown":
                return self._format_multiple_markdown(results)
            else:  # default to text
                return self._format_multiple_text(results)
                
        except Exception as e:
            self.logger.error(f"다중 결과 포맷팅 중 오류: {str(e)}")
            return f"포맷팅 오류: {str(e)}"
    
    def _format_text(self, result: ValidationResult) -> str:
        """텍스트 형식으로 포맷팅"""
        lines = []
        lines.append("=" * 60)
        lines.append(f"시험항목명: {result.test_item_name}")
        lines.append(f"TE 번호: {result.te_number}")
        lines.append(f"검토결과: {result.status.value}")
        lines.append("-" * 40)
        
        if result.reasons:
            lines.append("이유 및 근거:")
            for i, reason in enumerate(result.reasons, 1):
                lines.append(f"  {i}. {reason}")
        
        if result.evidence:
            lines.append("\n증거 자료:")
            for i, evidence in enumerate(result.evidence, 1):
                lines.append(f"  {i}. {evidence}")
        
        if result.iso_references:
            lines.append("\nISO/IEC 24759 참조:")
            for i, ref in enumerate(result.iso_references, 1):
                lines.append(f"  {i}. {ref}")
        
        lines.append(f"\n검증 시간: {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        
        return "\n".join(lines)
    
    def _format_json(self, result: ValidationResult) -> str:
        """JSON 형식으로 포맷팅"""
        return result.to_json()
    
    def _format_html(self, result: ValidationResult) -> str:
        """HTML 형식으로 포맷팅"""
        status_color = "#28a745" if result.status == ValidationStatus.PASS else "#dc3545"
        status_icon = "✓" if result.status == ValidationStatus.PASS else "✗"
        
        html = f"""
        <div class="validation-result" style="border: 1px solid #ddd; padding: 15px; margin: 10px 0; border-radius: 5px;">
            <h3 style="color: {status_color}; margin-top: 0;">
                {status_icon} {result.test_item_name}
            </h3>
            <table style="width: 100%; border-collapse: collapse;">
                <tr>
                    <td style="font-weight: bold; padding: 5px; border-bottom: 1px solid #eee;">TE 번호:</td>
                    <td style="padding: 5px; border-bottom: 1px solid #eee;">{result.te_number}</td>
                </tr>
                <tr>
                    <td style="font-weight: bold; padding: 5px; border-bottom: 1px solid #eee;">검토결과:</td>
                    <td style="padding: 5px; border-bottom: 1px solid #eee; color: {status_color}; font-weight: bold;">
                        {result.status.value}
                    </td>
                </tr>
        """
        
        if result.reasons:
            html += """
                <tr>
                    <td style="font-weight: bold; padding: 5px; border-bottom: 1px solid #eee; vertical-align: top;">이유 및 근거:</td>
                    <td style="padding: 5px; border-bottom: 1px solid #eee;">
                        <ul style="margin: 0; padding-left: 20px;">
            """
            for reason in result.reasons:
                html += f"<li>{reason}</li>"
            html += "</ul></td></tr>"
        
        if result.evidence:
            html += """
                <tr>
                    <td style="font-weight: bold; padding: 5px; border-bottom: 1px solid #eee; vertical-align: top;">증거 자료:</td>
                    <td style="padding: 5px; border-bottom: 1px solid #eee;">
                        <ul style="margin: 0; padding-left: 20px;">
            """
            for evidence in result.evidence:
                html += f"<li>{evidence}</li>"
            html += "</ul></td></tr>"
        
        if result.iso_references:
            html += """
                <tr>
                    <td style="font-weight: bold; padding: 5px; border-bottom: 1px solid #eee; vertical-align: top;">ISO 참조:</td>
                    <td style="padding: 5px; border-bottom: 1px solid #eee;">
                        <ul style="margin: 0; padding-left: 20px;">
            """
            for ref in result.iso_references:
                html += f"<li>{ref}</li>"
            html += "</ul></td></tr>"
        
        html += f"""
                <tr>
                    <td style="font-weight: bold; padding: 5px;">검증 시간:</td>
                    <td style="padding: 5px;">{result.timestamp.strftime('%Y-%m-%d %H:%M:%S')}</td>
                </tr>
            </table>
        </div>
        """
        
        return html
    
    def _format_markdown(self, result: ValidationResult) -> str:
        """Markdown 형식으로 포맷팅"""
        status_emoji = "✅" if result.status == ValidationStatus.PASS else "❌"
        
        md = f"""
## {status_emoji} {result.test_item_name}

| 항목 | 내용 |
|------|------|
| **TE 번호** | {result.te_number} |
| **검토결과** | **{result.status.value}** |
"""
        
        if result.reasons:
            md += "| **이유 및 근거** | "
            reasons_text = "<br>".join([f"• {reason}" for reason in result.reasons])
            md += f"{reasons_text} |\n"
        
        if result.evidence:
            md += "| **증거 자료** | "
            evidence_text = "<br>".join([f"• {evidence}" for evidence in result.evidence])
            md += f"{evidence_text} |\n"
        
        if result.iso_references:
            md += "| **ISO 참조** | "
            ref_text = "<br>".join([f"• {ref}" for ref in result.iso_references])
            md += f"{ref_text} |\n"
        
        md += f"| **검증 시간** | {result.timestamp.strftime('%Y-%m-%d %H:%M:%S')} |\n"
        
        return md
    
    def _format_multiple_text(self, results: List[ValidationResult]) -> str:
        """다중 결과 텍스트 형식 포맷팅"""
        lines = []
        lines.append("ISO/IEC 24759 검증 결과 보고서")
        lines.append("=" * 60)
        lines.append(f"총 검증 항목: {len(results)}개")
        
        pass_count = sum(1 for r in results if r.status == ValidationStatus.PASS)
        fail_count = len(results) - pass_count
        
        lines.append(f"통과: {pass_count}개, 실패: {fail_count}개")
        lines.append(f"검증 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        lines.append("=" * 60)
        lines.append("")
        
        for i, result in enumerate(results, 1):
            lines.append(f"[{i}] {self._format_text(result)}")
            lines.append("")
        
        return "\n".join(lines)
    
    def _format_multiple_json(self, results: List[ValidationResult]) -> str:
        """다중 결과 JSON 형식 포맷팅"""
        report = {
            "report_info": {
                "title": "ISO/IEC 24759 검증 결과 보고서",
                "total_items": len(results),
                "pass_count": sum(1 for r in results if r.status == ValidationStatus.PASS),
                "fail_count": sum(1 for r in results if r.status == ValidationStatus.FAIL),
                "generated_at": datetime.now().isoformat()
            },
            "results": [result.to_dict() for result in results]
        }
        
        return json.dumps(report, ensure_ascii=False, indent=2)
    
    def _format_multiple_html(self, results: List[ValidationResult]) -> str:
        """다중 결과 HTML 형식 포맷팅"""
        pass_count = sum(1 for r in results if r.status == ValidationStatus.PASS)
        fail_count = len(results) - pass_count
        
        html = f"""
        <!DOCTYPE html>
        <html lang="ko">
        <head>
            <meta charset="UTF-8">
            <meta name="viewport" content="width=device-width, initial-scale=1.0">
            <title>ISO/IEC 24759 검증 결과 보고서</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                .header {{ background-color: #f8f9fa; padding: 20px; border-radius: 5px; margin-bottom: 20px; }}
                .summary {{ display: flex; gap: 20px; margin-bottom: 20px; }}
                .summary-item {{ padding: 15px; border-radius: 5px; text-align: center; flex: 1; }}
                .pass {{ background-color: #d4edda; color: #155724; }}
                .fail {{ background-color: #f8d7da; color: #721c24; }}
                .total {{ background-color: #d1ecf1; color: #0c5460; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>ISO/IEC 24759 검증 결과 보고서</h1>
                <p>생성 시간: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="summary">
                <div class="summary-item total">
                    <h3>{len(results)}</h3>
                    <p>총 검증 항목</p>
                </div>
                <div class="summary-item pass">
                    <h3>{pass_count}</h3>
                    <p>통과</p>
                </div>
                <div class="summary-item fail">
                    <h3>{fail_count}</h3>
                    <p>실패</p>
                </div>
            </div>
            
            <div class="results">
        """
        
        for result in results:
            html += self._format_html(result)
        
        html += """
            </div>
        </body>
        </html>
        """
        
        return html
    
    def _format_multiple_markdown(self, results: List[ValidationResult]) -> str:
        """다중 결과 Markdown 형식 포맷팅"""
        pass_count = sum(1 for r in results if r.status == ValidationStatus.PASS)
        fail_count = len(results) - pass_count
        
        md = f"""# ISO/IEC 24759 검증 결과 보고서

## 검증 요약

| 항목 | 개수 |
|------|------|
| 총 검증 항목 | {len(results)} |
| 통과 | {pass_count} |
| 실패 | {fail_count} |
| 생성 시간 | {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} |

## 상세 결과

"""
        
        for i, result in enumerate(results, 1):
            md += f"### {i}. {result.test_item_name}\n\n"
            md += self._format_markdown(result)
            md += "\n---\n\n"
        
        return md
    
    def create_summary_report(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """검증 결과 요약 보고서 생성"""
        if not results:
            return {
                "total_items": 0,
                "pass_count": 0,
                "fail_count": 0,
                "pass_rate": 0.0,
                "summary": "검증 결과가 없습니다."
            }
        
        pass_count = sum(1 for r in results if r.status == ValidationStatus.PASS)
        fail_count = len(results) - pass_count
        pass_rate = (pass_count / len(results)) * 100 if results else 0
        
        # 실패 이유 분석
        failure_reasons = {}
        for result in results:
            if result.status == ValidationStatus.FAIL:
                for reason in result.reasons:
                    failure_reasons[reason] = failure_reasons.get(reason, 0) + 1
        
        # 가장 많은 실패 이유
        top_failure_reasons = sorted(failure_reasons.items(), key=lambda x: x[1], reverse=True)[:5]
        
        return {
            "total_items": len(results),
            "pass_count": pass_count,
            "fail_count": fail_count,
            "pass_rate": round(pass_rate, 2),
            "top_failure_reasons": top_failure_reasons,
            "generated_at": datetime.now().isoformat(),
            "summary": f"총 {len(results)}개 항목 중 {pass_count}개 통과 ({pass_rate:.1f}%)"
        }
    
    def save_results_to_file(self, results: List[ValidationResult], file_path: str, format_type: str = "text"):
        """검증 결과를 파일로 저장"""
        try:
            if isinstance(results, ValidationResult):
                content = self.format_single_result(results, format_type)
            else:
                content = self.format_multiple_results(results, format_type)
            
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
            
            self.logger.info(f"검증 결과가 파일에 저장되었습니다: {file_path}")
            return True
            
        except Exception as e:
            self.logger.error(f"파일 저장 중 오류: {str(e)}")
            return False#
 ============================================================================
# ISO24759 메인 검증기
# ============================================================================

class ISO24759Validator:
    """
    ISO/IEC 24759 표준 기반 CMVP 시험결과보고서 검증 시스템의 메인 클래스
    
    이 클래스는 MR(Machine Readable) 보고서의 정확성과 완전성을 
    ISO/IEC 24759 국제표준에 따라 자동으로 검증합니다.
    """
    
    def __init__(self, json_validator, config_path: str = None):
        """
        ISO24759Validator 초기화
        
        Args:
            json_validator (JSONValidator): 기존 JSONValidator 인스턴스
            config_path (str, optional): 검증 규칙 설정 파일 경로
        """
        try:
            # 의존성 검증
            if json_validator is None:
                raise ValueError("JSONValidator 인스턴스가 필요합니다.")
            
            # 핵심 컴포넌트 초기화
            self.json_validator = json_validator
            self.rule_engine = ValidationRuleEngine(config_path)
            self.compliance_checker = ComplianceChecker()
            self.test_item_extractor = TestItemExtractor(json_validator)
            self.result_formatter = ValidationResultFormatter()
            
            # 설정 및 상태 관리
            self.config_path = config_path
            self.logger = logger
            self.validation_history = []
            self.is_initialized = False
            
            # 초기화 수행
            self._initialize_system()
            
            self.logger.info("ISO24759Validator가 성공적으로 초기화되었습니다.")
            
        except Exception as e:
            self.logger.error(f"ISO24759Validator 초기화 실패: {str(e)}")
            raise ValidationError(f"시스템 초기화 실패: {str(e)}")
    
    def _initialize_system(self):
        """시스템 초기화 및 설정 로드"""
        try:
            # 검증 규칙 로드
            self.logger.info("검증 규칙을 로드하는 중...")
            rules = self.rule_engine.get_all_rules()
            self.logger.info(f"검증 규칙 {len(rules)}개가 로드되었습니다.")
            
            # 규칙 유효성 검증
            validation_errors = self.rule_engine.validate_all_rules()
            if validation_errors:
                self.logger.warning(f"규칙 유효성 오류 {len(validation_errors)}개 발견")
                for te_number, errors in validation_errors.items():
                    self.logger.warning(f"규칙 '{te_number}': {', '.join(errors)}")
            
            # JSON 데이터 유효성 확인
            if not hasattr(self.json_validator, 'json_data') or self.json_validator.json_data is None:
                self.logger.warning("JSON 데이터가 로드되지 않았습니다. load_json_file()을 먼저 호출하세요.")
            
            self.is_initialized = True
            
        except Exception as e:
            self.logger.error(f"시스템 초기화 중 오류: {str(e)}")
            raise
    
    def get_system_status(self) -> Dict[str, Any]:
        """시스템 상태 정보 반환"""
        try:
            json_data_status = "로드됨" if (
                hasattr(self.json_validator, 'json_data') and 
                self.json_validator.json_data is not None
            ) else "미로드"
            
            available_te_numbers = self.test_item_extractor.get_available_te_numbers()
            
            return {
                "initialized": self.is_initialized,
                "json_data_status": json_data_status,
                "available_te_numbers": available_te_numbers,
                "available_te_count": len(available_te_numbers),
                "rule_engine_status": self.rule_engine.get_engine_status(),
                "validation_history_count": len(self.validation_history),
                "config_path": self.config_path
            }
            
        except Exception as e:
            self.logger.error(f"시스템 상태 조회 중 오류: {str(e)}")
            return {"error": str(e)}
    
    def reload_configuration(self) -> bool:
        """설정 및 규칙 재로드"""
        try:
            self.logger.info("설정을 재로드하는 중...")
            
            # 규칙 엔진 재로드
            success = self.rule_engine.reload_rules()
            if success:
                self.logger.info("설정 재로드가 완료되었습니다.")
                return True
            else:
                self.logger.error("설정 재로드에 실패했습니다.")
                return False
                
        except Exception as e:
            self.logger.error(f"설정 재로드 중 오류: {str(e)}")
            return False
    
    def get_available_te_numbers(self) -> List[str]:
        """사용 가능한 TE 번호 목록 반환"""
        try:
            return self.test_item_extractor.get_available_te_numbers()
        except Exception as e:
            self.logger.error(f"TE 번호 목록 조회 중 오류: {str(e)}")
            return []
    
    def get_validation_history(self, limit: int = 50) -> List[Dict[str, Any]]:
        """검증 이력 반환"""
        try:
            history = self.validation_history[-limit:] if limit > 0 else self.validation_history
            return [
                {
                    "te_number": item["te_number"],
                    "status": item["status"],
                    "timestamp": item["timestamp"],
                    "duration": item.get("duration", 0)
                }
                for item in history
            ]
        except Exception as e:
            self.logger.error(f"검증 이력 조회 중 오류: {str(e)}")
            return []
    
    def clear_validation_history(self):
        """검증 이력 초기화"""
        self.validation_history.clear()
        self.logger.info("검증 이력이 초기화되었습니다.")
    
    def _add_to_history(self, te_number: str, status: str, duration: float = 0):
        """검증 이력에 항목 추가"""
        history_item = {
            "te_number": te_number,
            "status": status,
            "timestamp": datetime.now().isoformat(),
            "duration": duration
        }
        
        self.validation_history.append(history_item)
        
        # 이력 크기 제한 (최근 1000개만 유지)
        if len(self.validation_history) > 1000:
            self.validation_history = self.validation_history[-1000:] 
   def validate_test_item(self, te_number: str) -> ValidationResult:
        """
        TE 번호에 대한 ISO/IEC 24759 표준 준수 검증
        
        Args:
            te_number (str): 검증할 TE 번호 (예: "TE02.03.01")
            
        Returns:
            ValidationResult: 검증 결과
            
        Raises:
            TestItemNotFoundError: 시험항목을 찾을 수 없는 경우
            ValidationError: 검증 중 오류 발생
        """
        start_time = datetime.now()
        
        try:
            # 시스템 초기화 확인
            if not self.is_initialized:
                raise ValidationError("시스템이 초기화되지 않았습니다.")
            
            # TE 번호 형식 검증
            if not self.test_item_extractor.validate_te_number_format(te_number):
                raise TestItemNotFoundError(te_number, "TE 번호 형식이 올바르지 않습니다.")
            
            self.logger.info(f"시험항목 검증 시작: {te_number}")
            
            # 1. 검증 규칙 조회
            rule = self.rule_engine.get_rules_for_test_item(te_number)
            if not rule:
                raise TestItemNotFoundError(
                    te_number, 
                    f"시험항목 '{te_number}'에 대한 검증 규칙을 찾을 수 없습니다."
                )
            
            # 2. 시험항목 데이터 추출
            test_data = self.test_item_extractor.extract_test_item_data(te_number)
            
            # 3. 표준 준수 검사 실행
            compliance_results = self._execute_compliance_checks(test_data, rule)
            
            # 4. 검증 결과 생성
            validation_result = self._create_validation_result(
                te_number, rule, test_data, compliance_results
            )
            
            # 5. 검증 이력 추가
            duration = (datetime.now() - start_time).total_seconds()
            self._add_to_history(te_number, validation_result.status.value, duration)
            
            self.logger.info(f"시험항목 검증 완료: {te_number} - {validation_result.status.value}")
            return validation_result
            
        except (TestItemNotFoundError, ValidationError):
            # 이미 적절한 예외이므로 재발생
            duration = (datetime.now() - start_time).total_seconds()
            self._add_to_history(te_number, "오류", duration)
            raise
        except Exception as e:
            # 예상치 못한 오류
            duration = (datetime.now() - start_time).total_seconds()
            self._add_to_history(te_number, "오류", duration)
            self.logger.error(f"시험항목 검증 중 예상치 못한 오류: {str(e)}")
            raise ValidationError(f"시험항목 '{te_number}' 검증 실패: {str(e)}")
    
    def _execute_compliance_checks(self, test_data: TestItemData, rule: ValidationRule) -> List[ComplianceResult]:
        """표준 준수 검사 실행"""
        compliance_results = []
        
        try:
            # 검증 체크 목록 실행
            for check_config in rule.validation_checks:
                check_type = check_config.get("type")
                weight = check_config.get("weight", 1.0)
                
                try:
                    if check_type == "metadata_completeness":
                        result = self.compliance_checker.check_metadata_completeness(test_data, rule)
                    elif check_type == "table_structure":
                        result = self.compliance_checker.check_table_structure(test_data, rule)
                    elif check_type == "content_accuracy":
                        result = self.compliance_checker.check_content_accuracy(test_data, rule)
                    elif check_type == "required_elements":
                        result = self.compliance_checker.check_required_elements(test_data, rule)
                    else:
                        self.logger.warning(f"알 수 없는 검증 타입: {check_type}")
                        continue
                    
                    # 가중치 적용
                    result.weight = weight
                    compliance_results.append(result)
                    
                    self.logger.debug(f"검증 체크 완료: {check_type} - {result.passed}")
                    
                except Exception as e:
                    self.logger.error(f"검증 체크 '{check_type}' 실행 중 오류: {str(e)}")
                    # 실패한 검증 결과 생성
                    error_result = ComplianceResult(
                        rule_name=check_type,
                        passed=False,
                        message=f"검증 실행 오류: {str(e)}",
                        iso_reference="",
                        weight=weight
                    )
                    compliance_results.append(error_result)
            
            return compliance_results
            
        except Exception as e:
            self.logger.error(f"표준 준수 검사 실행 중 오류: {str(e)}")
            raise ComplianceCheckError("compliance_execution", str(e))
    
    def _create_validation_result(
        self, 
        te_number: str, 
        rule: ValidationRule, 
        test_data: TestItemData, 
        compliance_results: List[ComplianceResult]
    ) -> ValidationResult:
        """검증 결과 생성"""
        try:
            # 전체 점수 계산
            total_score = 0
            total_weight = 0
            
            reasons = []
            evidence = []
            
            for result in compliance_results:
                weight = result.weight
                score = weight if result.passed else 0
                
                total_score += score
                total_weight += weight
                
                # 이유 및 증거 수집
                if result.passed:
                    if result.evidence:
                        evidence.append(f"{result.rule_name}: {result.evidence}")
                else:
                    reasons.append(f"{result.rule_name}: {result.message}")
                    if result.evidence:
                        evidence.append(f"{result.rule_name}: {result.evidence}")
            
            # 최종 통과/실패 판정
            pass_threshold = getattr(rule, 'minimum_pass_score', 0.7)
            final_score = total_score / total_weight if total_weight > 0 else 0
            passed = final_score >= pass_threshold
            
            # 상태 결정
            status = ValidationStatus.PASS if passed else ValidationStatus.FAIL
            
            # 통과한 경우 긍정적인 이유 추가
            if passed and not reasons:
                reasons.append(f"모든 검증 항목을 통과했습니다 (점수: {final_score:.2f}/{pass_threshold:.2f})")
            
            # 실패한 경우 점수 정보 추가
            if not passed:
                reasons.insert(0, f"검증 점수가 기준에 미달했습니다 (점수: {final_score:.2f}/{pass_threshold:.2f})")
            
            return ValidationResult(
                test_item_name=rule.name,
                te_number=te_number,
                status=status,
                reasons=reasons,
                evidence=evidence,
                iso_references=rule.iso_references,
                timestamp=datetime.now()
            )
            
        except Exception as e:
            self.logger.error(f"검증 결과 생성 중 오류: {str(e)}")
            # 오류 발생 시 실패 결과 반환
            return ValidationResult(
                test_item_name=rule.name if rule else "알 수 없음",
                te_number=te_number,
                status=ValidationStatus.FAIL,
                reasons=[f"검증 결과 생성 오류: {str(e)}"],
                evidence=[],
                iso_references=rule.iso_references if rule else [],
                timestamp=datetime.now()
            )
    
    def get_validation_details(self, te_number: str) -> Dict[str, Any]:
        """시험항목의 상세 검증 정보 반환 (실제 검증 없이 정보만 조회)"""
        try:
            # 규칙 정보 조회
            rule = self.rule_engine.get_rules_for_test_item(te_number)
            if not rule:
                return {"error": f"시험항목 '{te_number}'에 대한 규칙을 찾을 수 없습니다."}
            
            # 시험항목 데이터 조회 시도
            try:
                test_data = self.test_item_extractor.extract_test_item_data(te_number)
                data_available = True
                data_info = {
                    "page_number": test_data.page_number,
                    "has_image": test_data.has_image,
                    "cells_count": len(test_data.cells) if test_data.cells else 0,
                    "caption": test_data.caption,
                    "metadata_fields": list(test_data.metadata.keys())
                }
            except TestItemNotFoundError:
                data_available = False
                data_info = {"error": "시험항목 데이터를 찾을 수 없습니다."}
            
            return {
                "te_number": te_number,
                "rule_info": {
                    "name": rule.name,
                    "required_metadata": rule.required_metadata,
                    "required_table_fields": rule.required_table_fields,
                    "required_images": rule.required_images,
                    "iso_references": rule.iso_references,
                    "validation_checks": rule.validation_checks
                },
                "data_available": data_available,
                "data_info": data_info
            }
            
        except Exception as e:
            self.logger.error(f"검증 상세 정보 조회 중 오류: {str(e)}")
            return {"error": str(e)}    d
ef validate_multiple_items(self, te_numbers: List[str], parallel: bool = True) -> List[ValidationResult]:
        """
        여러 TE 번호에 대한 일괄 검증
        
        Args:
            te_numbers (List[str]): 검증할 TE 번호 목록
            parallel (bool): 병렬 처리 여부 (기본값: True)
            
        Returns:
            List[ValidationResult]: 검증 결과 목록
        """
        try:
            if not te_numbers:
                self.logger.warning("검증할 TE 번호가 제공되지 않았습니다.")
                return []
            
            self.logger.info(f"다중 시험항목 검증 시작: {len(te_numbers)}개 항목")
            
            if parallel and len(te_numbers) > 1:
                return self._validate_multiple_parallel(te_numbers)
            else:
                return self._validate_multiple_sequential(te_numbers)
                
        except Exception as e:
            self.logger.error(f"다중 시험항목 검증 중 오류: {str(e)}")
            raise ValidationError(f"다중 검증 실패: {str(e)}")
    
    def _validate_multiple_sequential(self, te_numbers: List[str]) -> List[ValidationResult]:
        """순차적 다중 검증"""
        results = []
        
        for i, te_number in enumerate(te_numbers, 1):
            try:
                self.logger.info(f"검증 진행 중: {i}/{len(te_numbers)} - {te_number}")
                result = self.validate_test_item(te_number)
                results.append(result)
                
            except Exception as e:
                self.logger.error(f"시험항목 '{te_number}' 검증 실패: {str(e)}")
                # 실패한 항목에 대해서도 결과 생성
                error_result = ValidationResult(
                    test_item_name=f"오류 - {te_number}",
                    te_number=te_number,
                    status=ValidationStatus.FAIL,
                    reasons=[f"검증 실행 오류: {str(e)}"],
                    evidence=[],
                    iso_references=[],
                    timestamp=datetime.now()
                )
                results.append(error_result)
        
        self.logger.info(f"순차 검증 완료: {len(results)}개 결과")
        return results
    
    def _validate_multiple_parallel(self, te_numbers: List[str]) -> List[ValidationResult]:
        """병렬 다중 검증"""
        import concurrent.futures
        import threading
        
        results = []
        max_workers = min(ValidationConfig.MAX_CONCURRENT_VALIDATIONS, len(te_numbers))
        
        # 스레드 로컬 스토리지를 위한 락
        results_lock = threading.Lock()
        
        def validate_single_item(te_number: str) -> ValidationResult:
            """단일 항목 검증 (스레드 안전)"""
            try:
                return self.validate_test_item(te_number)
            except Exception as e:
                self.logger.error(f"병렬 검증 중 오류 - {te_number}: {str(e)}")
                return ValidationResult(
                    test_item_name=f"오류 - {te_number}",
                    te_number=te_number,
                    status=ValidationStatus.FAIL,
                    reasons=[f"병렬 검증 오류: {str(e)}"],
                    evidence=[],
                    iso_references=[],
                    timestamp=datetime.now()
                )
        
        try:
            with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
                # 모든 작업 제출
                future_to_te = {
                    executor.submit(validate_single_item, te_number): te_number 
                    for te_number in te_numbers
                }
                
                # 결과 수집
                for future in concurrent.futures.as_completed(future_to_te):
                    te_number = future_to_te[future]
                    try:
                        result = future.result(timeout=30)  # 30초 타임아웃
                        with results_lock:
                            results.append(result)
                        self.logger.debug(f"병렬 검증 완료: {te_number}")
                        
                    except concurrent.futures.TimeoutError:
                        self.logger.error(f"검증 타임아웃: {te_number}")
                        timeout_result = ValidationResult(
                            test_item_name=f"타임아웃 - {te_number}",
                            te_number=te_number,
                            status=ValidationStatus.FAIL,
                            reasons=["검증 시간 초과 (30초)"],
                            evidence=[],
                            iso_references=[],
                            timestamp=datetime.now()
                        )
                        with results_lock:
                            results.append(timeout_result)
                        
                    except Exception as e:
                        self.logger.error(f"병렬 검증 예외: {te_number} - {str(e)}")
                        error_result = ValidationResult(
                            test_item_name=f"예외 - {te_number}",
                            te_number=te_number,
                            status=ValidationStatus.FAIL,
                            reasons=[f"병렬 처리 예외: {str(e)}"],
                            evidence=[],
                            iso_references=[],
                            timestamp=datetime.now()
                        )
                        with results_lock:
                            results.append(error_result)
            
            # 원래 순서대로 정렬
            te_number_to_index = {te: i for i, te in enumerate(te_numbers)}
            results.sort(key=lambda r: te_number_to_index.get(r.te_number, 999))
            
            self.logger.info(f"병렬 검증 완료: {len(results)}개 결과")
            return results
            
        except Exception as e:
            self.logger.error(f"병렬 검증 시스템 오류: {str(e)}")
            # 병렬 처리 실패 시 순차 처리로 폴백
            self.logger.info("순차 처리로 폴백합니다.")
            return self._validate_multiple_sequential(te_numbers)
    
    def validate_all_available_items(self, parallel: bool = True) -> List[ValidationResult]:
        """사용 가능한 모든 시험항목 검증"""
        try:
            available_te_numbers = self.get_available_te_numbers()
            
            if not available_te_numbers:
                self.logger.warning("검증 가능한 시험항목이 없습니다.")
                return []
            
            self.logger.info(f"전체 시험항목 검증 시작: {len(available_te_numbers)}개")
            return self.validate_multiple_items(available_te_numbers, parallel)
            
        except Exception as e:
            self.logger.error(f"전체 검증 중 오류: {str(e)}")
            raise ValidationError(f"전체 검증 실패: {str(e)}")
    
    def validate_by_pattern(self, pattern: str, parallel: bool = True) -> List[ValidationResult]:
        """
        패턴에 맞는 시험항목들을 검증
        
        Args:
            pattern (str): TE 번호 패턴 (예: "TE02.03.*", "TE02.*")
            parallel (bool): 병렬 처리 여부
            
        Returns:
            List[ValidationResult]: 검증 결과 목록
        """
        try:
            import re
            
            # 패턴을 정규식으로 변환
            regex_pattern = pattern.replace("*", ".*").replace("?", ".")
            if not regex_pattern.startswith("^"):
                regex_pattern = "^" + regex_pattern
            if not regex_pattern.endswith("$"):
                regex_pattern = regex_pattern + "$"
            
            available_te_numbers = self.get_available_te_numbers()
            matching_te_numbers = [
                te for te in available_te_numbers 
                if re.match(regex_pattern, te)
            ]
            
            if not matching_te_numbers:
                self.logger.warning(f"패턴 '{pattern}'에 맞는 시험항목이 없습니다.")
                return []
            
            self.logger.info(f"패턴 검증 시작: '{pattern}' - {len(matching_te_numbers)}개 항목")
            return self.validate_multiple_items(matching_te_numbers, parallel)
            
        except Exception as e:
            self.logger.error(f"패턴 검증 중 오류: {str(e)}")
            raise ValidationError(f"패턴 검증 실패: {str(e)}")
    
    def create_validation_report(self, results: List[ValidationResult], format_type: str = "text") -> str:
        """검증 결과 보고서 생성"""
        try:
            if not results:
                return "검증 결과가 없습니다."
            
            return self.result_formatter.format_multiple_results(results, format_type)
            
        except Exception as e:
            self.logger.error(f"보고서 생성 중 오류: {str(e)}")
            return f"보고서 생성 오류: {str(e)}"
    
    def save_validation_report(
        self, 
        results: List[ValidationResult], 
        file_path: str, 
        format_type: str = "text"
    ) -> bool:
        """검증 결과 보고서를 파일로 저장"""
        try:
            return self.result_formatter.save_results_to_file(results, file_path, format_type)
        except Exception as e:
            self.logger.error(f"보고서 저장 중 오류: {str(e)}")
            return False
    
    def get_validation_summary(self, results: List[ValidationResult]) -> Dict[str, Any]:
        """검증 결과 요약 정보 생성"""
        try:
            return self.result_formatter.create_summary_report(results)
        except Exception as e:
            self.logger.error(f"요약 정보 생성 중 오류: {str(e)}")
            return {"error": str(e)}