from backend.app.core.config import Settings


def test_settings_defaults():
    s = Settings()
    assert s.PROJECT_NAME == "CodeAtlas"
    assert s.VERSION == "0.1.0"
    assert s.API_V1_STR == "/api/v1"
    assert len(s.CORS_ORIGINS) > 0
    assert s.MAX_REPO_SIZE_MB == 250


def test_settings_cors_string_parsing():
    s = Settings(CORS_ORIGINS="http://localhost:3000,http://example.com")
    assert "http://localhost:3000" in s.CORS_ORIGINS
    assert "http://example.com" in s.CORS_ORIGINS
