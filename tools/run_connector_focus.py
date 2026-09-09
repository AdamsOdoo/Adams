#!/usr/bin/env python3
"""Fast, fail-closed native prerequisite for the full connector campaign."""

from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import time

ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS = Path(os.environ.get("ARTIFACT_DIR", ROOT / "ci-artifacts"))
LOG = ARTIFACTS / "focus.log"
SUMMARY = ARTIFACTS / "focus-summary.json"
CONFIG = ROOT / ".ci" / "connector-native-focus.json"
RUNNER = ROOT / "tools" / "run_connector_suite.sh"


def note(message: str) -> None:
    print(f"[connector-focus] {message}", flush=True)
    with LOG.open("a", encoding="utf-8") as stream:
        stream.write(f"[connector-focus] {message}\n")


def command(args: list[str], *, cwd: Path | None = None,
            env: dict[str, str] | None = None, check: bool = True) -> int:
    note("running: " + " ".join(args))
    with LOG.open("a", encoding="utf-8") as stream:
        result = subprocess.run(args, cwd=cwd, env=env, stdout=stream,
                                stderr=subprocess.STDOUT, check=False)
    if check and result.returncode:
        raise RuntimeError(f"command failed ({result.returncode}): {args[0]}")
    return result.returncode


def git_output(*args: str) -> str:
    return subprocess.check_output(["git", *args], cwd=ROOT, text=True).strip()


def runner_value(name: str) -> str:
    match = re.search(rf'^{name}="([^"]+)"$', RUNNER.read_text(), re.MULTILINE)
    if not match:
        raise RuntimeError(f"could not read {name} from {RUNNER.relative_to(ROOT)}")
    return match.group(1)


def selected_classes(config: dict) -> tuple[list[str], list[str]]:
    selectors, names = [], []
    for item in config.get("classes", []):
        addon, class_name = item.get("addon", ""), item.get("class", "")
        if not re.fullmatch(r"shopify_connector_[a-z_]+", addon):
            raise RuntimeError(f"invalid focused addon: {addon!r}")
        if not re.fullmatch(r"Test[A-Za-z0-9_]+", class_name):
            raise RuntimeError(f"invalid focused class: {class_name!r}")
        found = False
        for source in (ROOT / "addons" / addon / "tests").glob("test_*.py"):
            tree = ast.parse(source.read_text(encoding="utf-8"), filename=str(source))
            found |= any(isinstance(node, ast.ClassDef) and node.name == class_name
                         for node in tree.body)
        if not found:
            raise RuntimeError(f"focused class is missing: {addon}:{class_name}")
        selectors.append(f"/{addon}:{class_name}")
        names.append(class_name)
    if not selectors or len(selectors) != len(set(selectors)):
        raise RuntimeError("focused class inventory is empty or contains duplicates")
    return selectors, names


