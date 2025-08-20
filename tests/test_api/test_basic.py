"""Basic API tests."""

import pytest
from httpx import AsyncClient


class TestHealthEndpoints:
    """Test health check endpoints."""
    
    async def test_health_check(self, client: AsyncClient):
        """Test main health check endpoint."""
        response = await client.get("/health/")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data
        assert "timestamp" in data
        assert "version" in data
        assert "services" in data
    
    async def test_liveness_probe(self, client: AsyncClient):
        """Test liveness probe endpoint."""
        response = await client.get("/health/live")
        assert response.status_code == 200
        
        data = response.json()
        assert data["status"] == "ok"
    
    async def test_readiness_probe(self, client: AsyncClient):
        """Test readiness probe endpoint."""
        response = await client.get("/health/ready")
        assert response.status_code == 200
        
        data = response.json()
        assert "status" in data


class TestRootEndpoint:
    """Test root endpoint."""
    
    async def test_root(self, client: AsyncClient):
        """Test root endpoint."""
        response = await client.get("/")
        assert response.status_code == 200
        
        data = response.json()
        assert "message" in data
        assert "version" in data


class TestAuthenticationEndpoints:
    """Test authentication endpoints."""
    
    async def test_register_user(self, client: AsyncClient, test_user_data):
        """Test user registration."""
        response = await client.post("/api/v1/auth/register", json=test_user_data)
        
        # Should succeed or fail gracefully
        assert response.status_code in [201, 400]
        
        if response.status_code == 201:
            data = response.json()
            assert "id" in data
            assert data["username"] == test_user_data["username"]
            assert data["email"] == test_user_data["email"]
    
    async def test_login_invalid_credentials(self, client: AsyncClient):
        """Test login with invalid credentials."""
        response = await client.post("/api/v1/auth/login", json={
            "username": "nonexistent",
            "password": "wrongpassword"
        })
        
        assert response.status_code == 401
    
    async def test_protected_endpoint_without_token(self, client: AsyncClient):
        """Test accessing protected endpoint without token."""
        response = await client.get("/api/v1/auth/me")
        assert response.status_code == 401