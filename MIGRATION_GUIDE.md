# Migration Guide: Old → New Architecture

## Overview

This guide explains how to migrate from the old monolithic architecture to the new layered, loosely-coupled architecture.

## Key Changes

### 1. Package Structure

**Old Structure:**
```
/
├── validator.py (976 lines)
├── iso24759_validator.py (2,956 lines)
├── pdf_to_json.py (1,452 lines)
├── json_to_pdf.py (771 lines)
├── gui.py (5,772 lines) ← GOD OBJECT
├── config_reader.py (113 lines)
└── main.py (65 lines)
```

**New Structure:**
```
json_validation/
├── domain/              # Core business entities
│   ├── models.py
│   ├── enums.py
│   └── exceptions.py
├── interfaces/          # Contracts
│   ├── repositories.py
│   ├── services.py
│   └── validators.py
├── repositories/        # Data access
│   ├── json_repository.py
│   ├── config_repository.py
│   └── file_repository.py
├── services/           # Business logic
│   ├── validation_service.py
│   ├── document_service.py
│   └── conversion_service.py
├── validators/         # Validation strategies
├── converters/         # PDF/JSON conversion
├── infrastructure/     # Cross-cutting concerns
│   ├── config.py
│   └── di_container.py
└── gui/               # User interface
    ├── components/
    └── presenters/
```

## Migration Examples

### Example 1: Using JSON Operations

**Old Way (Tight Coupling):**
```python
from validator import JSONValidator

validator = JSONValidator()
validator.load_json_file("data.json")
found, not_found = validator.search_value(["TE02.03.01"])
```

**New Way (Loose Coupling):**
```python
from json_validation.infrastructure.di_container import get_container
from json_validation.interfaces.services import IDocumentService

# Get service from DI container
container = get_container()
doc_service = container.resolve(IDocumentService)

# Use high-level service methods
json_data = doc_service.load_document("data.json")
results = doc_service.search_in_document(json_data, ["TE02.03.01"])
```

**Benefits:**
- ✅ No direct dependency on implementation
- ✅ Easy to test with mock service
- ✅ Cleaner API

### Example 2: Configuration

**Old Way:**
```python
from config_reader import ConfigReader

config_reader = ConfigReader()
values = config_reader.read_config_file("config.txt")
```

**New Way:**
```python
from json_validation.infrastructure.di_container import get_container
from json_validation.interfaces.repositories import IConfigRepository

container = get_container()
config_repo = container.resolve(IConfigRepository)
values = config_repo.parse_search_config("config.txt")
```

**Or use centralized config:**
```python
from json_validation.infrastructure.config import config

output_dir = config.get('output_dir')
min_score = config.get('min_pass_score')
```

### Example 3: Validation

**Old Way:**
```python
from iso24759_validator import ISO24759Validator

validator = ISO24759Validator()
validator.load_json_data(json_data)
result = validator.validate_test_item("TE02.03.01")
```

**New Way:**
```python
from json_validation.infrastructure.di_container import get_container
from json_validation.interfaces.services import IValidationService

container = get_container()
validation_service = container.resolve(IValidationService)
result = validation_service.validate_test_item("TE02.03.01", json_data)
```

## Dependency Injection Benefits

### Old Way: Creating Dependencies Manually
```python
# Tight coupling - hard to test
class ValidationGUI:
    def __init__(self):
        self.validator = ISO24759Validator()  # Direct dependency
        self.config = ConfigReader()           # Direct dependency
        self.pdf_extractor = PDFExtractor()    # Direct dependency

    def validate(self):
        # Hard to test - can't mock dependencies
        result = self.validator.validate_test_item(te_num)
```

### New Way: Injecting Dependencies
```python
# Loose coupling - easy to test
class ValidationGUI:
    def __init__(
        self,
        validation_service: IValidationService,  # Interface, not implementation
        config_repo: IConfigRepository
    ):
        self._validation_service = validation_service
        self._config_repo = config_repo

    def validate(self):
        # Easy to test - inject mock service
        result = self._validation_service.validate_test_item(te_num, data)
```

**Testing with DI:**
```python
# Unit test with mock service
def test_validation_gui():
    # Create mock service
    mock_service = MockValidationService()
    mock_config = MockConfigRepository()

    # Inject mocks
    gui = ValidationGUI(mock_service, mock_config)

    # Test without real dependencies!
    gui.validate()
    assert mock_service.validate_called
```

## Layer Responsibilities

### Domain Layer
**What:** Core business entities (ValidationResult, TestItemData, etc.)
**Dependencies:** None
**Location:** `json_validation/domain/`

### Interfaces Layer
**What:** Contracts (IValidator, IRepository, etc.)
**Dependencies:** Domain only
**Location:** `json_validation/interfaces/`

### Repositories Layer
**What:** Data access (JsonRepository, ConfigRepository)
**Dependencies:** Interfaces, Domain
**Location:** `json_validation/repositories/`

### Services Layer
**What:** Business logic orchestration
**Dependencies:** Interfaces, Domain
**Location:** `json_validation/services/`

### GUI Layer
**What:** User interface
**Dependencies:** Services (NOT repositories directly!)
**Location:** `json_validation/gui/`

## Best Practices

### ✅ DO

