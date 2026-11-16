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

jwks_url = f"{KEYCLOAK_URL}/realms/{KEYCLOAK_REALM}/protocol/openid-connect/certs"
jwks_client = jwt.PyJWKClient(jwks_url)


def get_ch_client():
    return clickhouse_connect.get_client(
        host=CH_HOST, port=CH_PORT, username=CH_USER, password=CH_PASS
    )


def verify_token(authorization: Optional[str] = Header(None)):
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing or invalid token")

    token = authorization.split(" ")[1]

    try:
        signing_key = jwks_client.get_signing_key_from_jwt(token)

        payload = jwt.decode(
            token,
            signing_key.key,
            algorithms=["RS256"],
            options={"verify_aud": False}
        )
        return payload
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.PyJWKClientError as e:
        raise HTTPException(status_code=401, detail=f"Signing key error: {e}")
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
