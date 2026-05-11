"""Contract tests for deterministic answer normalization."""

from services.lesson_ops import is_answer_correct, normalize_answer


def test_normalize_answer_applies_nfkc_width_and_japanese_punctuation():
    assert normalize_answer("Ｈｅｌｌｏ，　Ｗｏｒｌｄ！") == "hello, world!"
    assert normalize_answer("ありがとう。") == "ありがとう."


def test_accepted_answers_support_list_and_delimited_string():
    item_with_list = {"correct_answer": "I am fine.", "accepted_answers": ["I'm fine.", "I am OK."]}
    assert is_answer_correct("ｉ＇ｍ　ｆｉｎｅ．", item_with_list)
    assert is_answer_correct("I am ok.", item_with_list)

    item_with_string = {"correct_answer": "hello", "accepted_answers": "hi; hey | greetings"}
    assert is_answer_correct("HEY", item_with_string)
    assert is_answer_correct("greetings", item_with_string)


def test_wrong_answers_are_not_fuzzy_matched():
    item = {"correct_answer": "book", "accepted_answers": ["notebook"]}
    assert is_answer_correct("book", item)
    assert is_answer_correct("notebook", item)
    assert not is_answer_correct("books", item)
    assert not is_answer_correct("note book", item)
