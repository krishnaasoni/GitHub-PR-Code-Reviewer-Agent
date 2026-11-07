"""Unit test verification for Telegram PR Reviewer helper functions.
Tests pure logic functions without requiring external network dependencies.
"""

import re
from typing import List, Optional, Tuple

GITHUB_PR_REGEX = re.compile(
    r"https?://github\.com/(?P<owner>[\w\-\.]+)/(?P<repo>[\w\-\.]+)/pull/(?P<number>\d+)",
    re.IGNORECASE,
)

CODE_SNIPPET_INDICATORS = [
    "def ", "class ", "import ", "from ", "return ", "function", "const ", "let ",
    "var ", "public ", "private ", "void ", "async ", "await ", "fn ", "struct ",
    "impl ", "package ", "SELECT ", "INSERT ", "UPDATE ", "DELETE ", "diff --git",
    "--- a/", "+++ b/", "@@ -",
]


def extract_github_pr_url(text: str) -> Optional[Tuple[str, str, str, str]]:
    match = GITHUB_PR_REGEX.search(text)
    if match:
        return (
            match.group(0),
            match.group("owner"),
            match.group("repo"),
            match.group("number"),
        )
    return None


def is_code_or_diff(text: str) -> bool:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        return True
    if any(stripped.startswith(prefix) for prefix in ["diff --git", "--- a/", "+++ b/", "@@"]):
        return True

    matches = sum(1 for indicator in CODE_SNIPPET_INDICATORS if indicator in text)
    if matches >= 2:
        return True

    lines = stripped.splitlines()
    if len(lines) >= 3 and any(char in stripped for char in ("{", "}", ";", "()", "->", "=>")):
        return True

    return False


def clean_code_snippet(text: str) -> str:
    stripped = text.strip()
    if stripped.startswith("```") and stripped.endswith("```"):
        lines = stripped.splitlines()
        if len(lines) >= 2:
            return "\n".join(lines[1:-1]).strip()
    return stripped


def split_telegram_message(text: str, max_length: int = 4000) -> List[str]:
    if len(text) <= max_length:
        return [text]

    chunks: List[str] = []
    current_chunk = ""

    for paragraph in text.split("\n\n"):
        if len(current_chunk) + len(paragraph) + 2 <= max_length:
            current_chunk = f"{current_chunk}\n\n{paragraph}" if current_chunk else paragraph
        else:
            if current_chunk:
                chunks.append(current_chunk)
            if len(paragraph) > max_length:
                lines = paragraph.splitlines()
                sub_chunk = ""
                for line in lines:
                    if len(sub_chunk) + len(line) + 1 <= max_length:
                        sub_chunk = f"{sub_chunk}\n{line}" if sub_chunk else line
                    else:
                        if sub_chunk:
                            chunks.append(sub_chunk)
                        sub_chunk = line
                if sub_chunk:
                    current_chunk = sub_chunk
                else:
                    current_chunk = ""
            else:
                current_chunk = paragraph

    if current_chunk:
        chunks.append(current_chunk)

    return chunks


def run_all_tests():
    # 1. PR Regex tests
    cases = [
        ("Check this: https://github.com/fastapi/fastapi/pull/1234", "fastapi", "fastapi", "1234"),
        ("Review https://github.com/django/django/pull/99/files now", "django", "django", "99"),
        ("http://github.com/pytorch/pytorch/pull/55555", "pytorch", "pytorch", "55555"),
    ]
    for text, exp_owner, exp_repo, exp_num in cases:
        result = extract_github_pr_url(text)
        assert result is not None, f"Failed on {text}"
        _, owner, repo, num = result
        assert owner == exp_owner and repo == exp_repo and num == exp_num, f"Mismatch on {text}"
    print("✔ GitHub PR regex tests passed!")

    # 2. Code detection tests
    assert is_code_or_diff("def foo(x):\n    return x + 1")
    assert is_code_or_diff("```python\nx = 1\n```")
    assert is_code_or_diff("diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py")
    assert is_code_or_diff("SELECT id, name FROM users WHERE role = 'admin'; UPDATE users SET active = 1")
    assert not is_code_or_diff("Hello there, how are you doing today?")
    assert not is_code_or_diff("What can this bot do?")
    print("✔ Code snippet detection tests passed!")

    # 3. Code cleaning tests
    wrapped = "```python\ndef test():\n    pass\n```"
    assert clean_code_snippet(wrapped) == "def test():\n    pass"
    raw = "def test():\n    pass"
    assert clean_code_snippet(raw) == raw
    print("✔ Code snippet cleaning tests passed!")

    # 4. Message splitting tests
    short_text = "Hello world"
    assert split_telegram_message(short_text, max_length=100) == [short_text]
    long_text = "Part 1\n\n" + ("A" * 80) + "\n\nPart 2\n\n" + ("B" * 80)
    chunks = split_telegram_message(long_text, max_length=100)
    assert len(chunks) >= 2
    for chunk in chunks:
        assert len(chunk) <= 100
    print("✔ Message splitting tests passed!")

    print("\n🎉 ALL LOGIC & PARSING TESTS PASSED PERFECTLY!")


if __name__ == "__main__":
    run_all_tests()
