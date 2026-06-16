"""Chat prompt assembly should not duplicate the current user turn."""

from chat_handler import ChatManager


def test_chat_prompt_does_not_duplicate_new_user_turn():
    manager = ChatManager()
    history = [
        {"role": "system", "content": "system prompt"},
        {"role": "user", "content": "old message"},
        {"role": "assistant", "content": "old response"},
    ]

    prompt = manager.build_prompt(history, "hello")

    assert prompt.count("User: hello") == 1
    assert prompt.endswith("User: hello")
    assert history[-1] == {"role": "assistant", "content": "old response"}