def main() -> int:
    ARTIFACTS.mkdir(parents=True, exist_ok=True)
    LOG.write_text("", encoding="utf-8")
    started = time.time()
    report: dict = {
        "status": "fail", "scope": "focused native prerequisite",
        "config": str(CONFIG.relative_to(ROOT)), "shopify_operations": "none",
        "evidence_class": "focused diagnostic scope only; not the full connector gate",
    }
    db = f"connector_focus_{os.getpid()}"
    try:
        config = json.loads(CONFIG.read_text(encoding="utf-8"))
        selectors, names = selected_classes(config)
        modules, extras = runner_value("MODULES"), runner_value("EXTRA_MODULES")
        sha = git_output("rev-parse", "HEAD")
        intended = os.environ.get("SOURCE_HEAD_SHA", "")
        report.update(scope=config["scope"], tested_checkout_sha=sha,
                      source_head_sha=intended,
                      source_base_sha=os.environ.get("SOURCE_BASE_SHA", ""),
                      source_head_verified=bool(intended and intended == sha),
                      connector_worktree_dirty=bool(git_output("status", "--porcelain")),
                      modules=modules, extra_modules=extras, selectors=selectors)
        if intended and intended != sha:
            raise RuntimeError(f"checkout {sha} is not intended source head {intended}")

        pin = os.environ.get("ODOO_PIN") or next(
            line.strip() for line in (ROOT / "tools" / "odoo-pin.txt").read_text().splitlines()
            if line.strip() and not line.lstrip().startswith("#"))
        if not re.fullmatch(r"[0-9a-f]{40}", pin):
            raise RuntimeError("tools/odoo-pin.txt does not contain an exact commit SHA")
        odoo = Path(os.environ.get("ODOO_SRC", ROOT / ".odoo-src"))
        if not (odoo / ".git").is_dir():
            command(["git", "clone", "--filter=blob:none", "--no-checkout",
                     "https://github.com/odoo/odoo.git", str(odoo)])
        current = subprocess.run(["git", "-C", str(odoo), "rev-parse", "HEAD"],
                                 text=True, capture_output=True).stdout.strip()
        if current != pin:
            if command(["git", "-C", str(odoo), "fetch", "--filter=blob:none",
                        "origin", pin], check=False):
                command(["git", "-C", str(odoo), "fetch", "--filter=blob:none",
                         "--depth", "400", "origin", "19.0"], check=False)
            command(["git", "-C", str(odoo), "checkout", "--quiet", "--detach", pin],
                    check=False)
        odoo_sha = subprocess.check_output(
            ["git", "-C", str(odoo), "rev-parse", "HEAD"], text=True).strip()
        report.update(odoo_pin=pin, odoo_sha=odoo_sha,
                      odoo_pin_verified=odoo_sha == pin)
        if odoo_sha != pin:
            raise RuntimeError(f"Odoo checkout {odoo_sha} does not match pin {pin}")

        python = os.environ.get("PYTHON") or shutil.which("python3.12") or shutil.which("python3")
        if not python:
            raise RuntimeError("no Python interpreter found")
        venv = odoo.parent / ".connector-venv"
        if not (venv / "bin/python").is_file():
            command([python, "-m", "venv", str(venv)])
            command([str(venv / "bin/pip"), "install", "--quiet", "--upgrade",
                     "pip", "setuptools<70", "wheel"])
            command([str(venv / "bin/pip"), "install", "--quiet", "psycopg2-binary"])
            requirements = [line for line in (odoo / "requirements.txt").read_text().splitlines()
                            if not re.match(r"(?i)^(psycopg2|python-ldap)", line)]
            (venv / "requirements.txt").write_text("\n".join(requirements) + "\n")
            command([str(venv / "bin/pip"), "install", "--quiet", "-r",
                     str(venv / "requirements.txt")])
        command([str(venv / "bin/pip"), "install", "--quiet", "graphql-core==3.2.6"])
        command([str(venv / "bin/python"), str(ROOT / "tools/validate_shopify_graphql.py")])
        report["python"] = subprocess.check_output(
            [str(venv / "bin/python"), "--version"], text=True, stderr=subprocess.STDOUT).strip()

        conf = ARTIFACTS / "focus-odoo.conf"
        conf.write_text("[options]\n" +
            f"addons_path = {odoo / 'addons'},{ROOT / 'addons'}\n"
            f"db_host = {os.environ.get('PGHOST', '/tmp')}\n"
            f"db_port = {os.environ.get('PGPORT', '5432')}\n"
            f"db_user = {os.environ.get('PGUSER', os.environ.get('USER', 'odoo'))}\n"
            f"data_dir = {ARTIFACTS / 'focus-odoo-data'}\n"
            "without_demo = False\nlimit_time_real = 0\nlimit_time_cpu = 0\n")
        command(["dropdb", "--if-exists", db], check=False)
        command(["createdb", db])
        report["postgres_server_version"] = subprocess.check_output(
            ["psql", "-tAc", "show server_version;", "postgres"], text=True).strip()
        test_env = os.environ.copy()
        test_env["SHOPIFY_LAYER2_RUN_PROCESS_DEATH"] = "1"
        rc = command([str(venv / "bin/python"), "odoo-bin", "-c", str(conf), "-d", db,
                      "--stop-after-init", "--log-level=test", "-i", f"{modules},{extras}",
                      "--test-enable", "--test-tags", ",".join(selectors)],
                     cwd=odoo, env=test_env, check=False)
        text = LOG.read_text(encoding="utf-8", errors="replace")
        result = re.findall(
            r"(\d+) failed, (\d+) error\(s\) of (\d+) tests", text)
        failed, errors, count = (map(int, result[-1]) if result else (0, 0, 0))
        seen = [name for name in names if re.search(rf"Starting {re.escape(name)}\.", text)]
        skipped = [name for name in names if re.search(
            rf"skipped (?:Subtest )?{re.escape(name)}\.[^:]+ :", text)]
        report.update(odoo_exit_code=rc, tests_failed=failed,
                      test_errors=errors, tests_executed=count,
                      selected_classes=names, started_classes=seen,
                      skipped_selected_classes=skipped)
        missing = sorted(set(names) - set(seen))
        if rc or failed or errors or count == 0 or missing or skipped:
            raise RuntimeError(f"focused evidence failed: exit={rc}, failed={failed}, "
                               f"errors={errors}, tests={count}, missing={missing}, "
                               f"skipped={skipped}")
        report["status"] = "pass"
        note(f"PASS: {count} focused tests; this is not the full connector gate")
        return 0
    except Exception as exc:
        report["error"] = str(exc)
        note(f"FAIL: {exc}")
        return 1
    finally:
        report["duration_seconds"] = round(time.time() - started, 3)
        SUMMARY.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n",
                           encoding="utf-8")
        dropdb = shutil.which("dropdb")
        if dropdb:
            try:
                subprocess.run([dropdb, "--if-exists", db], stdout=subprocess.DEVNULL,
                               stderr=subprocess.DEVNULL, check=False)
            except OSError as exc:
                note(f"database cleanup warning: {exc}")
        note(f"summary written to {SUMMARY}")


if __name__ == "__main__":
    raise SystemExit(main())
