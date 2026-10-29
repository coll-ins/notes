import pytest

from app import create_app
from config import TestConfig
from models import db


@pytest.fixture
def client():
    app = create_app(TestConfig)
    with app.app_context():
        db.create_all()
        yield app.test_client()
        db.session.remove()
        db.drop_all()


def signup(client, username="alice", password="secret123"):
    return client.post("/signup", json={"username": username, "password": password})


def test_signup_login_logout_check_session(client):
    assert client.get("/check_session").status_code == 401
    assert signup(client).status_code == 201
    assert client.get("/check_session").json["username"] == "alice"
    assert client.delete("/logout").status_code == 204
    assert client.get("/check_session").status_code == 401
    assert client.post("/login", json={"username": "alice", "password": "nope"}).status_code == 401
    r = client.post("/login", json={"username": "alice", "password": "secret123"})
    assert r.status_code == 200
    assert "password" not in r.json and "_password_hash" not in r.json


def test_signup_validation(client):
    assert signup(client).status_code == 201
    assert signup(client).status_code == 422
    assert signup(client, "ab").status_code == 422
    assert signup(client, "bob", "123").status_code == 422
    assert client.post("/signup", json={}).status_code == 422


def test_notes_require_auth(client):
    assert client.get("/notes").status_code == 401
    assert client.post("/notes", json={"title": "x"}).status_code == 401
    assert client.get("/notes/1").status_code == 401


def test_crud(client):
    signup(client)
    r = client.post("/notes", json={"title": "Hello", "content": "World"})
    assert r.status_code == 201
    nid = r.json["id"]
    assert client.post("/notes", json={"content": "no title"}).status_code == 422
    assert client.get(f"/notes/{nid}").json["title"] == "Hello"
    r = client.patch(f"/notes/{nid}", json={"is_pinned": True, "category": "work"})
    assert r.status_code == 200 and r.json["is_pinned"] and r.json["title"] == "Hello"
    assert client.patch(f"/notes/{nid}", json={"title": ""}).status_code == 422
    assert client.delete(f"/notes/{nid}").status_code == 204
    assert client.get(f"/notes/{nid}").status_code == 404


def test_ownership(client):
    signup(client, "alice")
    nid = client.post("/notes", json={"title": "private"}).json["id"]
    client.delete("/logout")
    signup(client, "bob")
    assert client.get("/notes").json["total"] == 0
    assert client.get(f"/notes/{nid}").status_code == 404
    assert client.patch(f"/notes/{nid}", json={"title": "hacked"}).status_code == 404
    assert client.delete(f"/notes/{nid}").status_code == 404


def test_pagination(client):
    signup(client)
    for i in range(7):
        client.post("/notes", json={"title": f"n{i}"})
    r = client.get("/notes?page=2&per_page=3").json
    assert (r["page"], r["per_page"], r["total"], r["pages"], len(r["items"])) == (2, 3, 7, 3, 3)
    assert len(client.get("/notes?page=3&per_page=3").json["items"]) == 1
