# JSON Validation System - Refactored Architecture

## Architecture Principles

### 1. Layered Architecture
```
┌─────────────────────────────────────┐
│     Presentation Layer (GUI)        │
├─────────────────────────────────────┤
│   Application Layer (Services)      │
├─────────────────────────────────────┤
│      Domain Layer (Models)          │
├─────────────────────────────────────┤
│  Infrastructure Layer (Repository)  │
└─────────────────────────────────────┘
```

### 2. Design Principles Applied
- **Loose Coupling**: Modules depend on abstractions, not concrete implementations
- **High Cohesion**: Each module has a single, well-defined responsibility
- **KISS**: Simple, readable code without over-engineering
- **DRY**: No code duplication
- **Dependency Inversion**: High-level modules don't depend on low-level modules
- **Interface Segregation**: Small, focused interfaces

### 3. Design Patterns Used
- **Repository Pattern**: Abstract data access
- **Service Layer**: Business logic orchestration
- **Dependency Injection**: Constructor-based injection
- **Strategy Pattern**: Pluggable validation algorithms
- **Factory Pattern**: Object creation
- **Adapter Pattern**: Convert between different interfaces
- **Facade Pattern**: Simplify complex subsystems

## Package Structure

```
json_validation/
├── domain/                      # Domain Layer (Pure Business Logic)
│   ├── __init__.py
│   ├── models.py               # Domain entities (ValidationResult, TestItem, etc.)
│   ├── enums.py                # Enumerations (ValidationStatus, etc.)
│   └── exceptions.py           # Domain-specific exceptions
│
├── interfaces/                  # Contracts/Abstractions
│   ├── __init__.py
│   ├── repositories.py         # Data access interfaces
│   ├── services.py             # Service interfaces
│   └── validators.py           # Validator interfaces
│
├── services/                    # Application Layer (Use Cases)
│   ├── __init__.py
│   ├── validation_service.py   # Validation orchestration
│   ├── conversion_service.py   # PDF conversion orchestration
│   └── document_service.py     # Document management
│
├── validators/                  # Validation Implementations
│   ├── __init__.py
│   ├── base_validator.py       # Base validator
│   ├── iso24759_validator.py   # ISO standard validator
│   ├── metadata_validator.py   # Metadata validation
│   ├── table_validator.py      # Table validation
│   └── content_validator.py    # Content validation
│
├── converters/                  # Conversion Layer
│   ├── __init__.py
│   ├── pdf_extractor.py        # PDF to JSON
│   └── pdf_generator.py        # JSON to PDF
│
├── repositories/                # Infrastructure Layer (Data Access)
│   ├── __init__.py
│   ├── json_repository.py      # JSON file operations
│   ├── config_repository.py    # Configuration file operations
│   └── file_repository.py      # Generic file operations
│
├── infrastructure/              # Infrastructure Concerns
│   ├── __init__.py
│   ├── config.py               # Configuration management
│   ├── logging_config.py       # Logging setup
│   └── di_container.py         # Dependency injection container
│
├── gui/                         # Presentation Layer
│   ├── __init__.py
│   ├── main_window.py          # Main application window
│   ├── components/             # Reusable UI components
│   │   ├── __init__.py
│   │   ├── document_viewer.py
│   │   ├── validation_panel.py
│   │   └── table_viewer.py
│   └── presenters/             # Presentation logic (MVP pattern)
│       ├── __init__.py
│       ├── validation_presenter.py
│       └── conversion_presenter.py
│
└── main.py                      # Application entry point

config/
└── validation_rules.json        # External configuration

Legacy files (to be migrated):
- validator.py → services/validation_service.py + repositories/json_repository.py
- iso24759_validator.py → validators/iso24759_validator.py + domain/models.py
- pdf_to_json.py → converters/pdf_extractor.py
- json_to_pdf.py → converters/pdf_generator.py
- gui.py → gui/main_window.py + gui/components/* + gui/presenters/*
- config_reader.py → repositories/config_repository.py
```

## Layer Responsibilities

### Domain Layer
- **Purpose**: Core business entities and rules
- **Dependencies**: None (pure Python, no external dependencies)
- **Contents**:
  - Data classes (ValidationResult, TestItem, ComplianceResult)
  - Enumerations (ValidationStatus)
  - Business exceptions
  - Domain logic (scoring, pass/fail determination)

