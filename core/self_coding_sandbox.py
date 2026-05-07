"""Sandbox MVP pour tester des auto-modifications en isolation."""

from __future__ import annotations

from dataclasses import dataclass
import time
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Optional
import re

from .self_improvement_evaluator import BenchmarkResult


@dataclass(frozen=True)
class SandboxResult:
    success: bool
    return_code: int
    stdout: str
    stderr: str
    applied_file: Optional[str] = None


class SelfCodingSandbox:
    """Exécute un test minimal de patch dans un workspace temporaire."""

    def __init__(self, repo_root: str, timeout_seconds: int = 60) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.timeout_seconds = timeout_seconds

    def test_modification(self, new_code: str, target_module: str) -> SandboxResult:
        target_path = self.repo_root / target_module
        if not target_path.exists():
            return SandboxResult(
                success=False,
                return_code=2,
                stdout="",
                stderr=f"target module not found: {target_module}",
            )

        with tempfile.TemporaryDirectory(prefix="lia_sandbox_") as tmp_dir:
            tmp_root = Path(tmp_dir) / "repo"
            shutil.copytree(self.repo_root, tmp_root)

            sandbox_target = tmp_root / target_module
            sandbox_target.write_text(new_code, encoding="utf-8")

            try:
                completed = subprocess.run(
                    ["python", "-m", "compileall", str(sandbox_target)],
                    cwd=str(tmp_root),
                    capture_output=True,
                    text=True,
                    timeout=self.timeout_seconds,
                    check=False,
                )
            except subprocess.TimeoutExpired as exc:
                return SandboxResult(
                    success=False,
                    return_code=124,
                    stdout=exc.stdout or "",
                    stderr=(exc.stderr or "") + "\ntimeout in sandbox",
                    applied_file=target_module,
                )

            return SandboxResult(
                success=completed.returncode == 0,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                applied_file=target_module,
            )

    def benchmark_modification(
        self,
        new_code: str,
        target_module: str,
        test_command: Optional[list[str]] = None,
    ) -> tuple[SandboxResult, BenchmarkResult]:
        """Exécute un benchmark réel (compilation + tests) dans un workspace temporaire."""
        target_path = self.repo_root / target_module
        if not target_path.exists():
            sandbox = SandboxResult(
                success=False,
                return_code=2,
                stdout="",
                stderr=f"target module not found: {target_module}",
            )
            return sandbox, BenchmarkResult(quality_score=0.0, latency_ms=0.0, tests_passed=0, tests_total=0)

        cmd = test_command or ["python", "-m", "pytest", "-q"]
        with tempfile.TemporaryDirectory(prefix="lia_sandbox_bench_") as tmp_dir:
            tmp_root = Path(tmp_dir) / "repo"
            shutil.copytree(self.repo_root, tmp_root)

            sandbox_target = tmp_root / target_module
            sandbox_target.write_text(new_code, encoding="utf-8")

            compile_start = time.perf_counter()
            compile_completed = subprocess.run(
                ["python", "-m", "compileall", str(sandbox_target)],
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            compile_ms = (time.perf_counter() - compile_start) * 1000.0
            if compile_completed.returncode != 0:
                sandbox = SandboxResult(
                    success=False,
                    return_code=compile_completed.returncode,
                    stdout=compile_completed.stdout,
                    stderr=compile_completed.stderr,
                    applied_file=target_module,
                )
                bench = BenchmarkResult(quality_score=0.0, latency_ms=compile_ms, tests_passed=0, tests_total=1)
                return sandbox, bench

            test_start = time.perf_counter()
            test_completed = subprocess.run(
                cmd,
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            tests_ms = (time.perf_counter() - test_start) * 1000.0
            total_ms = compile_ms + tests_ms

            tests_total, tests_passed = self._parse_pytest_counts(test_completed.stdout, test_completed.stderr)
            if tests_total == 0:
                tests_total = 1
                tests_passed = 1 if test_completed.returncode == 0 else 0
            quality = tests_passed / tests_total if tests_total > 0 else 0.0

            sandbox = SandboxResult(
                success=test_completed.returncode == 0,
                return_code=test_completed.returncode,
                stdout=(compile_completed.stdout or "") + "\n" + (test_completed.stdout or ""),
                stderr=(compile_completed.stderr or "") + "\n" + (test_completed.stderr or ""),
                applied_file=target_module,
            )
            bench = BenchmarkResult(
                quality_score=quality,
                latency_ms=total_ms,
                tests_passed=tests_passed,
                tests_total=tests_total,
            )
            return sandbox, bench

    @staticmethod
    def _parse_pytest_counts(stdout: str, stderr: str) -> tuple[int, int]:
        blob = f"{stdout}\n{stderr}"
        total = 0
        passed = 0

        for match in re.finditer(r"(\d+)\s+passed", blob):
            passed += int(match.group(1))
        for match in re.finditer(r"(\d+)\s+(failed|error|errors|skipped|xfailed|xpassed)", blob):
            total += int(match.group(1))
        total += passed
        return total, passed
