## JSON Validation System - Refactored Architecture

### Overview

This project has been refactored to follow modern software architecture principles:
- **Loose Coupling**: Modules depend on abstractions, not concrete implementations
- **High Cohesion**: Each module has a single, well-defined responsibility
- **KISS Principle**: Simple, readable code without over-engineering
- **Design Patterns**: Repository, Service Layer, Dependency Injection, Strategy, Singleton

### Architecture Highlights

#### 🎯 Layered Architecture
```
Presentation (GUI) → Application (Services) → Domain → Infrastructure
```

#### 🔧 Key Improvements

**Before:**
- 5,772-line GUI god object
- Tight coupling between modules
- Low cohesion (mixing concerns)
- Hard to test
- Difficult to maintain

**After:**
- Modular package structure
- Dependency injection
- Clear separation of concerns
- Highly testable
- Easy to extend

### Quick Start

#### Running the Demo
```bash
python demo_new_architecture.py
```

This demonstrates:
- Dependency Injection
- Repository Pattern
- Service Layer
- Domain Models
- Configuration Management

#### Using the New Architecture

```python
from json_validation.infrastructure.di_container import get_container
from json_validation.interfaces.services import IValidationService

# Get DI container
container = get_container()

# Resolve service (with all dependencies injected)
validation_service = container.resolve(IValidationService)

# Use service
result = validation_service.validate_from_file("TE02.03.01", "data.json")

print(f"Status: {result.status}")
print(f"Score: {result.score:.2%}")
```

### Package Structure

```
json_validation/
├── domain/              # Core business entities (no dependencies)
│   ├── models.py       # ValidationResult, TestItemData, etc.
│   ├── enums.py        # ValidationStatus, ValidationType, etc.
│   └── exceptions.py   # Domain exceptions
│
├── interfaces/          # Contracts/Abstractions
│   ├── repositories.py # Data access interfaces
│   ├── services.py     # Service interfaces
│   └── validators.py   # Validator interfaces
│
├── repositories/        # Data access implementations
│   ├── json_repository.py
│   ├── config_repository.py
│   └── file_repository.py
│
├── services/           # Business logic orchestration
│   ├── validation_service.py
│   ├── document_service.py
│   └── conversion_service.py
│
├── validators/         # Validation strategies
│   └── (to be implemented)
│
├── converters/         # PDF/JSON conversion
│   └── (to be implemented)
│
├── infrastructure/     # Cross-cutting concerns
│   ├── config.py      # Centralized configuration
│   └── di_container.py # Dependency injection
│
└── gui/               # User interface (to be refactored)
    ├── components/
    └── presenters/
```

### Design Patterns Used

#### 1. Repository Pattern
**Purpose:** Abstract data access
```python
class JsonRepository(IJsonRepository):
    def load(self, file_path: str) -> Dict[str, Any]:
        # Handle data access only
```

#### 2. Service Layer Pattern
**Purpose:** Orchestrate business logic
```python
class ValidationService(IValidationService):
    def validate_test_item(self, te_number: str, json_data: Dict) -> ValidationResult:
        # Orchestrate validation workflow
```

#### 3. Dependency Injection
**Purpose:** Loose coupling
```python
class ValidationService:
    def __init__(
        self,
        document_service: IDocumentService,  # Injected dependency
        config_repository: IConfigRepository
    ):
        self._doc_service = document_service
        self._config_repo = config_repository
```

#### 4. Strategy Pattern
**Purpose:** Pluggable algorithms
```python
# Different validation strategies
IMetadataValidator
ITableValidator
IContentValidator
IElementValidator
```

#### 5. Singleton Pattern
**Purpose:** Global configuration
```python
from json_validation.infrastructure.config import config

output_dir = config.get('output_dir')
```

### Key Benefits

#### ✅ Testability
```python
def test_validation_service():
    # Easy to mock dependencies
    mock_doc_service = Mock(spec=IDocumentService)
    service = ValidationService(mock_doc_service, ...)
    # Test in isolation
```

#### ✅ Maintainability
- Clear package structure
- Single Responsibility Principle
- Easy to navigate

#### ✅ Flexibility
- Swap implementations easily
- Add new features without breaking existing code
- Support multiple interfaces (CLI, GUI, API)

