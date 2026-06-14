# SkillsBench — results & website data

Result snapshots and supporting data for the [SkillsBench](https://skillsbench.ai) leaderboard.

## Current snapshot

The latest experimental results are the HuggingFace dataset
[`benchflow/skillsbench-leaderboard`](https://huggingface.co/datasets/benchflow/skillsbench-leaderboard),
**main branch + [PR #11](https://huggingface.co/datasets/benchflow/skillsbench-leaderboard/discussions/11)**
(v0.1 + v1.1). It covers **18 model–harness configurations × 87 tasks × 2 conditions
(with / without curated Skills) × 3 trials**, run at each model's maximum reasoning effort and
scored pass/fail. That dataset is the source of truth for both trajectories and results.

## `website-data/`

Build-time data consumed by skillsbench.ai (fetched from this repo's `main`):

- **`results-registry.json`** — per `(task, model–harness, condition)` aggregate
  (score, pass/perfect counts) backing each task page's Results board. Regenerated from
  the HuggingFace snapshot above.

The website no longer hosts agent trajectory files; trajectories are browsed and downloaded
on the HuggingFace dataset.

## Other directories

The contributor-named directories (`yimin/`, `xiangyi-*/`, `shenghan/`, `wenbo/`,
`minimax-m2.1+claude-code/`) are an **archive of earlier-generation runs**. Current
trajectories live on the HuggingFace dataset, not in this repo.
