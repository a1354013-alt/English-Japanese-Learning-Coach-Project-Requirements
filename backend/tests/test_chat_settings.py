from __future__ import annotations

import pytest
from config import Settings
from pydantic import ValidationError


@pytest.mark.parametrize(
    "overrides",
    (
        {"chat_recent_message_limit": 0},
        {"chat_context_max_chars": 99},
        {"chat_message_max_chars": 0},
        {"chat_assistant_response_max_chars": 0},
        {"chat_client_message_id_max_chars": 251},
    ),
)
def test_chat_runtime_settings_validate_positive_safe_limits(overrides):
    with pytest.raises(ValidationError):
        Settings(_env_file=None, **overrides)


def test_chat_runtime_settings_allow_idempotency_compatible_client_message_limit():
    settings = Settings(_env_file=None, chat_client_message_id_max_chars=250)

    assert settings.chat_client_message_id_max_chars == 250
