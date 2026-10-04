# Worked example: a mislabeled two-node baseline

The column originally labeled two-node baseline was not a measurement of the intended DeepSeek V4 Flash Vision-Exp deployment. A shared served alias pointed at Qwen3.8-Flash-Next. The alias was mistaken for model identity.
The correction identifies the wrong model; a valid same-model two-node quality baseline remains unavailable.

The [historical column and deltas](results.md#worked-example-mislabeled-two-node-baseline) are retained only to show how a mislabeled baseline invalidated a comparison. Own 90.0, pack 88.1 and vision 83.8, and the recorded deltas -4.4 / -6.4 / -7.5, do not measure the cost of moving the intended model from two nodes to one. No quality or topology conclusion is drawn from that column.

| Condition | Mislabeled two-node baseline | Single-node arms |
|---|---|---|
| Model behind the served alias | Qwen3.8-Flash-Next, not the intended DeepSeek model | DeepSeek V4 Flash Vision-Exp EXL3 K2.2-D2; separate DeepSeek V4 Flash 0731 text-only control |
| Grader build | different build; exact identifier not recorded here | same build for vision and control; exact identifier not recorded here |
| Output budget, `max_tokens` | 16,384 | 8,000 |
| Thinking key and effort handling | request enabled thinking; tier proxy forced low | `--thinking on` with request `reasoning_effort: low` |
| Per-question timeout scale | x2.048 | x1.0 |
| Evaluation date | 2026-09-24 | 2026-09-26 |
| Pack collection | separate re-run through a port forward after client network-permission failure | collected with the other categories |

The available record does not specify the baseline request's exact thinking-key spelling. The key and application mechanisms were not established as equivalent; neither the key spelling nor missing grader identifiers are reconstructed here. The eight own categories shared a bank hash, which did not establish model or condition equivalence.

The original quality gate comparison and the rewritten gate were judged against the wrong baseline. Their historical arithmetic is documented in [the gate table](results.md#acceptance-gates), but neither decision validates acceptance against the intended two-node model. Rewriting thresholds did not repair the baseline.
Single-node absolute scores, safety observations and needle checks remain observations of those runs. The native-versus-grafted speed and capability experiments used their own single-node comparators and are separate from this error.

Before using a baseline, verify the model behind the alias and record the grader build, output budget, thinking keys, effective effort and timeouts. A shared served name is not that verification.
