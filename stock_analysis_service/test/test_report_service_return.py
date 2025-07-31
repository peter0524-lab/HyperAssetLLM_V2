import pytest
import httpx
import asyncio
import uvicorn
from multiprocessing import Process
import time
import os

# Assuming the report_service.py is structured to be importable
# For testing, we might need to adjust sys.path or import directly
# from stock_analysis_service.services.report_service.report_service import app as report_app

# To run the FastAPI app in a separate process for testing
def run_fastapi_app():
    # Ensure the correct working directory for the service
    original_cwd = os.getcwd()
    service_dir = os.path.join(original_cwd, "stock_analysis_service", "services", "report_service")
    os.chdir(service_dir)
    try:
        # Import app after changing directory to resolve relative imports within the service
        from report_service import app as report_app
        uvicorn.run(report_app, host="127.0.0.1", port=8004, log_level="info")
    finally:
        os.chdir(original_cwd)

@pytest.fixture(scope="module")
def fastapi_process():
    proc = Process(target=run_fastapi_app)
    proc.start()
    time.sleep(5)  # Give the server some time to start
    yield
    proc.terminate()
    proc.join()

@pytest.mark.asyncio
async def test_report_service_returns_telegram_message(fastapi_process):
    async with httpx.AsyncClient(base_url="http://127.0.0.1:8004") as client:
        headers = {"X-User-ID": "test_user_123"}
        response = await client.post("/execute", headers=headers, timeout=600) # Increased timeout

        assert response.status_code == 200
        data = response.json()

        assert data["success"] is True
        assert "telegram_message" in data
        assert data["telegram_message"] is not None
        assert isinstance(data["telegram_message"], str)
        assert len(data["telegram_message"]) > 0
        print(f"Received telegram_message: {data['telegram_message']}")

