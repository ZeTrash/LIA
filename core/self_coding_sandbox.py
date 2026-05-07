"""Sandbox MVP pour tester des auto-modifications en isolation."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import hashlib
import os
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

    def __init__(self, repo_root: str, timeout_seconds: int = 60, use_docker: bool = True) -> None:
        self.repo_root = Path(repo_root).resolve()
        self.timeout_seconds = timeout_seconds
        self.use_docker = use_docker
        self._copy_ignore_names = {
            ".git",
            ".pytest_cache",
            "__pycache__",
            "_archive",
            "models",          # énorme cache HF/GGUF, inutile pour compilation/tests ciblés
            "agent_memory.db", # volumineux, non requis pour sandbox test
        }
        self.versions_dir = self.repo_root / "logs" / "self_mod_versions"
        self.versions_dir.mkdir(parents=True, exist_ok=True)

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
            tmp_root = self._prepare_tmp_repo(tmp_dir=tmp_dir, target_module=target_module, new_code=new_code)
            cmd = ["python", "-m", "compileall", str(target_module)]
            return self._run_isolated(cmd=cmd, tmp_root=tmp_root, target_module=target_module)

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
            tmp_root = self._prepare_tmp_repo(tmp_dir=tmp_dir, target_module=target_module, new_code=new_code)
            compile_start = time.perf_counter()
            compile_completed = self._run_isolated(
                cmd=["python", "-m", "compileall", str(target_module)],
                tmp_root=tmp_root,
                target_module=target_module,
            )
            compile_ms = (time.perf_counter() - compile_start) * 1000.0
            if compile_completed.return_code != 0:
                bench = BenchmarkResult(quality_score=0.0, latency_ms=compile_ms, tests_passed=0, tests_total=1)
                return compile_completed, bench

            test_start = time.perf_counter()
            test_completed = self._run_isolated(cmd=cmd, tmp_root=tmp_root, target_module=target_module)
            tests_ms = (time.perf_counter() - test_start) * 1000.0
            total_ms = compile_ms + tests_ms

            tests_total, tests_passed = self._parse_pytest_counts(test_completed.stdout, test_completed.stderr)
            if tests_total == 0:
                tests_total = 1
                tests_passed = 1 if test_completed.return_code == 0 else 0
            quality = tests_passed / tests_total if tests_total > 0 else 0.0

            sandbox = SandboxResult(
                success=test_completed.return_code == 0,
                return_code=test_completed.return_code,
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

    def rollback(self, target_module: str, previous_code: str) -> bool:
        """Restore un module local depuis son backup code."""
        target_path = self.repo_root / target_module
        if not target_path.exists():
            return False
        target_path.write_text(previous_code, encoding="utf-8")
        return True

    def save_version(self, target_module: str, code: str, label: str = "backup") -> str:
        """Sauvegarde une version du module (avant/après) pour rollback/versioning."""
        target_module = str(target_module).lstrip("./")
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        digest = hashlib.sha1(code.encode("utf-8")).hexdigest()[:10]
        safe_name = target_module.replace("/", "__")
        version_id = f"{ts}_{label}_{safe_name}_{digest}"
        path = self.versions_dir / f"{version_id}.py"
        path.write_text(code, encoding="utf-8")
        meta = self.versions_dir / f"{version_id}.meta.txt"
        meta.write_text(f"target={target_module}\nlabel={label}\nsha1={digest}\n", encoding="utf-8")
        return version_id

    def rollback_to_version(self, version_id: str) -> bool:
        """Rollback depuis une version sauvegardée."""
        version_id = str(version_id).strip()
        path = self.versions_dir / f"{version_id}.py"
        meta = self.versions_dir / f"{version_id}.meta.txt"
        if not path.exists() or not meta.exists():
            return False
        code = path.read_text(encoding="utf-8")
        target = None
        for line in meta.read_text(encoding="utf-8").splitlines():
            if line.startswith("target="):
                target = line.split("=", 1)[1].strip()
                break
        if not target:
            return False
        return self.rollback(target, code)

    def _prepare_tmp_repo(self, tmp_dir: str, target_module: str, new_code: str) -> Path:
        tmp_root = Path(tmp_dir) / "repo"
        shutil.copytree(
            self.repo_root,
            tmp_root,
            ignore=shutil.ignore_patterns(*sorted(self._copy_ignore_names)),
        )
        sandbox_target = tmp_root / target_module
        sandbox_target.write_text(new_code, encoding="utf-8")
        return tmp_root

    def _run_isolated(self, cmd: list[str], tmp_root: Path, target_module: str) -> SandboxResult:
        if self.use_docker and self._is_docker_available():
            return self._run_in_docker(cmd=cmd, tmp_root=tmp_root, target_module=target_module)
        return self._run_local(cmd=cmd, tmp_root=tmp_root, target_module=target_module)

    def _run_local(self, cmd: list[str], tmp_root: Path, target_module: str) -> SandboxResult:
        try:
            completed = subprocess.run(
                cmd,
                cwd=str(tmp_root),
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return SandboxResult(
                success=completed.returncode == 0,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                applied_file=target_module,
            )
        except subprocess.TimeoutExpired as exc:
            return SandboxResult(
                success=False,
                return_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\ntimeout in local sandbox",
                applied_file=target_module,
            )

    def _run_in_docker(self, cmd: list[str], tmp_root: Path, target_module: str) -> SandboxResult:
        container_name = f"lia-sandbox-{int(time.time())}"
        docker_cmd = [
            "docker",
            "run",
            "--rm",
            "--name",
            container_name,
            "--network",
            "none",
            "--cpus",
            "1.0",
            "--memory",
            "2g",
            "-v",
            f"{tmp_root}:/workspace:rw",
            "-w",
            "/workspace",
            "python:3.12-slim",
        ] + cmd
        try:
            completed = subprocess.run(
                docker_cmd,
                capture_output=True,
                text=True,
                timeout=self.timeout_seconds,
                check=False,
            )
            return SandboxResult(
                success=completed.returncode == 0,
                return_code=completed.returncode,
                stdout=completed.stdout,
                stderr=completed.stderr,
                applied_file=target_module,
            )
        except subprocess.TimeoutExpired as exc:
            # Best-effort stop if container still running.
            subprocess.run(["docker", "rm", "-f", container_name], check=False, capture_output=True, text=True)
            return SandboxResult(
                success=False,
                return_code=124,
                stdout=exc.stdout or "",
                stderr=(exc.stderr or "") + "\ntimeout in docker sandbox",
                applied_file=target_module,
            )

    @staticmethod
    def _is_docker_available() -> bool:
        if os.environ.get("LIA_DISABLE_DOCKER_SANDBOX", "").strip() == "1":
            return False
        try:
            p = subprocess.run(
                ["docker", "version", "--format", "{{.Server.Version}}"],
                capture_output=True,
                text=True,
                timeout=2,
                check=False,
            )
            return p.returncode == 0
        except Exception:
            return False

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
