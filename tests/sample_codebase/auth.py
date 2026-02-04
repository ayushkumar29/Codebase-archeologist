"""
Authentication service for the sample codebase.
"""

from typing import Optional
from .models import User, UserRepository


class AuthService:
    """Handles user authentication."""
    
    def __init__(self, user_repo: UserRepository):
        """Initialize with a user repository."""
        self.user_repo = user_repo
        self._session_cache: dict[int, str] = {}
        
    def authenticate(self, user_id: int, password: str) -> Optional[str]:
        """
        Authenticate a user and return a session token.
        
        Args:
            user_id: The user's ID
            password: The user's password
            
        Returns:
            Session token if authentication succeeds, None otherwise
        """
        user = self.user_repo.get_user(user_id)
        
        if user is None:
            return None
            
        if self._verify_password(password):
            token = self._generate_token(user)
            self._session_cache[user_id] = token
            return token
            
        return None
        
    def _verify_password(self, password: str) -> bool:
        """Verify the password (simplified for demo)."""
        return len(password) >= 8
        
    def _generate_token(self, user: User) -> str:
        """Generate a session token for the user."""
        import hashlib
        data = f"{user.id}:{user.email}"
        return hashlib.sha256(data.encode()).hexdigest()[:32]
        
    def logout(self, user_id: int) -> bool:
        """Log out a user by invalidating their session."""
        if user_id in self._session_cache:
            del self._session_cache[user_id]
            return True
        return False
        
    def is_authenticated(self, user_id: int, token: str) -> bool:
        """Check if a user's session is valid."""
        return self._session_cache.get(user_id) == token
