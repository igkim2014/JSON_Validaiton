"""
Demo script showcasing the new refactored architecture

This demonstrates:
1. Dependency Injection
2. Loose Coupling
3. High Cohesion
4. KISS principle
5. Repository Pattern
6. Service Layer Pattern
"""

from json_validation.infrastructure.di_container import get_container
from json_validation.infrastructure.config import config
from json_validation.interfaces.services import IValidationService, IDocumentService
from json_validation.interfaces.repositories import IJsonRepository, IConfigRepository
from json_validation.domain.enums import OutputFormat


def demo_dependency_injection():
    """Demonstrate dependency injection and loose coupling"""
    print("=" * 80)
    print("DEMO 1: Dependency Injection & Loose Coupling")
    print("=" * 80)

    # Get the DI container
    container = get_container()

    # Resolve services - automatically injects dependencies
    validation_service = container.resolve(IValidationService)
    document_service = container.resolve(IDocumentService)

    print("✅ Services successfully resolved from DI container")
    print(f"   - Validation Service: {type(validation_service).__name__}")
    print(f"   - Document Service: {type(document_service).__name__}")
    print()
    print("🔍 Notice: We depend on INTERFACES, not concrete implementations")
    print("   This allows easy testing and swapping of implementations!")
    print()


def demo_repository_pattern():
    """Demonstrate repository pattern for data access"""
    print("=" * 80)
    print("DEMO 2: Repository Pattern - Clean Data Access")
    print("=" * 80)

    container = get_container()

    # Get repositories
    json_repo = container.resolve(IJsonRepository)
    config_repo = container.resolve(IConfigRepository)

    print("✅ Repositories successfully resolved")
    print(f"   - JSON Repository: {type(json_repo).__name__}")
    print(f"   - Config Repository: {type(config_repo).__name__}")
    print()
    print("🔍 Benefits:")
    print("   - Data access logic is centralized")
    print("   - Easy to swap storage mechanisms")
    print("   - Testable with mock repositories")
    print()


def demo_service_layer():
    """Demonstrate service layer orchestration"""
    print("=" * 80)
    print("DEMO 3: Service Layer - Business Logic Orchestration")
    print("=" * 80)

    container = get_container()
    document_service = container.resolve(IDocumentService)

    print("✅ Document Service provides high-level operations:")
    print("   - load_document()")
    print("   - extract_test_item()")
    print("   - search_in_document()")
    print("   - find_test_result_table()")
    print()
    print("🔍 Services orchestrate workflows across repositories and validators")
    print("   GUI/CLI only needs to call simple service methods!")
    print()


def demo_configuration_management():
    """Demonstrate centralized configuration"""
    print("=" * 80)
    print("DEMO 4: Configuration Management")
    print("=" * 80)

    # Access global configuration
    print("✅ Centralized configuration (Singleton pattern):")
    print(f"   - Base directory: {config.get('base_dir')}")
    print(f"   - Config directory: {config.get('config_dir')}")
    print(f"   - Output directory: {config.get('output_dir')}")
    print(f"   - Min pass score: {config.get('min_pass_score')}")
    print()

    # Set custom configuration
    config.set('custom_setting', 'my_value')
    print(f"   - Custom setting: {config.get('custom_setting')}")
    print()
    print("🔍 All configuration in one place, easy to manage!")
    print()


def demo_domain_models():
    """Demonstrate domain models"""
    print("=" * 80)
    print("DEMO 5: Domain Models - Rich Business Objects")
    print("=" * 80)

    from json_validation.domain.models import ValidationResult, ComplianceResult
    from json_validation.domain.enums import ValidationStatus

    # Create domain objects
    result = ValidationResult(
        te_number="TE02.03.01",
        status=ValidationStatus.PASS,
        score=0.95
    )

    result.add_warning("This is a sample warning")

    print("✅ Rich domain models with behavior:")
    print(f"   - TE Number: {result.te_number}")
    print(f"   - Status: {result.status}")
    print(f"   - Score: {result.score:.2%}")
    print(f"   - Passed: {result.passed}")
    print(f"   - Total Checks: {result.total_checks}")
    print(f"   - Warnings: {result.warnings}")
    print()
    print("🔍 Domain objects encapsulate business logic and validation rules")
    print()


