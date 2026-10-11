"""Connectivity Manager module (Phase 0 stub).

Per Section 4:
- Connectivity Manager owns: Internet/API/auth-state availability, triggering offline degradation.
- Connectivity Manager does NOT own: Choosing what to do offline (caller's decision).
- Receives: Monitors/polls.
- Returns: Connectivity status.
- Called by: LLM Router, Tool Manager.
"""

from pydantic import BaseModel


class ConnectivityStatus(BaseModel):
    is_online: bool = True


class ConnectivityManager:
    """Connectivity Manager stub."""

    def get_status(self) -> ConnectivityStatus:
        return ConnectivityStatus(is_online=True)
