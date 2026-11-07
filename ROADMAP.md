# Open research questions

These are invitations to contribute, not promised results or a release schedule. Propose a small, discriminating test before committing to a large sweep.

## V2 follow-up priorities

The [layer-18 pilot](followup_20261106/REPORT.md) is available for use. Its next
scientific checks are the interrupted warm-start/second-seed replication and
the unrun V2 GSM24 panel. Keep request order, cache state, prompts, sampling and
caps recorded: the follow-up found different trajectories from the same weights
and request seed under different serving histories.

Further contributions can compare V2's merged and sidecar representations,
test selectable reasoning levels with matched sampling, or add original tasks
that distinguish useful self-correction from redundant checking. Preserve the
medium/1.3 reference and report explanation errors alongside final-answer grades.

## Shared research questions

| Question | A useful next experiment | Resources |
|---|---|---|
| Does the selected edit reproduce across seeds? | Freeze an original, checkable panel; compare control and selected edit across matched seeds; report the full distribution and all cutoffs. | GPU |
| How close is merged execution to the sidecar? | Pin both runtimes, compare fixed-prefix numerical outputs and matched generated responses, then run retention cases. Keep numerical and behavioral agreement separate. | GPU / runtime knowledge |
| Does the loop effect survive without a supplied repetitive prefix? | Design original tasks that expose unprompted repetition; compare stopping, correctness and failed-action repeats. | Task design first; GPU for evaluation |
| Which repetition measures miss visible failures? | Compare word n-grams, character runs and stopping behavior; add synthetic counterexamples and transparent thresholds. | CPU |
| Do lexical markers add information beyond length? | Use public measurements to examine normalized rates and matched cases; retain outcome/selection caveats. | CPU |
| Can we improve strict grading without rewriting history? | Add original parsing edge cases and evaluate an explicitly versioned alternative grader alongside the frozen one. | CPU |
| Do neighboring or earlier edits generalize? | State a mechanism and retention criterion before choosing more layers; compare against the simpler three-layer edit. | GPU |
| Can readers audit the evidence more easily? | Improve case navigation, add verified selected excerpts, or clarify an equation with a worked synthetic example. | No GPU |

## Small starting tasks

- Add a synthetic example where a word-repetition score misses a character-level failure.
- Explain the rank-one/64-column distinction with a tiny matrix example.
- Check one selected quote against an authorized local source and report the verification method.
- Improve a reproduction command after trying it in a clean environment.

Use an [experiment issue](https://github.com/Xananthium/Qwen3.8-Weight-Space-Programming/issues/new?template=experiment.yml) to share a hypothesis and proposed comparison. Follow [CONTRIBUTING.md](CONTRIBUTING.md) when adding results.
