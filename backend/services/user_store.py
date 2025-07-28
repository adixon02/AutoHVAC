from typing import Dict, Optional
import threading

class UserPlanStatus:
    def __init__(self):
        self.email: str = ""
        self.first_job_used: bool = False
        self.stripe_customer_id: Optional[str] = None
        self.active: bool = False

class InMemoryUserStore:
    def __init__(self):
        self._users: Dict[str, UserPlanStatus] = {}
        self._lock = threading.Lock()
    
    def get_user(self, email: str) -> UserPlanStatus:
        with self._lock:
            if email not in self._users:
                user = UserPlanStatus()
                user.email = email
                self._users[email] = user
            return self._users[email]
    
    def update_user(self, email: str, **kwargs) -> None:
        with self._lock:
            user = self.get_user(email)
            for key, value in kwargs.items():
                if hasattr(user, key):
                    setattr(user, key, value)
    
    def mark_first_job_used(self, email: str) -> None:
        self.update_user(email, first_job_used=True)
    
    def activate_subscription(self, email: str, stripe_customer_id: str) -> None:
        self.update_user(email, stripe_customer_id=stripe_customer_id, active=True)
    
    def deactivate_subscription(self, email: str) -> None:
        self.update_user(email, active=False)

user_store = InMemoryUserStore()