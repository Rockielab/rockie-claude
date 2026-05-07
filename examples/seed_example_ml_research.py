#!/usr/bin/env python3
"""EXAMPLE: project-specific seeds for an ML research repo.

Copy this file into your own repo's .claude/scripts/ (NOT the rockie
default) and edit it to encode your project's hard-won lessons.

Seeds live in the same workflow.db as the harness defaults — they're
partitioned by the `project` column, so your rules coexist with the
generic ones.

This example captures lessons from a matrix-valued-token research project
on an H100. Yours will look completely different.
"""
import os
import pathlib
import sqlite3

DB = pathlib.Path(__file__).resolve().parent.parent / "memory" / "workflow.db"
PROJECT = os.environ.get("PROJECT") or pathlib.Path(__file__).resolve().parents[2].name

SEEDS = [
    # Scale rules specific to small-model research
    ("scale", "288K params is unigram-statistics territory", None,
     "Can't draw conclusions about reasoning/generalization at this scale. Need 10M+ minimum."),
    ("scale", "Param-matched flat-vector ablation blocks ALL downstream decisions",
     "Ran matrix experiments without a vector baseline.",
     "Run the flat-vector ablation before anything else."),

    # Architecture rules for matrix-valued tokens
    ("matrix-arch", "Never compress matrices to vectors",
     "Compressing to vectors loses all structure.",
     "Use MultiProbeHead (bilinear probes) for output."),
    ("matrix-arch", "Reshape equivalence: d²-vector ↔ d×d matrix",
     "Assumed matrix ops automatically gave structure.",
     "Structure matters only if OPERATIONS preserve it. Flatten = structure gone."),
    ("matrix-arch", "Making matrix ops cheaper does NOT fix the quality gap", None,
     "Speed ≠ quality. Cheap ops are orthogonal to model capability."),

    # Training gotchas
    ("training", "PonderNet halting collapses at small scale", None,
     "Use fixed iterations first, adaptive later."),
    ("training", "Outer-product embedding init: u,v std = sqrt(target_std)",
     "Used target_std for u,v — products had std=σ² (too small).",
     "u,v std must be sqrt(target_std). Products have std=σ²."),

    # Distributed training
    ("distributed", "DDP eval on rank 0 only NCCL-timeouts if eval > 10 min",
     "Default NCCL timeout is 10 min.",
     "Set timeout to 30 min AND cap eval batches to 50 max."),
    ("distributed", "50K vocab logits tensor is the VRAM bottleneck", None,
     "Not model activations. Optimize vocab projections first."),

    # PyTorch-specific
    ("pytorch", "nn.MultiheadAttention requires explicit attn_mask OR is_causal, not both", None,
     "Passing both throws in PyTorch 2.4+."),
    ("pytorch", "HF cache defaults to container disk (/root/.cache/)",
     "Container disk filled up mid-training.",
     "Symlink HF_HOME to persistent volume immediately."),
]


def main() -> None:
    conn = sqlite3.connect(str(DB))
    conn.execute("PRAGMA trusted_schema=1")
    cur = conn.cursor()
    inserted, skipped = 0, 0
    for category, rule, mistake, correction in SEEDS:
        cur.execute(
            "SELECT id FROM learnings WHERE project=? AND category=? AND rule=? LIMIT 1",
            (PROJECT, category, rule),
        )
        if cur.fetchone():
            skipped += 1
            continue
        cur.execute(
            "INSERT INTO learnings (project, category, rule, mistake, correction, source) "
            "VALUES (?,?,?,?,?,?)",
            (PROJECT, category, rule, mistake, correction, "seed"),
        )
        inserted += 1

    conn.commit()
    conn.close()
    print(f"seeded [{PROJECT}]: {inserted} inserted, {skipped} skipped")


if __name__ == "__main__":
    main()
