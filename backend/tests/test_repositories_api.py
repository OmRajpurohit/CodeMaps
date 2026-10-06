import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_repository_success(client: AsyncClient):
    payload = {
        "url": "https://github.com/octocat/Hello-World.git",
        "name": "Hello-World",
        "default_branch": "master",
    }
    response = await client.post("/api/v1/repositories", json=payload)
    assert response.status_code == 201
    data = response.json()
    assert data["url"] == payload["url"]
    assert data["name"] == "Hello-World"
    assert "id" in data


@pytest.mark.asyncio
async def test_register_repository_idempotent(client: AsyncClient):
    payload = {
        "url": "https://github.com/psf/requests.git",
        "name": "requests",
    }
    res1 = await client.post("/api/v1/repositories", json=payload)
    assert res1.status_code == 201

    res2 = await client.post("/api/v1/repositories", json=payload)
    assert res2.status_code == 201
    assert res1.json()["id"] == res2.json()["id"]


@pytest.mark.asyncio
async def test_register_repository_rejects_malicious_url(client: AsyncClient):
    payload = {
        "url": "https://github.com/bad/repo; cat /etc/shadow",
    }
    response = await client.post("/api/v1/repositories", json=payload)
    assert response.status_code == 400
    assert "Security violation" in response.json()["detail"]


@pytest.mark.asyncio
async def test_list_repositories(client: AsyncClient):
    # Register two repositories
    await client.post(
        "/api/v1/repositories",
        json={"url": "https://github.com/org/repo-a.git", "name": "repo-a"},
    )
    await client.post(
        "/api/v1/repositories",
        json={"url": "https://github.com/org/repo-b.git", "name": "repo-b"},
    )

    response = await client.get("/api/v1/repositories")
    assert response.status_code == 200
    repos = response.json()
    assert len(repos) >= 2


@pytest.mark.asyncio
async def test_get_repository_by_id(client: AsyncClient):
    created = await client.post(
        "/api/v1/repositories",
        json={"url": "https://github.com/org/target-repo.git", "name": "target"},
    )
    repo_id = created.json()["id"]

    response = await client.get(f"/api/v1/repositories/{repo_id}")
    assert response.status_code == 200
    assert response.json()["id"] == repo_id
    assert response.json()["name"] == "target"


@pytest.mark.asyncio
async def test_delete_repository(client: AsyncClient):
    created = await client.post(
        "/api/v1/repositories",
        json={"url": "https://github.com/org/delete-me.git", "name": "delete-me"},
    )
    repo_id = created.json()["id"]

    del_res = await client.delete(f"/api/v1/repositories/{repo_id}")
    assert del_res.status_code == 204

    get_res = await client.get(f"/api/v1/repositories/{repo_id}")
    assert get_res.status_code == 404
