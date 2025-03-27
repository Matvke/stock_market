import pytest
from fastapi.testclient import TestClient
from main import app
from dependencies import get_db
from schemas.response import L2OrderBook


@pytest.fixture
def client(test_session):
    app.dependency_overrides[get_db] = lambda: test_session
    yield TestClient(app)
    app.dependency_overrides.clear()


@pytest.mark.asyncio
async def test_register_user(client):
    response = client.post("/api/v1/public/register", json={"name": "Pedro"})
    assert response.status_code == 200
    assert response.json()["name"] == "Pedro"


@pytest.mark.asyncio
async def test_get_instruments(client):
    response = client.get("/api/v1/public/instrument")
    assert response.status_code == 200


@pytest.mark.asyncio
async def test_get_orderbook(client):
    response = client.get("/api/v1/public/orderbook/AAPL")
    assert response.status_code == 200
