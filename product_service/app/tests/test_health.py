# product_service/app/tests/test_health.py
from fastapi.testclient import TestClient
from app.main import app

# Instantiate FastAPI's native TestClient
client = TestClient(app)

def test_health_check_endpoint():
    """
    Automated integration test verifying that the health check
    returns a 200 OK status and correct JSON data.
    """
    response = client.get("/")
    assert response.status_code == 200
    assert response.json() == {"status": "healthy", "service": "product-service"}