"""
Dependency Injection Container
Simple DI container following KISS principle
"""

from typing import Any, Callable, Dict, Type, TypeVar, Optional

T = TypeVar('T')


class DIContainer:
    """
    Simple dependency injection container
    Supports singleton and transient lifetimes
    """

    def __init__(self):
        """Initialize DI container"""
        self._singletons: Dict[Type, Any] = {}
        self._factories: Dict[Type, Callable[[], Any]] = {}
        self._transients: Dict[Type, Callable[[], Any]] = {}

    def register_singleton(self, interface: Type[T], implementation: T) -> None:
        """
        Register a singleton instance

        Args:
            interface: Interface type
            implementation: Implementation instance
        """
        self._singletons[interface] = implementation

    def register_factory(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory function that creates singletons

        Args:
            interface: Interface type
            factory: Factory function that creates the instance
        """
        self._factories[interface] = factory

    def register_transient(self, interface: Type[T], factory: Callable[[], T]) -> None:
        """
        Register a factory for transient (per-request) instances

        Args:
            interface: Interface type
            factory: Factory function that creates new instances
        """
        self._transients[interface] = factory

    def resolve(self, interface: Type[T]) -> T:
        """
        Resolve a dependency

        Args:
            interface: Interface type to resolve

        Returns:
            Instance of the requested type

        Raises:
            ValueError: If dependency cannot be resolved
        """
        # Check singletons first
        if interface in self._singletons:
            return self._singletons[interface]

        # Check factory singletons
        if interface in self._factories:
            if interface not in self._singletons:
                self._singletons[interface] = self._factories[interface]()
            return self._singletons[interface]

        # Check transients
        if interface in self._transients:
            return self._transients[interface]()

        raise ValueError(f"No registration found for type: {interface}")

    def resolve_optional(self, interface: Type[T]) -> Optional[T]:
        """
        Try to resolve a dependency, return None if not found

        Args:
            interface: Interface type to resolve

        Returns:
            Instance or None
        """
        try:
            return self.resolve(interface)
        except ValueError:
            return None

    def clear(self) -> None:
        """Clear all registrations"""
        self._singletons.clear()
        self._factories.clear()
        self._transients.clear()

    def is_registered(self, interface: Type) -> bool:
        """
        Check if interface is registered

        Args:
            interface: Interface type

        Returns:
            True if registered
        """
        return (
            interface in self._singletons
            or interface in self._factories
            or interface in self._transients
        )


def create_container() -> DIContainer:
    """
    Create and configure DI container with all dependencies

    Returns:
        Configured DI container
    """
    from ..repositories.json_repository import JsonRepository
    from ..repositories.config_repository import ConfigRepository
    from ..repositories.file_repository import FileRepository
    from ..interfaces.repositories import IJsonRepository, IConfigRepository, IFileRepository
    from ..interfaces.services import IDocumentService, IValidationService
    from ..services.document_service import DocumentService
    from ..services.validation_service import ValidationService

    container = DIContainer()

    # Register repositories as singletons
    container.register_factory(IJsonRepository, lambda: JsonRepository())
    container.register_factory(IConfigRepository, lambda: ConfigRepository())
    container.register_factory(IFileRepository, lambda: FileRepository())

    # Register services as singletons with dependency injection
    def create_document_service():
        json_repo = container.resolve(IJsonRepository)
        file_repo = container.resolve(IFileRepository)
        return DocumentService(json_repo, file_repo)

    def create_validation_service():
        doc_service = container.resolve(IDocumentService)
        config_repo = container.resolve(IConfigRepository)
        return ValidationService(doc_service, config_repo)

    container.register_factory(IDocumentService, create_document_service)
    container.register_factory(IValidationService, create_validation_service)

    return container


# Global container instance
_container: Optional[DIContainer] = None


def get_container() -> DIContainer:
    """
    Get global DI container instance

    Returns:
        DI container
    """
    global _container
    if _container is None:
        _container = create_container()
    return _container


def reset_container() -> None:
    """Reset global container"""
    global _container
    _container = None
