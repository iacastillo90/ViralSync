"""Contract tests for the Phase-0 slice-2 CI/CD configuration.

Verifies that the committed CI artifacts match the spec/design contracts:

- ``agency/ruff.toml``: line-length 120, Python 3.12 target, E4/E7/E9/F rules.
- ``.github/workflows/ci.yml``: push/PR triggers and the four parallel
  gating jobs (python, frontend, docker-lint, secrets).
- ``.gitignore``: env files ignored while ``.env.example`` stays trackable,
  plus both venv directories (``venv/`` and ``.venv/``).
"""

import tomllib
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
AGENCY = REPO_ROOT / "agency"


def _ruff_toml() -> dict:
    with open(AGENCY / "ruff.toml", "rb") as handle:
        return tomllib.load(handle)


def _ci_workflow() -> str:
    return (REPO_ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")


def test_ruff_toml_sets_line_length_120() -> None:
    assert _ruff_toml()["line-length"] == 120


def test_ruff_toml_targets_python_312() -> None:
    assert _ruff_toml()["target-version"] == "py312"


def test_ruff_toml_selects_expected_rule_codes() -> None:
    assert set(_ruff_toml()["lint"]["select"]) == {"E4", "E7", "E9", "F"}


def test_ci_workflow_triggers_on_push_and_pull_request() -> None:
    workflow = _ci_workflow()
    assert "pull_request" in workflow
    assert "push" in workflow


def test_ci_workflow_defines_four_gating_jobs() -> None:
    workflow = _ci_workflow()
    for job in ("python:", "frontend:", "docker-lint:", "secrets:"):
        assert job in workflow


def test_ci_python_job_installs_lock_and_runs_coverage_gate() -> None:
    workflow = _ci_workflow()
    assert "uv pip install -r requirements.lock" in workflow
    assert "uv run pytest" in workflow
    assert "--cov=agency/backend" in workflow
    assert "AGENCY_ENV" in workflow


def test_ci_python_job_lints_and_audits() -> None:
    workflow = _ci_workflow()
    assert "uvx ruff check" in workflow
    # Lint scope is the PR diff (checks-to-diff), not the whole tree.
    assert "origin/main...HEAD" in workflow
    assert "uvx pip-audit -r requirements.lock" in workflow


def test_ci_python_job_excludes_preexisting_video_debt() -> None:
    workflow = _ci_workflow()
    # Preexisting-main failures (video crew/renderer) stay out of the
    # regression gate until the debt issue is fixed.
    assert "--ignore=agency/tests/unit/test_video_prompt_crew.py" in workflow
    assert "--ignore=agency/tests/unit/test_video_renderer_microservice.py" in workflow
    assert "--ignore=agency/tests/unit/test_video_renderer_performance.py" in workflow


def test_ci_python_job_excludes_preexisting_minio_and_orm_debt() -> None:
    workflow = _ci_workflow()
    # Preexisting-main failures unrelated to any PR diff stay out of the
    # gate (checks-to-diff policy) until the debt issue is fixed.
    assert "--ignore=agency/tests/unit/test_minio_real.py" in workflow
    assert "--ignore=agency/tests/unit/test_video_metric_orm_alignment.py" in workflow


def test_ci_frontend_job_builds_and_audits() -> None:
    workflow = _ci_workflow()
    assert "npm ci" in workflow
    assert "npm run build" in workflow
    assert "npm audit" in workflow


def test_ci_has_docker_lint_and_secrets_jobs() -> None:
    workflow = _ci_workflow()
    assert "hadolint" in workflow
    assert "gitleaks" in workflow
    assert "fetch-depth: 0" in workflow


def test_gitignore_ignores_env_files_but_keeps_example() -> None:
    lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert ".env*" in lines
    assert "!.env.example" in lines
    assert lines.index(".env*") < lines.index("!.env.example")


def test_gitignore_ignores_both_venv_directories() -> None:
    lines = (REPO_ROOT / ".gitignore").read_text(encoding="utf-8").splitlines()
    assert "venv/" in lines
    assert ".venv/" in lines
