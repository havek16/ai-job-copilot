import json

import pytest
from pydantic import BaseModel, Field

from src.llm_client import _parse_json_response, call_with_retry


class SampleOutput(BaseModel):
    name: str
    score: int = Field(ge=0, le=100)


def test_parse_json_response_strips_markdown_fences():
    raw = '```json\n{"name": "Acme", "score": 80}\n```'
    data = _parse_json_response(raw)
    assert data == {"name": "Acme", "score": 80}


def test_call_with_retry_succeeds_on_valid_response(mocker):
    mocker.patch(
        "src.llm_client._call_groq",
        return_value=json.dumps({"name": "Acme", "score": 75}),
    )

    result = call_with_retry("system", "user", SampleOutput, max_retries=0)

    assert result.name == "Acme"
    assert result.score == 75


def test_call_with_retry_retries_on_validation_failure(mocker):
    groq = mocker.patch("src.llm_client._call_groq")
    groq.side_effect = [
        json.dumps({"name": "Acme", "score": 200}),  # invalid score
        json.dumps({"name": "Acme", "score": 80}),
    ]
    mocker.patch("src.llm_client.time.sleep")  # skip back-off delay

    result = call_with_retry("system", "user", SampleOutput, max_retries=1)

    assert result.score == 80
    assert groq.call_count == 2


def test_call_with_retry_falls_back_to_gemini(mocker):
    mocker.patch("src.llm_client._call_groq", side_effect=RuntimeError("Groq down"))
    mocker.patch(
        "src.llm_client._call_gemini",
        return_value=json.dumps({"name": "Fallback Corp", "score": 60}),
    )

    result = call_with_retry("system", "user", SampleOutput, max_retries=0)

    assert result.name == "Fallback Corp"
    assert result.score == 60


def test_call_with_retry_raises_after_exhausting_retries(mocker):
    mocker.patch(
        "src.llm_client._call_groq",
        return_value='{"name": "Acme", "score": 999}',
    )
    mocker.patch("src.llm_client.time.sleep")

    with pytest.raises(RuntimeError, match="failed after"):
        call_with_retry("system", "user", SampleOutput, max_retries=1)
