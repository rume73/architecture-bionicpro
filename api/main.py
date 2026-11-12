from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
import clickhouse_connect
import os
import jwt
import requests
from typing import Optional
from pydantic import BaseModel
from datetime import datetime

app = FastAPI(title="BionicPRO Reports API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:3000"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

CH_HOST = os.getenv("CLICKHOUSE_HOST", "clickhouse")
CH_PORT = int(os.getenv("CLICKHOUSE_PORT", "8123"))
CH_USER = os.getenv("CLICKHOUSE_USER", "default")
CH_PASS = os.getenv("CLICKHOUSE_PASSWORD", "clickhouse")

KEYCLOAK_URL = os.getenv("KEYCLOAK_URL", "http://keycloak:8080")
KEYCLOAK_REALM = os.getenv("KEYCLOAK_REALM", "reports-realm")


def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASS
    )


_jwks_cache = {}


def get_keycloak_public_key():
    if "key" in _jwks_cache:
        return _jwks_cache["key"]

    url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
    try:
        response = requests.get(url)
        response.raise_for_status()
        jwks = response.json()
        key_data = jwks["keys"][0]

        from jwt.algorithms import RSAAlgorithm
        public_key = RSAAlgorithm.from_jwk(key_data)
        _jwks_cache["key"] = public_key
        return public_key
    except Exception as e:
        print(f"Error fetching JWKS: {e}")
        return None


def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]
    public_key = get_keycloak_public_key()

    if not public_key:
        raise HTTPException(status_code=500, detail="Cannot validate token signature")

    try:
        payload = jwt.decode(
            token,
            public_key,
            algorithms=["RS256"],
            audience="account",
            options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.InvalidTokenError as e:
        raise HTTPException(status_code=401, detail=f"Invalid token: {e}")


class ReportResponse(BaseModel):
    user_id: int
    user_email: str
    prosthesis_id: int
    total_movements: int
    avg_response_ms: float
    last_active: str
    report_date: str


@app.get("/reports", response_model=ReportResponse)
def get_report(token_payload: dict = Depends(verify_token)):
    username = token_payload.get("preferred_username", "")
    user_id = None
    if username.startswith("prothetic"):
        try:
            user_id = int(username.replace("prothetic", ""))
        except ValueError:
            pass

    if user_id is None:
        raise HTTPException(status_code=403, detail="No report available for this user")

    client = get_ch_client()

    result = client.query(
        "SELECT * FROM report_datamart WHERE user_id = {uid:UInt64} ORDER BY report_date DESC LIMIT 1",
        parameters={"uid": user_id}
    )

    if not result.result_rows:
        raise HTTPException(status_code=404, detail="Report not found for this user. Data may not be processed yet.")

    row = result.result_rows[0]

    return ReportResponse(
        user_id=row[0],
        user_email=row[1],
        prosthesis_id=row[2],
        total_movements=row[3],
        avg_response_ms=round(row[4], 2),
        last_active=row[5].isoformat() if row[5] else "",
        report_date=str(row[6])
    )


@app.get("/health")
def health():
    return {"status": "ok"}
