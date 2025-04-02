from pydantic import ValidationError
import pytest
from fastapi.testclient import TestClient
from fastapi import status
from main import app
from dependencies import get_db
from schemas.response import L2OrderBook, InstrumentResponse, UserResponse, Level, TransactionResponse


@pytest.mark.asyncio
async def test_register_user(client):
    response = client.post("/api/v1/public/register", json={"name": "Pedro"})
    assert response.status_code == 200
    assert response.json()["name"] == "Pedro"
    try:
        UserResponse.model_validate(response.json())
    except ValidationError as e:
        pytest.fail(f"Response doesn't match schema: {e}")


@pytest.mark.asyncio
async def test_get_instruments(client):
    response = client.get("/api/v1/public/instrument")
    assert response.status_code == 200
    for item in response.json():
        try:
            InstrumentResponse.model_validate(item)
        except ValidationError as e:
            pytest.fail(f"Item {item} doesn't match schema: {e}")


@pytest.mark.asyncio
async def test_get_orderbook(client):
    response = client.get("/api/v1/public/orderbook/AAPL")
    assert response.status_code == 200
    try:
        L2OrderBook.model_validate(response.json())
    except ValidationError as e:
        pytest.fail(f"Response doesn't match schema: {e}")


@pytest.mark.asyncio
async def test_get_transactions_history(client):
    response = client.get("/api/v1/public/transactions/AAPL")
    assert response.status_code == 200
    for item in response.json():
        try:
            TransactionResponse.model_validate(item)
        except ValidationError as e:
            pytest.fail(f"Item {item} doesn't match schema: {e}")


@pytest.mark.asyncio
async def test_get_balances_unauthorized(client):
    response = client.get("/api/v1/balance")
    assert response.status_code == status.HTTP_403_FORBIDDEN


@pytest.mark.asyncio
async def test_get_balances_authorized(auth_client):
    response = auth_client.get("/api/v1/balance") 
    assert response.status_code == status.HTTP_200_OK
    assert isinstance(response.json(), dict)
    assert "AAPL" in response.json()