import os
from dotenv import load_dotenv
from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError

load_dotenv()

API_KEY_HEADER_NAME = "X-API-Key"
expected_hash = os.environ.get("MUSIC_API_KEY_HASH")
api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=True)

ph = PasswordHasher()

def verify_api_key(api_key: str = Security(api_key_header)):
    print(expected_hash)
    print(api_key)
    if not expected_hash:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Brak konfiguracji MUSIC_API_KEY_HASH na serwerze"
        )
        
    try:
        ph.verify(expected_hash, api_key)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Nieprawidłowy klucz API"
        )
    
    return api_key