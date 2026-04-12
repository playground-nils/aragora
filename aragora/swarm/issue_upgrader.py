"""Upgrade low-quality boss-ready issues into high-quality worker-ready specs.

Instead of filtering out hard issues, this module transforms them by:
1. Reading the target module to understand what it actually does
2. Identifying specific functions, dependencies, and test patterns
3. Rewriting the issue body with concrete guidance the worker can follow

This is the B1 (Assist) booster: the system drafts high-quality work orders
from vague inputs, so workers succeed instead of crashing.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from pathlib import Path

logger = logging.getLogger(__name__)


@dataclass
class UpgradedIssue:
    """An issue that's been enriched with concrete module analysis."""

    original_title: str
    original_body: str
    upgraded_title: str
    upgraded_body: str
    module_summary: str
    functions_found: list[str]
    loc: int
    imports: list[str]
    complexity: str  # "trivial", "simple", "medium", "complex"
    upgrade_method: str  # "llm" or "heuristic"


def _read_module(path: Path) -> str | None:
    """Read a module file, return content or None."""
    try:
        return path.read_text(encoding="utf-8", errors="replace")
    except OSError:
        return None


def _extract_functions(content: str) -> list[str]:
    """Extract public function and method names."""
    return [
        m.group(1)
        for m in re.finditer(r"(?:def|async def)\s+(\w+)\s*\(", content)
        if not m.group(1).startswith("_")
    ]


def _extract_classes(content: str) -> list[str]:
    """Extract class names."""
    return [m.group(1) for m in re.finditer(r"class\s+(\w+)\s*[:(]", content)]


def _extract_imports(content: str) -> list[str]:
    """Extract import statements."""
    imports: list[str] = []
    for line in content.splitlines():
        stripped = line.strip()
        if stripped.startswith("import ") or stripped.startswith("from "):
            imports.append(stripped)
    return imports


def _needs_mocking(imports: list[str]) -> list[str]:
    """Identify imports that likely need mocking in tests."""
    mock_hints: list[str] = []
    mock_patterns = [
        "redis",
        "postgres",
        "sqlite",
        "database",
        "db",
        "httpx",
        "requests",
        "aiohttp",
        "subprocess",
        "os.environ",
        "anthropic",
        "openai",
        "boto3",
        "s3",
    ]
    for imp in imports:
        imp_lower = imp.lower()
        for pattern in mock_patterns:
            if pattern in imp_lower:
                mock_hints.append(f"Mock `{imp.split()[-1]}` — external dependency")
                break
    return mock_hints


def _estimate_complexity(
    loc: int,
    num_functions: int,
    num_imports: int,
    has_async: bool,
) -> str:
    """Estimate testing complexity."""
    if loc < 30 and num_functions <= 3:
        return "trivial"
    if loc < 100 and num_functions <= 7 and num_imports < 5:
        return "simple"
    if loc < 300 and num_functions <= 15:
        return "medium"
    return "complex"


def upgrade_issue_heuristic(
    title: str,
    body: str,
    *,
    repo_root: Path,
) -> UpgradedIssue | None:
    """Upgrade an issue using heuristic module analysis (no LLM needed)."""
    # Extract the target module path from the issue
    path_match = re.search(r"`(aragora/\S+\.py)`", body)
    if not path_match:
        return None

    module_rel = path_match.group(1)
    module_path = repo_root / module_rel
    content = _read_module(module_path)
    if content is None:
        return None

    lines = content.splitlines()
    loc = len(lines)
    functions = _extract_functions(content)
    classes = _extract_classes(content)
    imports = _extract_imports(content)
    has_async = "async def" in content
    mock_hints = _needs_mocking(imports)
    complexity = _estimate_complexity(loc, len(functions), len(imports), has_async)

    # Extract docstring
    docstring = ""
    if '"""' in content:
        ds_match = re.search(r'"""(.*?)"""', content, re.DOTALL)
        if ds_match:
            docstring = ds_match.group(1).strip()[:200]

    # Build the test file path
    parts = Path(module_rel).parts
    if parts[0] == "aragora" and len(parts) >= 2:
        test_rel = str(Path("tests") / Path(*parts[1:-1]) / f"test_{parts[-1]}")
    else:
        test_rel = f"tests/test_{parts[-1]}"

    # Build upgraded body with concrete guidance
    func_list = (
        "\n".join(f"   - `{f}()`" for f in functions[:15])
        if functions
        else "   - (no public functions found)"
    )
    class_list = "\n".join(f"   - `{c}`" for c in classes) if classes else ""
    mock_list = (
        "\n".join(f"   - {m}" for m in mock_hints)
        if mock_hints
        else "   - No external dependencies to mock"
    )

    async_note = ""
    if has_async:
        async_note = "\n\n**Note:** This module uses `async def`. Use `pytest-asyncio` or wrap calls in `asyncio.run()` for testing."

    upgraded_body = f"""## Task

Write focused unit tests for `{module_rel}` ({loc} lines, {len(functions)} public functions).

{f"**Module purpose:** {docstring}" if docstring else ""}

### What to test

Public functions:
{func_list}
{f"{chr(10)}Classes:{chr(10)}{class_list}" if class_list else ""}

### Mocking requirements
{mock_list}
{async_note}

### Complexity: {complexity}
{f"This is a {complexity} module. " if complexity == "trivial" else ""}{f"Focus on the {len(functions)} public functions — keep tests simple and direct." if complexity in ("trivial", "simple") else f"This module has {len(functions)} functions and {len(imports)} imports. Prioritize the most important public API surface."}

### File Scope
- `{module_rel}`
- `{test_rel}` (create)

### Validation
```bash
pytest {test_rel} -v
```

### Acceptance Criteria
- All tests pass
- At least {min(len(functions) * 2, 12)} test functions
- No external service calls (mock all dependencies)
- Tests complete in under 10 seconds

### Constraints
- Single-file change preferred
- Estimated complexity: {complexity}"""

    upgraded_title = f"Add unit tests for {'/'.join(parts[1:])}" if len(parts) > 1 else title

    return UpgradedIssue(
        original_title=title,
        original_body=body,
        upgraded_title=upgraded_title,
        upgraded_body=upgraded_body,
        module_summary=docstring,
        functions_found=functions,
        loc=loc,
        imports=[i.split()[-1] for i in imports[:10]],
        complexity=complexity,
        upgrade_method="heuristic",
    )