def demo_architecture_benefits():
    """Summarize architecture benefits"""
    print("=" * 80)
    print("ARCHITECTURE BENEFITS SUMMARY")
    print("=" * 80)
    print()
    print("✅ LOOSE COUPLING:")
    print("   - Modules depend on interfaces, not concrete implementations")
    print("   - Easy to swap implementations")
    print("   - Changes in one module don't affect others")
    print()
    print("✅ HIGH COHESION:")
    print("   - Each class has a single, well-defined responsibility")
    print("   - JsonRepository: JSON operations only")
    print("   - DocumentService: Document operations only")
    print("   - ValidationService: Validation orchestration only")
    print()
    print("✅ KISS PRINCIPLE:")
    print("   - Simple, readable code")
    print("   - No over-engineering")
    print("   - Clear separation of concerns")
    print()
    print("✅ DESIGN PATTERNS:")
    print("   - Repository Pattern: Clean data access")
    print("   - Service Layer: Business logic orchestration")
    print("   - Dependency Injection: Loose coupling")
    print("   - Strategy Pattern: Pluggable validators")
    print("   - Singleton: Configuration management")
    print()
    print("✅ TESTABILITY:")
    print("   - Each component can be tested in isolation")
    print("   - Easy to mock dependencies")
    print("   - Clear interfaces for testing")
    print()
    print("✅ MAINTAINABILITY:")
    print("   - Clear package structure")
    print("   - Easy to navigate codebase")
    print("   - Changes are localized")
    print()
    print("✅ SCALABILITY:")
    print("   - Easy to add new validators")
    print("   - Easy to add new services")
    print("   - Can support CLI, GUI, API with same core")
    print()


def demo_layer_separation():
    """Demonstrate layer separation"""
    print("=" * 80)
    print("DEMO 6: Layer Separation")
    print("=" * 80)
    print()
    print("📦 DOMAIN LAYER (No dependencies)")
    print("   └── Models, Enums, Exceptions")
    print("       ├── ValidationResult")
    print("       ├── TestItemData")
    print("       ├── ValidationStatus")
    print("       └── ValidationError")
    print()
    print("📦 INTERFACES LAYER (Domain only)")
    print("   └── Contracts for implementations")
    print("       ├── IJsonRepository")
    print("       ├── IValidationService")
    print("       └── IValidator")
    print()
    print("📦 REPOSITORIES LAYER (Interfaces + Domain)")
    print("   └── Data access implementations")
    print("       ├── JsonRepository")
    print("       ├── ConfigRepository")
    print("       └── FileRepository")
    print()
    print("📦 SERVICES LAYER (Interfaces + Domain)")
    print("   └── Business logic orchestration")
    print("       ├── ValidationService")
    print("       └── DocumentService")
    print()
    print("📦 INFRASTRUCTURE LAYER")
    print("   └── Cross-cutting concerns")
    print("       ├── Config")
    print("       └── DIContainer")
    print()
    print("📦 GUI/CLI LAYER (Services only)")
    print("   └── User interface")
    print("       └── Depends on Services, not Repositories!")
    print()
    print("🔍 Dependencies flow INWARD toward Domain")
    print("   Outer layers depend on inner layers, never the reverse!")
    print()


def main():
    """Run all demos"""
    print("\n")
    print("🎯" * 40)
    print("JSON VALIDATION SYSTEM - NEW ARCHITECTURE DEMO")
    print("🎯" * 40)
    print("\n")

    try:
        demo_dependency_injection()
        input("Press Enter to continue...\n")

        demo_repository_pattern()
        input("Press Enter to continue...\n")

        demo_service_layer()
        input("Press Enter to continue...\n")

        demo_configuration_management()
        input("Press Enter to continue...\n")

        demo_domain_models()
        input("Press Enter to continue...\n")

        demo_layer_separation()
        input("Press Enter to continue...\n")

        demo_architecture_benefits()

        print("\n")
        print("=" * 80)
        print("✅ DEMO COMPLETED SUCCESSFULLY!")
        print("=" * 80)
        print()
        print("📚 For more information, see ARCHITECTURE.md")
        print()

    except Exception as e:
        print(f"\n❌ Error during demo: {e}")
        import traceback
        traceback.print_exc()


if __name__ == "__main__":
    main()
