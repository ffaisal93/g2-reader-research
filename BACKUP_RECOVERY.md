# Emergency backup and recovery

This repository was created before the August 26, 2026 ORC outage to preserve
the G2-Reader research code, experiment definitions, reports, adjudication
records, and compact validation evidence.

## Branches

- `main` contains the research workspace backup.
- `official-trace-backup` contains the modified official G2-Reader runtime at
  commit `5dae93c`.

The official runtime is represented on `main` as an embedded-repository commit
pointer. To recover its complete working tree directly:

```bash
git clone --branch official-trace-backup \
  https://github.com/ffaisal93/g2-reader-research.git \
  G2_Reader_official_trace
```

The Minimal G2 implementation remains in its independent repository:

```text
https://github.com/ffaisal93/minimal_g2_reader
```

## Intentionally excluded

Downloaded datasets, processed document payloads, external clones, Python
environments, model weights, graph pickles, service logs, question workspaces,
and other reproducible bulk runtime artifacts are excluded by `.gitignore`.
They must be restored from their original sources or a separate binary backup.
