"""Credential Vault module (Phase 0 stub).

Per Section 4 & Section 12:
- Credential Vault owns: Storing/retrieving secrets via Windows Credential Manager,
  never exposing raw secrets to LLM context.
- Credential Vault does NOT own: Deciding when a credential is needed.
- Receives: Credential name request.
- Returns: Opaque handle or injected auth, never raw text into context.
- Called by: Browser / auth-requiring tools.
"""

from typing import Optional


class CredentialVault:
    """Credential Vault stub."""

    def get_credential_handle(self, name: str) -> Optional[str]:
        return f"credential_handle_for_{name}"
