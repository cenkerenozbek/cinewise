"""
Tests for the authentication API endpoints.

Covers:
- POST /api/auth/register (success, duplicate email)
- POST /api/auth/login (success, invalid credentials)
- Password hashing verification
- Protected endpoint without Bearer token
"""
import pytest
from httpx import AsyncClient


async def test_register_success(client: AsyncClient):
    """Test 1: POST /api/auth/register with valid data returns 201."""
    response = await client.post(
        "/api/auth/register",
        json={"email": "test@test.com", "password": "StrongPass1!"},
    )
    assert response.status_code == 201
    data = response.json()
    assert "id" in data
    assert data["email"] == "test@test.com"
    # Password must NOT be returned
    assert "password" not in data
    assert "hashed_password" not in data


async def test_register_duplicate(client: AsyncClient):
    """Test 2: Registering same email twice returns 409."""
    await client.post(
        "/api/auth/register",
        json={"email": "dup@test.com", "password": "StrongPass1!"},
    )
    response = await client.post(
        "/api/auth/register",
        json={"email": "dup@test.com", "password": "AnotherPass1!"},
    )
    assert response.status_code == 409


async def test_login_success(client: AsyncClient):
    """Test 3: POST /api/auth/login with valid credentials returns 200 with JWT."""
    await client.post(
        "/api/auth/register",
        json={"email": "login@test.com", "password": "StrongPass1!"},
    )
    response = await client.post(
        "/api/auth/login",
        data={"username": "login@test.com", "password": "StrongPass1!"},
    )
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["token_type"] == "bearer"
    assert len(data["access_token"]) > 0


async def test_login_invalid(client: AsyncClient):
    """Test 4: POST /api/auth/login with wrong password returns 401."""
    await client.post(
        "/api/auth/register",
        json={"email": "invalid@test.com", "password": "StrongPass1!"},
    )
    response = await client.post(
        "/api/auth/login",
        data={"username": "invalid@test.com", "password": "WrongPassword1!"},
    )
    assert response.status_code == 401


async def test_password_hashing(client: AsyncClient, test_db):
    """Test 5: Stored password is a bcrypt hash (starts with '$2b$')."""
    await client.post(
        "/api/auth/register",
        json={"email": "hash@test.com", "password": "StrongPass1!"},
    )
    # Read directly from the test database
    user = await test_db["users"].find_one({"email": "hash@test.com"})
    assert user is not None
    assert "hashed_password" in user
    assert user["hashed_password"].startswith("$2b$")


async def test_protected_endpoint(client: AsyncClient):
    """Test 6: Request without Bearer token to protected endpoint returns 401."""
    response = await client.get("/api/auth/me")
    assert response.status_code == 401
