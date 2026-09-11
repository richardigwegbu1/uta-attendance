import os
import tempfile

import pytest

from app import app, init_db


@pytest.fixture
def client():
    fd, path = tempfile.mkstemp()

    app.config.update(
        TESTING=True,
        DATABASE=path,
        SECRET_KEY="test-key",
    )

    with app.app_context():
        init_db()

    with app.test_client() as client:
        yield client

    os.close(fd)
    os.unlink(path)


def test_health(client):
    response = client.get("/health")

    assert response.status_code == 200
    assert response.get_json()["status"] == "ok"


def test_register_login_and_attendance(client):
    client.post(
        "/register",
        data={
            "full_name": "UTA Student",
            "email": "student@example.com",
            "password": "StrongPass123!",
        },
    )

    login = client.post(
        "/login",
        data={
            "email": "student@example.com",
            "password": "StrongPass123!",
        },
        follow_redirects=True,
    )

    assert login.status_code == 200
    assert b"Welcome" in login.data

    attendance = client.post(
        "/attendance",
        follow_redirects=True,
    )

    assert attendance.status_code == 200
    assert b"Attendance recorded successfully" in attendance.data
