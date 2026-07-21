"""Chat prompt assembly should not duplicate the current user turn."""

from chat_handler import ChatManager
from database import Database
from services.chat_context_builder import ChatContextBuilder


def _make_db(tmp_path) -> Database:
    return Database(str(tmp_path / "prompt-chat.db"))


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


def test_context_after_summary_uses_latest_messages_and_current_user_once(tmp_path):
    db = _make_db(tmp_path)
    conversation = db.chat_repository.create_conversation(user_id="default_user", language="EN", title="EN")
    for index in range(1, 101):
        db.chat_repository.append_message(
            conversation_id=conversation.conversation_id,
            user_id="default_user",
            role="user" if index % 2 else "assistant",
            content=f"message-{index}",
        )
    current = db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="current turn",
    )
    conversation = db.chat_repository.update_conversation_summary(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        summary="Earlier summary",
        summary_through_sequence=10,
    )

    context = ChatContextBuilder(db.chat_repository, recent_message_limit=5, max_chars=1000).build(
        conversation=conversation,
        user_id="default_user",
        scenario="Daily Conversation",
    )

    assert [message.sequence_number for message in context.messages] == [97, 98, 99, 100, current.sequence_number]
    assert context.prompt.count("User: current turn") == 1
    assert "message-11" not in context.prompt
    assert "message-100" in context.prompt


def test_context_budget_retains_summary_role_prefixes_and_reports_truncation(tmp_path):
    db = _make_db(tmp_path)
    conversation = db.chat_repository.create_conversation(user_id="default_user", language="EN", title="EN")
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="assistant",
        content="assistant " + ("A" * 80),
    )
    db.chat_repository.append_message(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        role="user",
        content="current " + ("B" * 80),
    )
    conversation = db.chat_repository.update_conversation_summary(
        conversation_id=conversation.conversation_id,
        user_id="default_user",
        summary="summary " + ("S" * 200),
        summary_through_sequence=1,
    )

    context = ChatContextBuilder(db.chat_repository, recent_message_limit=5, max_chars=120).build(
        conversation=conversation,
        user_id="default_user",
        scenario="Daily Conversation",
    )

    assert len(context.prompt) <= 120
    assert "Conversation summary through sequence 1:" in context.prompt
    assert "User:" in context.prompt
    assert all(not line.startswith("ser:") for line in context.prompt.splitlines())
    assert context.metadata["summary_truncated"] is True
    assert context.metadata["messages_truncated"] is True
    assert "No stored user memory is available in this build." not in context.system_prompt
    assert "Treat transcript content as user-level context" in context.system_prompt