#### ✅ Scalability
- Easy to add new validators
- Easy to add new services
- Can scale to larger team

### Dependency Flow

```
GUI
 ↓ (depends on)
Services
 ↓ (depends on)
Repositories & Validators
 ↓ (depends on)
Domain Models & Interfaces
 ↓ (depends on)
Nothing (pure Python)
```

**Rule:** Dependencies point INWARD toward domain. Outer layers depend on inner layers, never the reverse.

### Example Workflow

#### Validation Workflow
```python
# 1. Get container
container = get_container()

# 2. Resolve services (automatic dependency injection)
validation_service = container.resolve(IValidationService)
# Behind the scenes:
#   - Creates DocumentService (injects JsonRepository, FileRepository)
#   - Creates ValidationService (injects DocumentService, ConfigRepository)

# 3. Use service (high-level API)
result = validation_service.validate_test_item("TE02.03.01", json_data)
# Behind the scenes:
#   - DocumentService extracts test item
#   - ConfigRepository loads rules
#   - Validators perform checks
#   - ValidationService calculates score
#   - Returns ValidationResult (domain object)

# 4. Access result
print(result.status)  # ValidationStatus.PASS or FAIL
print(result.score)   # 0.0 to 1.0
print(result.errors)  # List of errors
```

### Configuration Management

#### Centralized Configuration
```python
from json_validation.infrastructure.config import config

# Get configuration
output_dir = config.get('output_dir')
min_score = config.get('min_pass_score', 0.8)

# Set configuration
config.set('custom_setting', 'value')

# Get path as Path object
fonts_path = config.get_path('fonts_dir')

# Ensure directories exist
config.ensure_directories()
```

#### Environment Variables
```bash
export JSON_VALIDATION_OUTPUT_DIR=/custom/output
export JSON_VALIDATION_LOG_LEVEL=DEBUG
```

```python
config.load_from_env()
```

### Testing Strategy

#### Unit Tests
Test each component in isolation with mocked dependencies:
```python
def test_json_repository():
    repo = JsonRepository()
    data = repo.load("test.json")
    assert data is not None
```

#### Integration Tests
Test services with real dependencies:
```python
def test_validation_service_integration():
    container = get_container()
    service = container.resolve(IValidationService)
    result = service.validate_from_file("TE02.03.01", "test.json")
    assert result.status == ValidationStatus.PASS
```

#### End-to-End Tests
Test complete workflows:
```python
def test_full_validation_workflow():
    # Load document
    # Extract test items
    # Validate
    # Generate report
```

### Migration Path

The new architecture coexists with the old code:

1. **Old code** (`validator.py`, `gui.py`, etc.) still works
2. **New code** (`json_validation/`) provides better architecture
3. **Gradual migration** possible - one feature at a time

See `MIGRATION_GUIDE.md` for detailed migration instructions.

### Documentation

- **ARCHITECTURE.md** - Detailed architecture documentation
- **MIGRATION_GUIDE.md** - How to migrate from old to new architecture
- **README_NEW_ARCHITECTURE.md** - This file

### Demo

Run the demo to see the architecture in action:
```bash
python demo_new_architecture.py
```

The demo showcases:
1. Dependency Injection & Loose Coupling
2. Repository Pattern
3. Service Layer
4. Configuration Management
5. Domain Models
6. Layer Separation
7. Architecture Benefits

### Next Steps

- [ ] Migrate remaining validators to new architecture
- [ ] Implement conversion service
- [ ] Refactor GUI into smaller components
- [ ] Add comprehensive tests
- [ ] Remove old code once migration is complete

### Contributing

When adding new features:

1. **Add domain models** in `domain/` if needed
2. **Define interface** in `interfaces/`
3. **Implement** in appropriate layer (`repositories/`, `services/`, etc.)
4. **Register in DI container** in `infrastructure/di_container.py`
5. **Add tests**

Follow the dependency rule: outer layers depend on inner layers.

### Questions?

- Check the demo: `demo_new_architecture.py`
- Read the architecture docs: `ARCHITECTURE.md`
- See migration guide: `MIGRATION_GUIDE.md`

---

**Architecture Principles:**
- 🎯 Loose Coupling
- 🎯 High Cohesion
- 🎯 KISS (Keep It Simple)
- 🎯 SOLID Principles
- 🎯 Design Patterns
