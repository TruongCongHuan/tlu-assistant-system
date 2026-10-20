"""Run dev -> lock -> test -> report in separate processes, without an LLM API."""
from __future__ import annotations

import argparse
import json
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

SERVICE = Path(__file__).resolve().parents[1]
ROOT = SERVICE.parents[1]
RUNNER = SERVICE / "eval/run_retrieval_benchmark.py"
REPORT = SERVICE / "eval/report_retrieval_benchmark.py"
OUT = ROOT / "data/benchmarks/reranking"


def execute(arguments: list[str], log: Path) -> Path | None:
    command = [sys.executable, *arguments]
    result = None
    with log.open("w") as stream:
        process = subprocess.Popen(command, cwd=ROOT, stdout=subprocess.PIPE,
                                   stderr=subprocess.STDOUT, text=True, bufsize=1)
        for line in process.stdout:
            stream.write(line)
            stream.flush()
            print(line, end="", flush=True)
            if line.startswith("[RESULT] "):
                result = Path(line.removeprefix("[RESULT] ").strip())
        code = process.wait()
    if code:
        raise RuntimeError(f"Command failed (code={code}); inspect {log}")
    return result


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--config", type=Path, default=SERVICE / "eval/benchmark_configs_bge_int8.json")
    parser.add_argument("--repetitions", type=int, default=1)
    parser.add_argument("--smoke-first", action="store_true")
    args = parser.parse_args()
    logs = OUT / ("pipeline_" + datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ"))
    logs.mkdir(parents=True, exist_ok=False)
    base = [str(RUNNER), "--config", str(args.config.resolve())]
    execute([str(RUNNER), "--validate-data"], logs / "validate.log")
    execute(base + ["--stage", "embed", "--split", "dev"], logs / "embed_dev.log")
    if args.smoke_first:
        execute(base + ["--split", "dev", "--smoke"], logs / "smoke.log")
    dev = execute(base + ["--split", "dev", "--repetitions", str(args.repetitions)], logs / "dev.log")
    if dev is None:
        raise RuntimeError("Dev run did not emit a result directory")
    execute([str(RUNNER), "--lock-from", str(dev)], logs / "lock.log")
    locked = ["--locked-config", str(OUT / "locked_config.json")]
    execute(base + ["--stage", "embed", "--split", "test", *locked], logs / "embed_test.log")
    test = execute(base + ["--split", "test", "--repetitions", str(args.repetitions), *locked], logs / "test.log")
    if test is None:
        raise RuntimeError("Test run did not emit a result directory")
    execute([str(REPORT), "--run-dir", str(dev)], logs / "report_dev.log")
    execute([str(REPORT), "--run-dir", str(test)], logs / "report_test.log")
    summary = {"dev": str(dev), "test": str(test), "config": str(args.config.resolve()),
               "scope": "retrieval-only; no generation or judge", "logs": str(logs)}
    (logs / "pipeline.json").write_text(json.dumps(summary, indent=2) + "\n")
    print("[PIPELINE COMPLETE]", logs / "pipeline.json", flush=True)


if __name__ == "__main__":
    main()