1. **Depend on Interfaces:**
   ```python
   def __init__(self, service: IValidationService):  # ✅ Interface
       self._service = service
   ```

2. **Use DI Container:**
   ```python
   container = get_container()
   service = container.resolve(IValidationService)
   ```

3. **Keep Layers Separated:**
   ```python
   # GUI → Services → Repositories → Data
   # Each layer only knows about the layer below
   ```

4. **Use Domain Models:**
   ```python
   result = ValidationResult(te_number="TE02.03.01", status=ValidationStatus.PASS)
   ```

### ❌ DON'T

1. **Don't Depend on Concrete Classes:**
   ```python
   def __init__(self, service: ValidationService):  # ❌ Concrete class
       self._service = service
   ```

2. **Don't Skip Service Layer:**
   ```python
   # ❌ GUI directly using repository
   class GUI:
       def __init__(self):
           self.repo = JsonRepository()  # ❌ Skip service layer

   # ✅ GUI using service
   class GUI:
       def __init__(self, doc_service: IDocumentService):  # ✅
           self._doc_service = doc_service
   ```

3. **Don't Mix Concerns:**
   ```python
   # ❌ Service doing data access AND business logic AND presentation
   class BadService:
       def validate(self):
           data = json.load(...)  # Data access
           result = check(data)   # Business logic
           print(result)          # Presentation
           return result

   # ✅ Separated concerns
   class Repository:
       def load(self): return json.load(...)  # Only data access

   class Service:
       def validate(self): return check(data)  # Only business logic

   class Presenter:
       def display(self): print(result)  # Only presentation
   ```

## Testing Strategy

### Unit Tests (New Architecture)
```python
def test_validation_service():
    # Create mocks
    mock_doc_service = Mock(spec=IDocumentService)
    mock_config_repo = Mock(spec=IConfigRepository)

    # Inject mocks
    service = ValidationService(mock_doc_service, mock_config_repo)

    # Setup test data
    mock_doc_service.extract_test_item.return_value = TestItemData(...)

    # Test
    result = service.validate_test_item("TE02.03.01", {})

    # Verify
    assert result.te_number == "TE02.03.01"
    mock_doc_service.extract_test_item.assert_called_once()
```

### Integration Tests
```python
def test_full_validation_workflow():
    # Use real container
    container = get_container()
    validation_service = container.resolve(IValidationService)

    # Test with real dependencies
    result = validation_service.validate_from_file("TE02.03.01", "test_data.json")

    assert result.status == ValidationStatus.PASS
```

## Gradual Migration Path

You can migrate gradually:

1. **Phase 1:** Use new architecture alongside old code
2. **Phase 2:** Migrate one feature at a time
3. **Phase 3:** Update GUI to use services
4. **Phase 4:** Remove old code

**Example: Using both old and new:**
```python
# Old code still works
from validator import JSONValidator
old_validator = JSONValidator()

# New code available
from json_validation.infrastructure.di_container import get_container
from json_validation.interfaces.services import IDocumentService
container = get_container()
doc_service = container.resolve(IDocumentService)

# Choose which to use
use_new_architecture = True
if use_new_architecture:
    data = doc_service.load_document("data.json")
else:
    old_validator.load_json_file("data.json")
    data = old_validator.json_data
```

## Common Patterns

### Pattern 1: Service Method
```python
# Service orchestrates multiple operations
class ValidationService:
    def validate_test_item(self, te_number, json_data):
        # 1. Extract data (via document service)
        test_item = self._doc_service.extract_test_item(te_number, json_data)

        # 2. Load rules (via config repository)
        rules = self._config_repo.load_validation_rules()

        # 3. Validate (via validators)
        results = self._perform_checks(test_item, rules)

        # 4. Calculate score
        score = self._calculate_score(results)

        # 5. Return domain object
        return ValidationResult(te_number, score, results)
```

### Pattern 2: Repository Method
```python
# Repository handles only data access
class JsonRepository:
    def load(self, file_path):
        with open(file_path, 'r') as f:
            return json.load(f)  # Just data access, no business logic
```

### Pattern 3: Domain Model with Behavior
```python
# Domain object with business logic
@dataclass
class ValidationResult:
    te_number: str
    status: ValidationStatus
    score: float

    @property
    def passed(self) -> bool:
        return self.status == ValidationStatus.PASS

    def add_error(self, error: str):
        self.errors.append(error)
        if self.status == ValidationStatus.PASS:
            self.status = ValidationStatus.FAIL
```

## Getting Started with New Architecture

### Quick Start
```python
# 1. Import DI container
from json_validation.infrastructure.di_container import get_container

# 2. Get container
container = get_container()

# 3. Resolve services
from json_validation.interfaces.services import IValidationService, IDocumentService

validation_service = container.resolve(IValidationService)
document_service = container.resolve(IDocumentService)

# 4. Use services
json_data = document_service.load_document("data.json")
result = validation_service.validate_test_item("TE02.03.01", json_data)

# 5. Access result
print(f"Status: {result.status}")
print(f"Score: {result.score:.2%}")
```

### Run Demo
```bash
python demo_new_architecture.py
```

## Questions?

- See `ARCHITECTURE.md` for detailed architecture documentation
- See `demo_new_architecture.py` for working examples
- Check `json_validation/` for implementation details
