from app.services.project_manager import project_domain
from app.services.transcription_service import caption_prompt


def test_a_project_domain_is_one_of_the_three_fields():
    assert project_domain("Medical") == "medical"
    assert project_domain("sports") == "sports"
    assert project_domain("cooking") == "general"


def test_caption_prompt_follows_the_project_domain():
    assert "cancer" in caption_prompt("medical")
    assert "goal" in caption_prompt("sports")
    assert "faithfully" in caption_prompt("general")
    assert "cancer" not in caption_prompt("unknown")
