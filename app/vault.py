import base64
import os
from typing import Dict, Optional
from cryptography.fernet import Fernet
from app.config import settings
from app.models import Workflow, WorkflowContext


def generate_vault_key() -> str:
    """Generate a new 32-byte base64 vault key."""
    return base64.urlsafe_b64encode(os.urandom(32)).decode()


def get_fernet() -> Fernet:
    """Get Fernet instance with vault key."""
    vault_key = settings.vault_key
    if not vault_key:
        # Auto-generate for development
        vault_key = generate_vault_key()
        print(f"Generated vault key: {vault_key}")
        print("Set VAULT_KEY environment variable for production!")
    
    try:
        return Fernet(vault_key.encode())
    except Exception:
        # If key is invalid, generate a new one
        new_key = generate_vault_key()
        print(f"Invalid vault key, generated new one: {new_key}")
        return Fernet(new_key.encode())


def encrypt_secret(value: str) -> str:
    """Encrypt a secret value."""
    fernet = get_fernet()
    return fernet.encrypt(value.encode()).decode()


def decrypt_secret(encrypted_value: str) -> str:
    """Decrypt a secret value."""
    fernet = get_fernet()
    return fernet.decrypt(encrypted_value.encode()).decode()


# In-memory secret store (replace with DB in production)
SECRET_STORE: Dict[str, Dict[str, str]] = {}


def store_secret(account_id: str, key: str, value: str) -> None:
    """Store an encrypted secret for an account."""
    if account_id not in SECRET_STORE:
        SECRET_STORE[account_id] = {}
    
    SECRET_STORE[account_id][key] = encrypt_secret(value)


def get_secret(account_id: str, key: str) -> Optional[str]:
    """Retrieve and decrypt a secret for an account."""
    if account_id not in SECRET_STORE:
        return None
    
    encrypted_value = SECRET_STORE[account_id].get(key)
    if not encrypted_value:
        return None
    
    try:
        return decrypt_secret(encrypted_value)
    except Exception:
        return None


def inject_secrets(workflow: Workflow, account_id: Optional[str]) -> WorkflowContext:
    """Create workflow context with injected secrets."""
    context = WorkflowContext(
        request_id=f"req_{base64.urlsafe_b64encode(os.urandom(8)).decode()}",
        account_id=account_id
    )
    
    if not account_id:
        return context
    
    # Inject common secrets
    secrets = {}
    if settings.openai_key:
        secrets["OPENAI_API_KEY"] = settings.openai_key
    
    # Add account-specific secrets
    if account_id in SECRET_STORE:
        for key, encrypted_value in SECRET_STORE[account_id].items():
            try:
                secrets[key] = decrypt_secret(encrypted_value)
            except Exception:
                continue
    
    context.secrets = secrets
    return context 