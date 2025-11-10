"""
Result object for error handling throughout Arcane Arsenal.

All operations that can fail return a Result object instead of raising exceptions.
This provides clear, type-safe error handling and makes the API predictable.
"""

from dataclasses import dataclass
from enum import Enum
from typing import Any, Optional


class ErrorCode(Enum):
    """
    Standard error codes for Result objects.

    Provides machine-readable error classification for better error handling.
    """

    # Entity errors
    ENTITY_NOT_FOUND = "entity_not_found"
    ENTITY_ALREADY_EXISTS = "entity_already_exists"
    ENTITY_DELETED = "entity_deleted"

    # Component errors
    COMPONENT_NOT_FOUND = "component_not_found"
    COMPONENT_ALREADY_EXISTS = "component_already_exists"
    COMPONENT_TYPE_NOT_REGISTERED = "component_type_not_registered"

    # Validation errors
    VALIDATION_ERROR = "validation_error"
    SCHEMA_VALIDATION_FAILED = "schema_validation_failed"
    INVALID_INPUT = "invalid_input"
    MISSING_REQUIRED_FIELD = "missing_required_field"

    # Relationship errors
    RELATIONSHIP_NOT_FOUND = "relationship_not_found"
    RELATIONSHIP_TYPE_NOT_REGISTERED = "relationship_type_not_registered"
    CIRCULAR_RELATIONSHIP = "circular_relationship"

    # Permission errors
    PERMISSION_DENIED = "permission_denied"
    UNAUTHORIZED = "unauthorized"

    # Database errors
    DATABASE_ERROR = "database_error"
    TRANSACTION_FAILED = "transaction_failed"
    STORAGE_ERROR = "storage_error"

    # Dependency errors
    DEPENDENCY_ERROR = "dependency_error"
    MODULE_NOT_LOADED = "module_not_loaded"

    # State errors
    INVALID_STATE = "invalid_state"
    OPERATION_NOT_ALLOWED = "operation_not_allowed"

    # Generic errors
    UNKNOWN = "unknown"
    NOT_IMPLEMENTED = "not_implemented"
    UNEXPECTED_ERROR = "unexpected_error"

    def __str__(self) -> str:
        """Return the error code value."""
        return self.value


@dataclass
class Result:
    """
    Represents the result of an operation that can succeed or fail.
    
    Attributes:
        success: Whether the operation succeeded
        data: The result data if successful
        error: Error message if failed
        error_code: Machine-readable error code if failed
    
    Examples:
        >>> result = Result.ok({"entity_id": "123"})
        >>> if result.success:
        ...     print(result.data)
        
        >>> result = Result.fail("Entity not found", "ENTITY_NOT_FOUND")
        >>> if not result.success:
        ...     print(f"Error: {result.error}")
    """
    success: bool
    data: Any = None
    error: Optional[str] = None
    error_code: Optional[str] = None
    
    @staticmethod
    def ok(data: Any = None) -> 'Result':
        """
        Create a successful result.
        
        Args:
            data: Optional data to return
            
        Returns:
            Result with success=True
        """
        return Result(success=True, data=data)
    
    @staticmethod
    def fail(error: str, code: Optional[str | ErrorCode] = None) -> 'Result':
        """
        Create a failed result.

        Args:
            error: Human-readable error message
            code: Machine-readable error code (ErrorCode enum or string)

        Returns:
            Result with success=False

        Examples:
            >>> Result.fail("Entity not found", ErrorCode.ENTITY_NOT_FOUND)
            >>> Result.fail("Validation error", "CUSTOM_ERROR")
        """
        error_code_str = code.value if isinstance(code, ErrorCode) else code
        return Result(success=False, error=error, error_code=error_code_str)
    
    def __bool__(self) -> bool:
        """Allow using Result in boolean context: if result: ..."""
        return self.success
