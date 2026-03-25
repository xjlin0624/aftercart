# Authentication

> **Stack:** FastAPI · python-jose (HS256 JWT) · passlib/bcrypt · PostgreSQL

---

## Endpoints

| Method | Path | Auth required | Description |
|---|---|---|---|
| `POST` | `/api/v1/auth/signup` | No | Create account, returns `UserRead` (201) |
| `POST` | `/api/v1/auth/login` | No | Verify credentials, returns token pair |
| `POST` | `/api/v1/auth/logout` | No* | Invalidate refresh token (204) |
| `POST` | `/api/v1/auth/refresh` | No* | Rotate token pair |

*These endpoints accept the refresh token in the request body rather than a header, since they operate on the token itself.

---

## Token Design

### Two-token pattern
- **Access token** — short-lived (default 30 min), passed as `Authorization: Bearer <token>` on protected routes. Never stored in the database.
- **Refresh token** — long-lived (default 7 days), used only to obtain a new token pair. Stored as a bcrypt hash in `users.refresh_token_hash`.

### Why store the refresh token hashed?
If the database were compromised, plaintext refresh tokens would let an attacker silently impersonate users until the tokens expire. Hashing means the attacker gets only the hash — useless without brute-forcing bcrypt. The access token is not stored because its short TTL limits the damage window to 30 minutes without requiring any DB lookup on every request.

### Refresh token rotation
Every call to `/refresh` issues a **new** refresh token and invalidates the old one (by overwriting `refresh_token_hash`). This means:
- A stolen refresh token can only be used once before it is rotated away.
- If an attacker uses a stolen token before the legitimate user does, the legitimate user's next refresh will fail (the hash won't match), signalling compromise.

### Logout
`/logout` accepts the refresh token and sets `refresh_token_hash = NULL`. The access token is not revoked — it will expire naturally within its TTL. Clients should discard it locally on logout.

---

## Configuration

All values are set via environment variables (see `.env.example`):

| Variable | Default | Description |
|---|---|---|
| `JWT_SECRET` | `change-me-in-production` | HMAC signing key — **must be changed in production** |
| `JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | `30` | Access token TTL |
| `REFRESH_TOKEN_EXPIRE_DAYS` | `7` | Refresh token TTL |

---

## File Map

```
backend/app/
├── main.py                  # FastAPI app entry point; mounts router at /api/v1
├── core/
│   ├── settings.py          # Pydantic settings; JWT config loaded from env
│   └── security.py          # hash_password, verify_password, create_access_token,
│                            #   create_refresh_token, decode_token
├── schemas/
│   └── auth.py              # SignupRequest, LoginRequest, RefreshRequest, TokenResponse
└── api/
    ├── deps.py              # get_db() FastAPI dependency (yields SQLAlchemy Session)
    └── v1/
        └── auth.py          # The 4 auth endpoints
```

---

## Token Payload

```json
{
  "sub": "<user UUID as string>",
  "kind": "access" | "refresh",
  "exp": <unix timestamp>
}
```

The `kind` claim prevents an access token from being accepted where a refresh token is expected and vice versa.
