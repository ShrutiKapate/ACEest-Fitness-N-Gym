"""Pytest suite for ACEest Fitness Flask app."""
import pytest
from app import create_app, calculate_calories, calculate_bmi


@pytest.fixture
def client(tmp_path):
    db = tmp_path / "test.db"
    app = create_app(db_path=str(db))
    app.config["TESTING"] = True
    return app.test_client()


def test_calories_fat_loss():
    assert calculate_calories(70, "Fat Loss") == 70 * 22


def test_calories_muscle_gain():
    assert calculate_calories(80, "Muscle Gain") == 80 * 35


def test_calories_unknown_program():
    with pytest.raises(ValueError):
        calculate_calories(70, "Yoga")


def test_calories_negative_weight():
    with pytest.raises(ValueError):
        calculate_calories(-5, "Beginner")


def test_bmi_normal():
    assert calculate_bmi(70, 175) == pytest.approx(22.86, abs=0.01)


def test_health_endpoint(client):
    r = client.get("/health")
    assert r.status_code == 200
    assert r.get_json()["status"] == "ok"


def test_version_endpoint(client):
    r = client.get("/version")
    assert r.status_code == 200


def test_programs_endpoint(client):
    r = client.get("/api/programs")
    assert r.status_code == 200
    assert "Fat Loss" in r.get_json()


def test_create_client(client):
    r = client.post("/api/clients", json={
        "name": "Ravi", "age": 28, "weight": 75, "program": "Fat Loss"
    })
    assert r.status_code == 201
    assert r.get_json()["calories"] == 75 * 22


def test_create_client_bad_payload(client):
    r = client.post("/api/clients", json={"name": "Ravi"})
    assert r.status_code == 400


def test_calories_endpoint(client):
    r = client.post("/api/calories", json={"weight": 70, "program": "Fat Loss"})
    assert r.status_code == 200
    assert r.get_json()["calories"] == 1540


def test_bmi_endpoint(client):
    r = client.post("/api/bmi", json={"weight": 70, "height": 175})
    assert r.status_code == 200
