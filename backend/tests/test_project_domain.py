from app.services.project_manager import DOMAINS, project_domain
from app.services.transcription_service import CAPTION_PROMPTS, caption_prompt


def test_caption_overlay_stays_on_until_it_is_turned_off():
    from app.core.models import ProjectSettings
    assert ProjectSettings().caption_overlay is True
    assert ProjectSettings.model_validate({"aspect_ratio": "16:9"}).caption_overlay is True
    assert ProjectSettings(caption_overlay=False).caption_overlay is False


def test_a_project_domain_is_one_of_the_offered_fields():
    assert project_domain("Medical") == "medical"
    assert project_domain("real estate") == "real_estate"
    assert project_domain("sports") == "sports"
    assert project_domain("cooking") == "general"


def test_every_domain_has_a_caption_prompt():
    assert set(CAPTION_PROMPTS) == set(DOMAINS)


def test_caption_prompt_follows_the_project_domain():
    assert "cancer" in caption_prompt("medical")
    assert "goal" in caption_prompt("sports")
    assert "mortgage" in caption_prompt("real_estate")
    assert "interest" in caption_prompt("finance")
    assert "faithfully" in caption_prompt("general")
    assert "cancer" not in caption_prompt("unknown")
