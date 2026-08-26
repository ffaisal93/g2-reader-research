"""Run frozen official G² questions in isolated, resumable subprocesses."""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import time
from pathlib import Path


def sha256_bytes(value: bytes) -> str:
    return hashlib.sha256(value).hexdigest()


def sha256_file(path: Path) -> str:
    return sha256_bytes(path.read_bytes())


def git(root: Path, *args: str) -> str:
    return subprocess.check_output(["git", "-C", str(root), *args], text=True).strip()


def write_json(path: Path, value: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--official-root", type=Path, required=True)
    parser.add_argument("--questions", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, required=True)
    parser.add_argument("--python", type=Path, required=True)
    parser.add_argument("--memory-dir", type=Path, required=True)
    parser.add_argument("--model", default="local-qwen-vl")
    parser.add_argument("--embedding-model", default="local-bge-m3")
    parser.add_argument("--base-url", default="http://127.0.0.1:18000/v1")
    parser.add_argument("--embedding-base-url")
    parser.add_argument("--max-concurrency", type=int, default=1)
    parser.add_argument("--request-timeout-seconds", type=int, default=3600)
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--evolution-rounds", type=int, help="Pass only to worktrees that expose this runtime control")
    parser.add_argument("--document-limit", type=int, help="Pass only to worktrees that expose this runtime control")
    parser.add_argument("--limit", type=int)
    parser.add_argument("--timeout-seconds", type=int, default=21600)
    parser.add_argument("--max-question-attempts", type=int, default=2)
    args = parser.parse_args()

    args.official_root = args.official_root.resolve()
    args.questions = args.questions.resolve()
    args.output_dir = args.output_dir.resolve()
    args.memory_dir = args.memory_dir.resolve()
    args.output_dir.mkdir(parents=True, exist_ok=True)
    args.memory_dir.mkdir(parents=True, exist_ok=True)

    rows = [json.loads(line) for line in args.questions.read_text(encoding="utf-8").splitlines() if line]
    if args.limit is not None:
        rows = rows[: args.limit]

    diff = subprocess.check_output(["git", "-C", str(args.official_root), "diff", "--binary"])
    untracked = git(args.official_root, "ls-files", "--others", "--exclude-standard").splitlines()
    manifest = {
        "name": args.output_dir.name,
        "created_at_unix": time.time(),
        "official_root": str(args.official_root),
        "upstream_commit": git(args.official_root, "rev-parse", "HEAD"),
        "tracked_diff_sha256": sha256_bytes(diff),
        "untracked_instrumentation_files": untracked,
        "questions": str(args.questions),
        "questions_sha256": sha256_file(args.questions),
        "question_count": len(rows),
        "model": args.model,
        "embedding_model": args.embedding_model,
        "base_url": args.base_url,
        "embedding_base_url": args.embedding_base_url or args.base_url,
        "memory_dir": str(args.memory_dir),
        "max_concurrency": args.max_concurrency,
        "request_timeout_seconds": args.request_timeout_seconds,
        "seed": args.seed,
        "official_arguments": {
            "n_proc": 1,
            "debug": True,
            "use_dag": True,
            "top_k": 5,
            "evolution_rounds": args.evolution_rounds if args.evolution_rounds is not None else "upstream default",
            "document_limit": args.document_limit if args.document_limit is not None else "upstream default",
        },
        "timeout_seconds": args.timeout_seconds,
        "max_question_attempts": args.max_question_attempts,
    }
    write_json(args.output_dir / "run_manifest.json", manifest)

    environment = os.environ.copy()
    environment.update(
        {
            "G2_USE_LOCAL_RUNTIME": "1",
            "G2_LLM_BASE_URL": args.base_url,
            "G2_EMBED_BASE_URL": args.embedding_base_url or args.base_url,
            "G2_API_KEY": environment.get("G2_API_KEY", "local"),
            "G2_EMBED_API_KEY": environment.get("G2_EMBED_API_KEY", "local"),
            "G2_CHAT_MODEL": args.model,
            "G2_EMBED_MODEL": args.embedding_model,
            "G2_MEMORY_DIR": str(args.memory_dir),
            "G2_MAX_CONCURRENCY": str(args.max_concurrency),
            "G2_REQUEST_TIMEOUT_SECONDS": str(args.request_timeout_seconds),
            "G2_RANDOM_SEED": str(args.seed),
            "PYTHONHASHSEED": str(args.seed),
            "PYTHONPATH": str(args.official_root),
        }
    )

    failed_questions: list[str] = []

    def archive_failed_attempt(question_dir: Path, question_id: str, attempt: int) -> None:
        archive_root = args.output_dir / "failed_attempts"
        archive_root.mkdir(parents=True, exist_ok=True)
        archive = archive_root / f"{question_id}_attempt_{attempt}_{time.time_ns()}"
        shutil.move(str(question_dir), str(archive))

        # A prebuild crash can leave an iteration-zero graph that the next run
        # would overwrite. Preserve it when no completed evolved graph exists.
        if not (args.memory_dir / f"{question_id}_iter_1").exists():
            partials = sorted(args.memory_dir.glob(f"{question_id}_iter_*"))
            if partials:
                memory_archive = args.memory_dir / "_failed_attempts" / archive.name
                memory_archive.mkdir(parents=True, exist_ok=True)
                for partial in partials:
                    shutil.move(str(partial), str(memory_archive / partial.name))

    for position, row in enumerate(rows):
        question_id = str(row["_id"])
        question_dir = args.output_dir / "questions" / question_id
        status_path = question_dir / "status.json"
        if status_path.exists():
            previous = json.loads(status_path.read_text(encoding="utf-8"))
            if previous.get("status") == "complete":
                continue
            archive_failed_attempt(question_dir, question_id, int(previous.get("attempt", 0)))

        question_complete = False
        for attempt in range(1, args.max_question_attempts + 1):
            question_dir.mkdir(parents=True, exist_ok=True)
            input_path = question_dir / "input.jsonl"
            input_path.write_text(json.dumps(row, ensure_ascii=False) + "\n", encoding="utf-8")
            command = [
                str(args.python),
                "-u",
                "-m",
                "scripts.test_rag",
                "--data_path",
                str(input_path),
                "--save_dir",
                str(question_dir / "official_output"),
                "--model",
                args.model,
                "--n_proc",
                "1",
                "--debug",
                "--use_dag",
                "--top_k",
                "5",
            ]
            if args.evolution_rounds is not None:
                command.extend(["--evolution_rounds", str(args.evolution_rounds)])
            if args.document_limit is not None:
                command.extend(["--document_limit", str(args.document_limit)])
            started = time.time()
            status = {
                "question_id": question_id,
                "position": position,
                "attempt": attempt,
                "started_at_unix": started,
                "command": command,
            }
            try:
                with (question_dir / "console.log").open("w", encoding="utf-8") as log:
                    completed = subprocess.run(
                        command,
                        cwd=args.official_root,
                        env=environment,
                        stdout=log,
                        stderr=subprocess.STDOUT,
                        timeout=args.timeout_seconds,
                        check=False,
                    )
                status.update(
                    {
                        "status": "complete" if completed.returncode == 0 else "failed",
                        "return_code": completed.returncode,
                    }
                )
            except subprocess.TimeoutExpired:
                status.update({"status": "timeout", "return_code": None})
            status["duration_seconds"] = time.time() - started
            write_json(status_path, status)
            if status["status"] == "complete":
                question_complete = True
                break
            if attempt < args.max_question_attempts:
                archive_failed_attempt(question_dir, question_id, attempt)

        if not question_complete:
            failed_questions.append(question_id)

    if failed_questions:
        raise SystemExit(f"failed questions after retries: {', '.join(failed_questions)}")


if __name__ == "__main__":
    main()