async def upgrade_issue_llm(
    title: str,
    body: str,
    *,
    repo_root: Path,
    model: str = "claude-haiku-4-5-20251001",
    timeout: float = 20.0,
) -> UpgradedIssue | None:
    """Upgrade an issue using LLM analysis for richer understanding."""
    # First do the heuristic analysis for the module data
    heuristic = upgrade_issue_heuristic(title, body, repo_root=repo_root)
    if heuristic is None:
        return None

    # Extract module path and content for LLM context
    path_match = re.search(r"`(aragora/\S+\.py)`", body)
    if not path_match:
        return heuristic  # Fall back to heuristic

    module_rel = path_match.group(1)
    module_path = repo_root / module_rel
    content = _read_module(module_path)
    if content is None:
        return heuristic

    # Truncate for LLM context
    content_truncated = content[:4000]

    prompt = f"""Analyze this Python module and suggest specific test cases.

Module: {module_rel} ({heuristic.loc} lines)
Public functions: {", ".join(heuristic.functions_found[:10])}
Complexity: {heuristic.complexity}

```python
{content_truncated}
```

Return a JSON object with:
{{
  "module_purpose": "one sentence describing what this module does",
  "test_cases": [
    {{"name": "test_function_name", "description": "what to test", "approach": "how to test it"}}
  ],
  "mock_strategy": "what needs mocking and why",
  "edge_cases": ["list of edge cases to cover"]
}}"""

    text: str | None = None
    try:
        api_key = os.environ.get("ANTHROPIC_API_KEY")
        if api_key:
            import anthropic

            client = anthropic.AsyncAnthropic()
            response = await client.messages.create(
                model=model,
                max_tokens=512,
                messages=[{"role": "user", "content": prompt}],
                timeout=timeout,
            )
            text = response.content[0].text.strip()
    except Exception as exc:
        logger.debug("LLM upgrade unavailable: %s", exc)

    if text is None:
        try:
            or_key = os.environ.get("OPENROUTER_API_KEY")
            if or_key:
                import httpx

                async with httpx.AsyncClient(timeout=timeout) as http:
                    resp = await http.post(
                        "https://openrouter.ai/api/v1/chat/completions",
                        headers={
                            "Authorization": f"Bearer {or_key}",
                            "Content-Type": "application/json",
                        },
                        json={
                            "model": "anthropic/claude-haiku-4.5",
                            "max_tokens": 512,
                            "messages": [{"role": "user", "content": prompt}],
                        },
                    )
                    resp.raise_for_status()
                    text = resp.json()["choices"][0]["message"]["content"].strip()
        except Exception as exc:
            logger.debug("OpenRouter upgrade unavailable: %s", exc)

    if text is None:
        return heuristic  # Fall back

    # Parse LLM response and enrich the heuristic body
    import json as _json

    try:
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        data = _json.loads(text)

        purpose = data.get("module_purpose", heuristic.module_summary)
        test_cases = data.get("test_cases", [])
        mock_strategy = data.get("mock_strategy", "")
        edge_cases = data.get("edge_cases", [])

        # Enrich the body with LLM insights
        tc_lines = "\n".join(
            f"   - `{tc['name']}`: {tc['description']}"
            for tc in test_cases[:10]
            if isinstance(tc, dict)
        )
        edge_lines = "\n".join(f"   - {e}" for e in edge_cases[:5]) if edge_cases else ""

        enrichment = ""
        if tc_lines:
            enrichment += f"\n\n### Suggested test cases\n{tc_lines}"
        if mock_strategy:
            enrichment += f"\n\n### Mocking strategy\n{mock_strategy}"
        if edge_lines:
            enrichment += f"\n\n### Edge cases to cover\n{edge_lines}"

        # Replace module purpose if LLM gave a better one
        upgraded_body = heuristic.upgraded_body
        if purpose and "Module purpose:" not in upgraded_body:
            upgraded_body = upgraded_body.replace(
                "## Task", f"## Task\n\n**Module purpose:** {purpose}", 1
            )
        upgraded_body += enrichment

        return UpgradedIssue(
            original_title=heuristic.original_title,
            original_body=heuristic.original_body,
            upgraded_title=heuristic.upgraded_title,
            upgraded_body=upgraded_body,
            module_summary=purpose or heuristic.module_summary,
            functions_found=heuristic.functions_found,
            loc=heuristic.loc,
            imports=heuristic.imports,
            complexity=heuristic.complexity,
            upgrade_method="llm",
        )
    except (_json.JSONDecodeError, KeyError, IndexError):
        return heuristic  # Fall back on parse failure
