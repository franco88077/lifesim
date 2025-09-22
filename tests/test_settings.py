from __future__ import annotations

from app.settings.services import get_app_settings


def test_settings_page_renders(client):
    """The settings console should load successfully."""

    response = client.get("/settings/")

    assert response.status_code == 200
    assert b"System Preferences" in response.data
    assert b"Active timezone" in response.data


def test_settings_timezone_update(client, app):
    """Submitting a timezone selection should persist the change."""

    response = client.post("/settings/", data={"timezone": "America/New_York"})

    assert response.status_code == 200
    assert b"Timezone updated" in response.data

    with app.app_context():
        settings = get_app_settings()
        assert settings.timezone == "America/New_York"
