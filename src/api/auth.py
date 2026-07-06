from fastapi import APIRouter, Depends, HTTPException, Security, status
from fastapi.security import APIKeyHeader
from argon2 import PasswordHasher
from argon2.exceptions import VerifyMismatchError
from src.config import API_KEY_HEADER_NAME,EXPECTED_HASH


api_key_header = APIKeyHeader(name=API_KEY_HEADER_NAME, auto_error=True)

ph = PasswordHasher()

router = APIRouter(
    prefix="/auth", 
    tags=["auth"]
)

def verify_api_key(api_key: str = Security(api_key_header)):
    try:
        ph.verify(EXPECTED_HASH, api_key)
    except VerifyMismatchError:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Not Welcome"
        )
    return api_key

@router.get("/")
def check_password(api_key: str = Depends(verify_api_key)):
    return {"message": "Welcome"}