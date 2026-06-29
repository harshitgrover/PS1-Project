import json
from fastapi.testclient import TestClient
from main import app

client = TestClient(app)

def test_health():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json() == {"status": "ok"}
    print("Health check passed.")

def test_verify_pass():
    with open("demo_inputs/shell_pass.json") as f:
        data = json.load(f)
    response = client.post("/verify", json=data)
    assert response.status_code == 200
    res = response.json()
    assert res["result"] == "SAT"
    assert len(res["hard_violations"]) == 0
    print("Verify pass test passed.")

def test_dynamic_seattle():
    with open("demo_inputs/dynamic_seattle.json") as f:
        data = json.load(f)
    response = client.post("/verify", json=data)
    assert response.status_code == 200
    res = response.json()
    assert res["result"] == "SAT"
    assert len(res["hard_violations"]) == 0
    print("Verify dynamic seattle test passed.")

def test_dynamic_bellevue():
    with open("demo_inputs/dynamic_bellevue.json") as f:
        data = json.load(f)
    response = client.post("/verify", json=data)
    assert response.status_code == 200
    res = response.json()
    assert res["result"] == "SAT"
    assert len(res["hard_violations"]) == 0
    print("Verify dynamic bellevue test passed.")

def test_verify_fail():
    with open("demo_inputs/shell_fail_setback.json") as f:
        data = json.load(f)
    response = client.post("/verify", json=data)
    assert response.status_code == 200
    res = response.json()
    assert res["result"] == "UNSAT"
    assert len(res["hard_violations"]) > 0
    assert "corrected_coordinates" not in res["hard_violations"][0]
    print("Verify fail test passed.")

if __name__ == "__main__":
    test_health()
    test_verify_pass()
    test_dynamic_seattle()
    test_dynamic_bellevue()
    test_verify_fail()
    print("All tests passed!")
