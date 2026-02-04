"""
Sample codebase for testing the Archaeologist.
This file contains various code patterns for testing the parser and extractor.
"""

from dataclasses import dataclass
from typing import Optional


# Example module-level constant
VERSION = "1.0.0"


@dataclass
class User:
    """Represents a user in the system."""
    id: int
    name: str
    email: str


class BaseRepository:
    """Base class for all repositories."""
    
    def __init__(self, connection_string: str):
        """Initialize the repository with a database connection."""
        self.connection_string = connection_string
        
    def connect(self) -> bool:
        """Establish database connection."""
        print(f"Connecting to {self.connection_string}")
        return True
        
    def disconnect(self) -> None:
        """Close database connection."""
        print("Disconnecting...")


class UserRepository(BaseRepository):
    """Repository for user operations."""
    
    def get_user(self, user_id: int) -> Optional[User]:
        """Fetch a user by ID."""
        # Simulated database lookup
        if user_id == 1:
            return User(id=1, name="John Doe", email="john@example.com")
        return None
        
    def save_user(self, user: User) -> bool:
        """Save a user to the database."""
        self._validate_user(user)
        print(f"Saving user: {user.name}")
        return True
        
    def _validate_user(self, user: User) -> None:
        """Validate user data before saving."""
        if not user.email or "@" not in user.email:
            raise ValueError("Invalid email address")
