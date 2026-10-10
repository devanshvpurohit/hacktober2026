"""
CircuitForge AI - End-to-End API Integration Test
Tests the complete lifecycle of a project through the FastAPI backend:
1. Health & System endpoints
2. Catalog lookup
3. Project creation
4. AI/Deterministic planning
5. Code & Diagram generation
6. Structural & Hardware validation
7. BOM calculation & pricing verification
8. ZIP export and archive integrity
9. Wokwi simulation workflow
10. Project persistence & deletion
"""
import os
import sys
import json
import zipfile
import pytest
from io import BytesIO

sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', '..', 'apps', 'backend'))

from fastapi.testclient import TestClient
from main import app
from storage.db import init_db
import asyncio

asyncio.run(init_db())
client = TestClient(app)


def test_health_endpoint():
    res = client.get("/api/health")
    assert res.status_code == 200
    data = res.json()
    assert data["status"] == "ok"
    assert "ollama_running" in data
    assert "arduino_cli_available" in data


def test_system_endpoint():
    res = client.get("/api/system")
    assert res.status_code == 200
    data = res.json()
    assert "os" in data
    assert "arduino_cli" in data
    assert "models" in data


def test_catalog_endpoint():
    res = client.get("/api/catalog")
    assert res.status_code == 200
    items = res.json()
    assert len(items) >= 7
    ids = [i["id"] for i in items]
    assert "esp32_devkitv1" in ids
    assert "dht22" in ids
    assert "led_red" in ids


def test_complete_project_lifecycle():
    # 1. Create project
    create_res = client.post("/api/projects", json={
        "user_request": "Create an ESP32-based temperature monitor using a DHT22 sensor. Turn on an LED when the temperature exceeds 30 degrees Celsius."
    })
    assert create_res.status_code == 201
    project = create_res.json()
    project_id = project["id"]
    assert project["status"] == "created"

    # 2. Plan project
    plan_res = client.post(f"/api/projects/{project_id}/plan")
    assert plan_res.status_code == 200
    planned_proj = plan_res.json()
    assert planned_proj["status"] == "planned"
    assert planned_proj["spec"] is not None
    assert len(planned_proj["spec"]["components"]) >= 2
    assert planned_proj["bom"] is not None
    assert planned_proj["bom"]["total_inr"] > 0

    # 3. Generate firmware & diagram
    gen_res = client.post(f"/api/projects/{project_id}/generate")
    assert gen_res.status_code == 200
    gen_proj = gen_res.json()
    assert gen_proj["status"] == "generated"
    assert gen_proj["firmware_code"] is not None
    assert "setup()" in gen_proj["firmware_code"]
    assert gen_proj["diagram_json"] is not None
    assert "parts" in gen_proj["diagram_json"]

    # 4. Validate project
    val_res = client.post(f"/api/projects/{project_id}/validate")
    assert val_res.status_code == 200
    val_data = val_res.json()
    assert val_data["validation"]["valid"] is True

    # 5. Get BOM
    bom_res = client.get(f"/api/projects/{project_id}/bom")
    assert bom_res.status_code == 200
    bom_data = bom_res.json()
    assert bom_data["currency"] == "INR"
    assert len(bom_data["lines"]) >= 2

    # 6. Test simulation workflow endpoint
    sim_res = client.post(f"/api/projects/{project_id}/simulate")
    assert sim_res.status_code == 200
    sim_data = sim_res.json()
    assert "simulation_status" in sim_data

    # 7. Download ZIP export
    dl_res = client.get(f"/api/projects/{project_id}/download")
    assert dl_res.status_code == 200
    assert dl_res.headers["content-type"] == "application/zip"

    # Verify ZIP integrity
    zf = zipfile.ZipFile(BytesIO(dl_res.content))
    names = zf.namelist()
    assert any("sketch.ino" in n for n in names)
    assert any("diagram.json" in n for n in names)
    assert any("project.json" in n for n in names)
    assert any("README.md" in n for n in names)

    # 8. Verify project persistence
    get_res = client.get(f"/api/projects/{project_id}")
    assert get_res.status_code == 200
    assert get_res.json()["id"] == project_id

    # 9. Clean up
    del_res = client.delete(f"/api/projects/{project_id}")
    assert del_res.status_code == 200
    assert del_res.json()["deleted"] is True


if __name__ == '__main__':
    test_health_endpoint()
    print("PASS: Health endpoint")
    test_system_endpoint()
    print("PASS: System endpoint")
    test_catalog_endpoint()
    print("PASS: Catalog endpoint")
    test_complete_project_lifecycle()
    print("PASS: Complete project lifecycle (Create -> Plan -> Generate -> Validate -> BOM -> Export -> Delete)")
    print("\nALL END-TO-END TESTS PASSED!")