### Interfaces Layer
- **Purpose**: Define contracts for implementations
- **Dependencies**: Domain layer only
- **Benefits**:
  - Testability (easy mocking)
  - Flexibility (swap implementations)
  - Clear contracts

### Services Layer
- **Purpose**: Orchestrate use cases and business workflows
- **Dependencies**: Interfaces, Domain
- **Responsibilities**:
  - Coordinate validators
  - Manage transactions
  - Business logic orchestration
  - Return domain objects

### Validators Layer
- **Purpose**: Implement validation strategies
- **Dependencies**: Interfaces, Domain
- **Pattern**: Strategy pattern
- **Characteristics**:
  - Focused, single-purpose validators
  - Composable
  - Testable in isolation

### Converters Layer
- **Purpose**: Handle PDF ↔ JSON transformations
- **Dependencies**: Interfaces, Domain
- **Characteristics**:
  - Independent from GUI
  - Reusable from CLI or API
  - Well-tested

### Repositories Layer
- **Purpose**: Abstract data access
- **Dependencies**: Interfaces, Domain
- **Pattern**: Repository pattern
- **Benefits**:
  - Encapsulate data access logic
  - Easy to swap storage mechanisms
  - Centralized data operations

### Infrastructure Layer
- **Purpose**: Cross-cutting concerns
- **Contents**:
  - Configuration management
  - Logging
  - Dependency injection container
  - File system utilities

### GUI Layer
- **Purpose**: User interface
- **Dependencies**: Services (not direct to repositories or validators)
- **Pattern**: MVP (Model-View-Presenter)
- **Characteristics**:
  - Thin UI layer
  - No business logic
  - Delegates to services

## Dependency Flow

```
GUI → Services → Validators → Repositories
 ↓         ↓          ↓            ↓
Presenters ← Interfaces ← Domain ← Infrastructure
```

**Key Rules**:
1. Dependencies point **inward** (toward domain)
2. Domain has **zero** external dependencies
3. Outer layers depend on interfaces, not implementations
4. No circular dependencies

## Key Improvements

### Before (Tight Coupling)
```python
# gui.py directly using concrete classes
class JSONValidatorGUI:
    def validate(self):
        validator = ISO24759Validator()  # Tight coupling
        result = validator.validate_test_item(te_num)
```

### After (Loose Coupling with DI)
```python
# gui/main_window.py using injected services
class MainWindow:
    def __init__(self, validation_service: IValidationService):
        self._validation_service = validation_service  # Injected dependency

    def validate(self):
        result = self._validation_service.validate(te_num)
```

### Before (Low Cohesion)
```python
# validator.py mixing concerns
class JSONValidator:
    def search_value(self):          # Data access
    def create_table_image(self):    # Image generation
    def find_test_result_table(self): # Business logic
```

### After (High Cohesion)
```python
# Separated concerns
class JSONRepository:           # Data access only
    def find_value(self, path): pass

class TableImageGenerator:      # Image generation only
    def create_image(self, data): pass

class ValidationService:        # Business logic only
    def validate(self, te_num): pass
```

## Migration Strategy

1. **Phase 1**: Create new structure (domain, interfaces)
2. **Phase 2**: Extract services from existing code
3. **Phase 3**: Implement repositories
4. **Phase 4**: Refactor GUI into smaller components
5. **Phase 5**: Wire up dependency injection
6. **Phase 6**: Test and verify
7. **Phase 7**: Remove old files

## Testing Strategy

- **Unit Tests**: Test each component in isolation
- **Integration Tests**: Test service layer with real dependencies
- **GUI Tests**: Test presenters without actual UI
- **End-to-End Tests**: Full workflow tests

## Benefits of New Architecture

1. **Testability**: Each component can be tested in isolation
2. **Maintainability**: Clear separation of concerns
3. **Flexibility**: Easy to swap implementations
4. **Scalability**: Can add new validators, converters easily
5. **Reusability**: Services can be used from CLI, API, or GUI
6. **Understanding**: Clear structure makes codebase navigable
