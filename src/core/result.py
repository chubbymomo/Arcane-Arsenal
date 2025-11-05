"""
Result object for error handling throughout Arcane Arsenal.

All operations that can fail return a Result object instead of raising exceptions.
This provides clear, type-safe error handling and makes the API predictable.
"""

from dataclasses import dataclass
from typing import Any, Optional


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
    def fail(error: str, code: str = None) -> 'Result':
        """
        Create a failed result.
        
        Args:
            error: Human-readable error message
            code: Machine-readable error code (e.g., 'ENTITY_NOT_FOUND')
            
        Returns:
            Result with success=False
        """
        return Result(success=False, error=error, error_code=code)
    
    def __bool__(self) -> bool:
        """Allow using Result in boolean context: if result: ..."""
        return self.success
