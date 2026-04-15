# RTK - Rust Token Killer (Codex CLI)

**Usage**: token-optimized CLI proxy for shell commands in Codex.

## Rule

Prefer RTK for shell commands, using the invocation that actually works in this
environment. Use raw commands only when RTK does not support the operation or
when full-fidelity output is required for debugging.

## High-Value Patterns For This Repo

```bash
rtk git status
rtk git diff --stat
rtk read path/to/file.py --max-lines 160
rtk grep "pattern" src
rtk find . -name "*.py"
```

This repository uses a local virtualenv and Makefile targets, so validation
commands should usually be wrapped like this:

```bash
rtk test .venv/bin/python -m pytest tests/unit -q
rtk test .venv/bin/python -m pytest tests/unit/test_erro_leitura_ml.py -q
rtk .venv/bin/ruff check src tests scripts
rtk .venv/bin/mypy src scripts
rtk make erro-leitura-dry-run
rtk make erro-leitura-normalize
rtk make erro-leitura-train
```

For dashboard sharing and Docker diagnostics:

```bash
rtk docker ps
rtk docker compose -p enel-share -f infra/docker-compose.share.yml ps
rtk docker compose -p enel-share -f infra/docker-compose.share.yml logs streamlit
rtk docker compose -p enel-share -f infra/docker-compose.share.yml build streamlit
```

## Meta Commands

```bash
rtk gain            # Token savings analytics
rtk gain --history  # Recent command savings history
rtk proxy <cmd>     # Run raw command without filtering
rtk rewrite <cmd>   # Show canonical RTK equivalent when supported
rtk init --show --codex
```

## Best Practices

- Prefer `rtk read`, `rtk grep`, `rtk ls`, `rtk find`, and `rtk git` for repo
  inspection.
- Prefer `rtk test ...pytest...` for pytest so failures stay visible and
  passing boilerplate stays compact.
- Use `rtk proxy` when the exact raw output matters.
- Avoid adding local filters that duplicate RTK built-in handlers.
- Treat `rtk gain` as analytics only; if the tracking DB fails, keep using RTK
  for compact output.

## Verification

```bash
rtk --version
rtk gain
command -v rtk
rtk init --show --codex
```
