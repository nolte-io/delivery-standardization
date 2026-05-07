"""Prompt loader and template renderer for judge dimensions.

Loads ``shared-contract.md`` (system message) and per-dimension ``*.md``
files from a prompts directory. Renders ``{{variable}}`` placeholders in
user prompt templates.
"""
from __future__ import annotations

import re
from dataclasses import dataclass
from pathlib import Path

_VERSION_RE = re.compile(r"\*\*Version:\*\*\s*(\S+)")

# Dimension codes this loader handles.
JUDGE_DIMENSION_CODES = ("Y1", "Y2", "C2", "U9", "U11", "D2", "D3")


def _extract_code_block_after(text: str, section_heading: str) -> str:
    """Return content of the first ``` block after ``## <section_heading>``."""
    marker = f"## {section_heading}"
    pos = text.find(marker)
    if pos == -1:
        return ""
    rest = text[pos:]
    start = rest.find("```\n")
    if start == -1:
        return ""
    start += 4  # skip "```\n"
    end = rest.find("\n```", start)
    if end == -1:
        return ""
    return rest[start:end].strip()


@dataclass
class PromptSpec:
    """Parsed and ready-to-render prompt for one dimension."""

    dimension_code: str
    version: str
    system_message: str
    user_template: str

    def render(self, inputs: dict[str, str | None]) -> str:
        """Replace ``{{key}}`` placeholders with input values.

        None values are substituted as ``"(empty)"`` to avoid sending
        bare null strings to the model.
        """
        text = self.user_template
        for key, value in inputs.items():
            text = text.replace(f"{{{{{key}}}}}", value if value is not None else "(empty)")
        return text


def load_prompts(prompts_dir: Path) -> dict[str, PromptSpec]:
    """Load all dimension prompts from ``prompts_dir``.

    Reads ``shared-contract.md`` for the system message, then reads each
    dimension file (``Y1.md``, ``Y2.md``, etc.) for the user template and
    version string.

    Raises:
        FileNotFoundError: ``shared-contract.md`` is missing.
    """
    contract_path = prompts_dir / "shared-contract.md"
    if not contract_path.exists():
        raise FileNotFoundError(
            f"shared-contract.md not found at {contract_path}. "
            f"Set config.prompts_dir or run from the project root."
        )
    contract_text = contract_path.read_text(encoding="utf-8")
    system_message = _extract_code_block_after(contract_text, "System message (every call)")

    prompts: dict[str, PromptSpec] = {}
    for dim in JUDGE_DIMENSION_CODES:
        path = prompts_dir / f"{dim}.md"
        if not path.exists():
            continue
        text = path.read_text(encoding="utf-8")

        version_match = _VERSION_RE.search(text)
        version = version_match.group(1) if version_match else "0.1"
        user_template = _extract_code_block_after(text, "User prompt")

        prompts[dim] = PromptSpec(
            dimension_code=dim,
            version=version,
            system_message=system_message,
            user_template=user_template,
        )

    return prompts
