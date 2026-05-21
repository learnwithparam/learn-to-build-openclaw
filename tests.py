#!/usr/bin/env python3
"""
tests.py — Automated tests for the OpenClaw workshop.

Verifies that all 10 modules are properly structured and functional:
  1. Required files exist in each module folder
  2. Python files have valid syntax (compile check)
  3. README/GUIDE/EXERCISES files are non-empty and have expected sections
  4. Makefile has all required targets
  5. Top-level files exist
  6. Module code compiles without syntax errors

Run: make test
  or: uv run python tests.py
"""
import ast
from pathlib import Path

WORKSHOP_DIR = Path(__file__).parent
PASS = "\033[32m✓\033[0m"
FAIL = "\033[31m✗\033[0m"

results = {"passed": 0, "failed": 0, "errors": []}


def check(description: str, condition: bool, detail: str = ""):
    """Record a test result."""
    if condition:
        results["passed"] += 1
        print(f"  {PASS} {description}")
    else:
        results["failed"] += 1
        msg = f"{description}: {detail}" if detail else description
        results["errors"].append(msg)
        print(f"  {FAIL} {description}" + (f" — {detail}" if detail else ""))


# --- Module definitions ---

MODULES = [
    {
        "dir": "01-simplest-bot",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "02-persistent-sessions",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "03-personality-soul",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": ["SOUL.md"],
    },
    {
        "dir": "04-tools-agent-loop",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "05-permission-controls",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "06-gateway",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "07-context-compaction",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "08-long-term-memory",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "09-concurrency-scheduling",
        "main_file": "bot.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
    {
        "dir": "10-multi-agent-integration",
        "main_file": "mini-openclaw.py",
        "docs": ["README.md", "GUIDE.md", "EXERCISES.md"],
        "extra_files": [],
    },
]


def test_top_level_files():
    """Test that top-level workshop files exist."""
    print("\nTop-Level Files")

    required = ["README.md", "Makefile", "pyproject.toml", ".env.example", ".gitignore", "tests.py"]
    for filename in required:
        path = WORKSHOP_DIR / filename
        check(f"{filename} exists", path.exists())
        if path.exists():
            check(f"{filename} is non-empty", path.stat().st_size > 0)


def test_module_structure():
    """Test that all 10 module folders have the required files."""
    print("\nModule Structure")

    for module in MODULES:
        module_dir = WORKSHOP_DIR / module["dir"]
        check(f"{module['dir']}/ exists", module_dir.is_dir())

        if not module_dir.is_dir():
            continue

        # Main Python file
        main_file = module_dir / module["main_file"]
        check(f"{module['dir']}/{module['main_file']} exists", main_file.exists())

        # Documentation files
        for doc in module["docs"]:
            doc_path = module_dir / doc
            check(f"{module['dir']}/{doc} exists", doc_path.exists())

        # Extra files
        for extra in module["extra_files"]:
            extra_path = module_dir / extra
            check(f"{module['dir']}/{extra} exists", extra_path.exists())


def test_python_syntax():
    """Test that all Python files have valid syntax."""
    print("\nPython Syntax")

    for module in MODULES:
        main_file = WORKSHOP_DIR / module["dir"] / module["main_file"]
        if not main_file.exists():
            continue

        try:
            source = main_file.read_text()
            ast.parse(source)
            check(f"{module['dir']}/{module['main_file']} compiles", True)
        except SyntaxError as e:
            check(f"{module['dir']}/{module['main_file']} compiles", False, str(e))


def test_doc_content():
    """Test that documentation files have expected sections."""
    print("\nDocumentation Content")

    for module in MODULES:
        module_dir = WORKSHOP_DIR / module["dir"]
        if not module_dir.is_dir():
            continue

        # README should have key sections
        readme = module_dir / "README.md"
        if readme.exists():
            content = readme.read_text()
            check(
                f"{module['dir']}/README.md has title",
                content.startswith("#"),
                "Should start with a heading",
            )
            check(
                f"{module['dir']}/README.md is substantial",
                len(content) > 200,
                f"Only {len(content)} chars",
            )

        # GUIDE should be substantial
        guide = module_dir / "GUIDE.md"
        if guide.exists():
            content = guide.read_text()
            check(
                f"{module['dir']}/GUIDE.md is substantial",
                len(content) > 500,
                f"Only {len(content)} chars",
            )

        # EXERCISES should have multiple exercises
        exercises = module_dir / "EXERCISES.md"
        if exercises.exists():
            content = exercises.read_text()
            exercise_count = content.count("## Exercise")
            check(
                f"{module['dir']}/EXERCISES.md has 3+ exercises",
                exercise_count >= 3,
                f"Found {exercise_count}",
            )
            # Check for checkpoints
            checkpoint_count = content.lower().count("checkpoint")
            check(
                f"{module['dir']}/EXERCISES.md has checkpoints",
                checkpoint_count >= 2,
                f"Found {checkpoint_count}",
            )


def test_makefile_targets():
    """Test that the Makefile has all required targets."""
    print("\nMakefile Targets")

    makefile = WORKSHOP_DIR / "Makefile"
    if not makefile.exists():
        check("Makefile exists", False)
        return

    content = makefile.read_text()

    required_targets = [
        "install",
        "01-simplest-bot",
        "02-persistent-sessions",
        "03-personality-soul",
        "04-tools-agent-loop",
        "05-permission-controls",
        "06-gateway",
        "07-context-compaction",
        "08-long-term-memory",
        "09-concurrency-scheduling",
        "10-multi-agent-integration",
        "test",
        "clean",
    ]

    for target in required_targets:
        check(
            f"Makefile has '{target}' target",
            f"{target}:" in content,
        )


def test_pyproject():
    """Test pyproject.toml has required dependencies."""
    print("\nDependencies")

    pyproject = WORKSHOP_DIR / "pyproject.toml"
    if not pyproject.exists():
        check("pyproject.toml exists", False)
        return

    content = pyproject.read_text()

    required_deps = ["openai", "python-telegram-bot", "flask", "schedule", "python-dotenv"]
    for dep in required_deps:
        check(
            f"pyproject.toml includes {dep}",
            dep in content,
        )
    # Should NOT include the old anthropic SDK
    check(
        "pyproject.toml does not still include anthropic",
        "anthropic" not in content,
        "anthropic SDK should be removed in favor of openai/OpenRouter",
    )


def test_code_progression():
    """Test that code complexity increases across modules."""
    print("\nCode Progression")

    sizes = []
    for module in MODULES:
        main_file = WORKSHOP_DIR / module["dir"] / module["main_file"]
        if main_file.exists():
            size = len(main_file.read_text().splitlines())
            sizes.append((module["dir"], size))

    if len(sizes) >= 2:
        # Module 01 should be smallest
        check(
            f"01 is smallest ({sizes[0][1]} lines)",
            sizes[0][1] <= sizes[1][1],
            f"{sizes[0][1]} > {sizes[1][1]}",
        )

        # General trend should be increasing (allow some variation)
        check(
            f"Code grows from ~{sizes[0][1]} to ~{sizes[-1][1]} lines",
            sizes[-1][1] > sizes[0][1] * 2,
            "Final module should be significantly larger than first",
        )


def test_key_concepts():
    """Test that key concepts appear in the right modules."""
    print("\nKey Concepts in Code")

    concept_checks = [
        ("01-simplest-bot", "bot.py", "chat.completions.create", "OpenRouter API call"),
        ("01-simplest-bot", "bot.py", "openrouter.ai/api/v1", "OpenRouter base URL"),
        ("02-persistent-sessions", "bot.py", "jsonl", "JSONL format"),
        ("02-persistent-sessions", "bot.py", "load_session", "Session loading"),
        ("03-personality-soul", "bot.py", "SOUL", "SOUL system prompt"),
        ("04-tools-agent-loop", "bot.py", "execute_tool", "Tool execution"),
        ("04-tools-agent-loop", "bot.py", "while True", "Agent loop"),
        ("04-tools-agent-loop", "bot.py", "tool_calls", "Tool calls"),
        ("05-permission-controls", "bot.py", "check_command_safety", "Safety checks"),
        ("05-permission-controls", "bot.py", "DANGEROUS_PATTERNS", "Dangerous patterns"),
        ("06-gateway", "bot.py", "Flask", "Flask HTTP"),
        ("06-gateway", "bot.py", "threading", "Threading"),
        ("07-context-compaction", "bot.py", "estimate_tokens", "Token estimation"),
        ("07-context-compaction", "bot.py", "compact_session", "Compaction"),
        ("08-long-term-memory", "bot.py", "save_memory", "Memory saving"),
        ("08-long-term-memory", "bot.py", "memory_search", "Memory search"),
        ("09-concurrency-scheduling", "bot.py", "session_locks", "Session locks"),
        ("09-concurrency-scheduling", "bot.py", "schedule", "Scheduling"),
        ("10-multi-agent-integration", "mini-openclaw.py", "AGENTS", "Agent config"),
        ("10-multi-agent-integration", "mini-openclaw.py", "resolve_agent", "Agent routing"),
    ]

    for module_dir, filename, concept, label in concept_checks:
        filepath = WORKSHOP_DIR / module_dir / filename
        if filepath.exists():
            content = filepath.read_text()
            check(
                f"{module_dir} has {label}",
                concept in content,
            )


# --- Run all tests ---

def test_env_example():
    """Test that .env.example documents the new OpenRouter variables."""
    print("\nEnvironment Variables")

    env_example = WORKSHOP_DIR / ".env.example"
    if not env_example.exists():
        check(".env.example exists", False)
        return

    content = env_example.read_text()
    check(".env.example mentions OPENROUTER_API_KEY", "OPENROUTER_API_KEY" in content)
    check(".env.example mentions OPENROUTER_MODEL", "OPENROUTER_MODEL" in content)
    check(".env.example mentions qwen/qwen3-coder default", "qwen/qwen3-coder" in content)
    check(
        ".env.example no longer mentions ANTHROPIC_API_KEY",
        "ANTHROPIC_API_KEY" not in content,
        "Should be replaced by OPENROUTER_API_KEY",
    )


def test_tool_call_shape():
    """Smoke-test: load module 04 and verify TOOLS uses OpenAI function-call format."""
    print("\nOpenAI Tool-Call Shape (offline)")

    bot_path = WORKSHOP_DIR / "04-tools-agent-loop" / "bot.py"
    if not bot_path.exists():
        check("04 bot.py exists", False)
        return

    content = bot_path.read_text()
    # OpenAI shape: each tool is {"type": "function", "function": {"name": ..., "parameters": ...}}
    check("04 uses OpenAI tool shape (\"type\": \"function\")", '"type": "function"' in content)
    check("04 uses 'parameters' (not Anthropic 'input_schema')", '"parameters"' in content)
    check(
        "04 does not still use Anthropic 'input_schema'",
        '"input_schema"' not in content,
        "input_schema is the Anthropic format",
    )


if __name__ == "__main__":
    print("=" * 60)
    print("  OpenClaw Workshop — Automated Tests")
    print("=" * 60)

    test_top_level_files()
    test_module_structure()
    test_python_syntax()
    test_doc_content()
    test_makefile_targets()
    test_pyproject()
    test_env_example()
    test_tool_call_shape()
    test_code_progression()
    test_key_concepts()

    # Summary
    total = results["passed"] + results["failed"]
    print(f"\n{'=' * 60}")
    print(f"  Results: {results['passed']}/{total} passed")

    if results["errors"]:
        print(f"\n  Failures:")
        for err in results["errors"]:
            print(f"    - {err}")

    print(f"{'=' * 60}")

    exit(0 if results["failed"] == 0 else 1)
