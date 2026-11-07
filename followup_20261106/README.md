# Calmer V2: a provisional efficiency pilot

This is the curated public record of the 6 November 2026 follow-up to [Weight-Space Programming](../PAPER.md). The user selected the layer-18 pilot for hands-on use after reviewing its limitations. [Calmer V2 Qwen3.8 27B, 4-bit](https://huggingface.co/Xananthium/Calmer-V2-Qwen3.8-27B-4bit) is an experimental pilot, not a confirmed general reasoning upgrade.

In one exposed development run, the pilot used **22.45% fewer tokens** on the five-case fast panel and **58.19% fewer tokens** on one topology case. It retained the fast panel's two HLE choices and three GSM answers. Its tree explanation had additional false event histories, and its hat response remained unfinished. Warm-profile, second-seed and wider GSM24 candidate confirmation are **missing**.

After an authorized reboot, startup checks and a small readiness response succeeded. The pilot is in use by user choice. That smoke test is **not benchmark confirmation** and does not fill the missing results.

- [Scientific report](REPORT.md): construction, findings, failures and interpretation.
- [All completed numerical outcomes](RESULTS.md): every retained compiled comparison, plus interrupted and unexecuted work.
- [Language observations](LANGUAGE.md) and [literal selected excerpts](examples/SELECTED_LANGUAGE.md): fewer repetitions, useful checking, mistakes and malformed output.
- [Dated primary-source research](research/README.md): tested hypotheses versus later suggestions.
- [Publication scope and attribution](RIGHTS_AND_SCOPE.md): what is included, withheld and independently reproducible.
- [Transformation manifest](PUBLICATION_MANIFEST.json): public-file hashes, source inventory and checks.

The inventory covers **14 additional weight variants**, 20 isolated server-start attempts, 45 completed generation batches and one interrupted batch: **248 response records and 933,411 observed generated tokens**. These are repeated development observations, not 248 independent benchmark questions. The initial busy-service/eager samples and activation replays are excluded from these totals.

## Reproduce the public summaries

Python's standard library is enough for the integrity and privacy checks:

```sh
python3 verify_publication.py
```

With Matplotlib installed, the included numerical tables regenerate the figures and result table:

```sh
python3 rebuild_figures.py
python3 build_results.py
```

`prepare_public_metrics.py --source-root PATH` is an allowlisted export tool for a separately authorized local archive. The archive is not included. It authenticates exact historical observations; it does not promise that sampled outputs can be recreated by rerunning the model.

All reported generation scores belong to the tested **packed GGUF plus fixed FP32 corrections cast to BF16 before the tensor-parallel all-reduce**. They do not, by themselves, validate a separately merged/requantized weight export. Consult the model card for artifact-specific representation limits.
