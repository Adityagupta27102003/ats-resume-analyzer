"""Supabase auth: the frontend logs users in with supabase-js and sends the access
token as `Authorization: Bearer <token>`. We verify it by asking Supabase Auth who
the token belongs to — this works for both legacy (HS256) and new asymmetric JWT
signing keys, so we never have to handle the JWT secret ourselves.
"""
import logging
from typing import Optional

import httpx
from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from backend.core.config import SUPABASE_URL, SUPABASE_ANON_KEY

logger = logging.getLogger('ats_resume_scorer')
_bearer = HTTPBearer(auto_error=False)


async def get_optional_user(
    creds: Optional[HTTPAuthorizationCredentials] = Depends(_bearer),
) -> Optional[str]:
    """Return the Supabase user id, or None for anonymous requests.

    A token that is present but invalid is rejected (401) rather than silently
    treated as anonymous — otherwise an expired session would quietly stop saving history.
    """
    if creds is None:
        return None
    if not SUPABASE_URL or not SUPABASE_ANON_KEY:
        logger.warning('Auth token received but Supabase is not configured; treating as anonymous')
        return None

    try:
        async with httpx.AsyncClient(timeout=10) as client:
            resp = await client.get(
                f"{SUPABASE_URL.rstrip('/')}/auth/v1/user",
                headers={'apikey': SUPABASE_ANON_KEY, 'Authorization': f'Bearer {creds.credentials}'},
            )
    except httpx.HTTPError as exc:
        logger.error(f'Supabase auth check failed: {exc}')
        raise HTTPException(status.HTTP_503_SERVICE_UNAVAILABLE, 'Authentication service unavailable')

    if resp.status_code != 200:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Invalid or expired session. Please log in again.')
    return resp.json()['id']


async def get_current_user(user_id: Optional[str] = Depends(get_optional_user)) -> str:
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, 'Login required')
    return user_id
