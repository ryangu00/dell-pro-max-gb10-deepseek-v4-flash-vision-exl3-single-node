# Acceptance evidence and gates

[Book](../README.md) · [Mislabeled-baseline worked example](results.md#worked-example-mislabeled-two-node-baseline)

## The question

Can one Dell Pro Max with GB10 supply the vision-capable service at an acceptable quality cost, and how does that choice compare with keeping the tensor-parallel pair or using a text-only single-node control?
The intended question remains unanswered against the pair: [the column labeled two-node baseline reached Qwen3.8-Flash-Next through a shared served alias](baseline-source-conflict.md), not the intended DeepSeek V4 Flash Vision-Exp model.
The column is retained only as a worked example of a mislabeled baseline. Model identity, grader build, output budget, thinking keys and effective effort, timeouts, dates and pack collection differed. Its arithmetic cannot establish the quality cost of moving the same model from two nodes to one.

## Mechanism: separate score families and preserve uncertainty

The bank has 11 categories. Own categories score 0/1; pack categories score 0/1/2. Each category is run twice, summarized by its median and range.
Own and pack means are separate. A spread above 5 points marks the runs not comparable by the harness rule.
Do not reconstruct exact scores from the rounded run values in the summary table.

| Category | Workload | Score family |
|---|---|---|
| C1 | knowledge-base QA | own |
| C2 | stacked-document long context; published method lists 32K / 95K / 200K | own |
| C3 | tool use | pack |
| C4 | single-file code fixes with hidden tests | own |
| C5 | structured extraction | own |
| C6 | OCR, charts, architecture diagrams; 40 items | own |
| C7 | Chinese/bilingual instruction following | own |
| C7a | agentic instruction following | pack |
| C8 | judgment | pack |
| C9 | long-horizon coding; 6 repositories | own |
| C10 | SRE/ops | own |

The question texts, expected answers and per-item results are not public. The shipped comparison tool consumes only aggregate result rows.
A synthetic row looks like `{"cat":"c1-kbqa","runs":[90,90],"safety":0}`; these example values are invented test data, not bank results.
`--own` and `--pack` take category lists. Missing categories prevent a mean from being computed; missing safety fields are reported as unknown.
The tool reports arithmetic only. Aggregate rows and served labels do not verify model identity or matched conditions, so the tool does not issue original or rewritten quality-gate verdicts.

## Procedure and the exact session flags

Needle probes went directly to the engine with periodic filler, an 8-digit code at a random depth between 35% and 65%, temperature 0, max_tokens 1500 and timeout 1700.
`--tokens` controls filler construction rather than measuring actual tokenizer output; read `usage.prompt_tokens` for the actual length.
The two recorded lengths were 128,146 and 245,146 tokens, not the nominal arguments 128000 and 245000.
The second probe reused 61,440 prefix tokens. `--shuffle` randomizes filler to reduce this reuse but was not the condition of the reported pair.

The original evaluation wrappers are published as flag documentation only. They depend on an unavailable private bank and a private runner build with `--recipe-arm` support.
Map these flags to the public method's runner; a compatible runnable private evaluation command cannot be supplied here.

| Session | Exact workload flags, excluding paths and endpoint selection |
|---|---|
| Full comparison | `--recipe-arm harness-uniform --reason "same-harness comparison" --tier private --runs 2 --parallel 1 --thinking on --chat-kwargs '{"reasoning_effort":"low"}'` |
| C9 supplementary re-run | same arm and thinking flags; `--cats c9-long-coding --runs 1 --parallel 1` |
| Graft capability subset | same arm and thinking flags; `--cats c6-vision,c1-kbqa,c4-code,c5-extract,c7-zhif --runs 1 --parallel 1` |

The reason string above is a neutral replacement for the required rationale field. The harness refused an arm without a stated reason.
The single-node and control full runs used default max_tokens 8000. Temperature was 0.5 and top_p 0.95 under harness-uniform.
The vendor-setting control used maximum effort, max_tokens 32,768, temperature 1.0, top_p 1.0 and timeout x4.096.

Compare aggregate result directories with:

```bash
python3 scripts/g2_compare.py --runs fixtures/generated/runs --baseline synthetic-reference --vision vision --control control
```

A reference assembled from separate own and pack sessions can use comma-separated labels in `--baseline`; that option selects input data and does not validate it as a baseline.
The tool selects the latest matching result directory when a direct label directory is absent. Verify the selected data and do not mix unrelated dates.

## Controls and conditions

The planned two-node reference was the Vision-Exp deployment described by the sibling cookbook. The shared served alias instead pointed at Qwen3.8-Flash-Next. That model supplied the mislabeled baseline column; the column cannot describe a DeepSeek topology change. The Qwen checkpoint precision and serving stack are not recorded here.

The text-only control used `0xSero/deepseek-v4-flash-0731-spark` with the pinned `MiaAI-Lab/DeepSeek-v4-Flash-One-DGX-Spark` launcher.
It retained 216 of 256 routed experts per layer, used EXL3 3.0 bpw, one sequence, 384K context and K5.
This describes the control used here; the sibling cookbook is linked neutrally and is not used to supply an engine claim or speed target.

The mislabeled Qwen baseline ran on 2026-09-24; the single-node DeepSeek candidates ran on 2026-09-26.
The wrong baseline used 16,384 output tokens and timeout x2.048, while single-node arms used 8,000 and x1.0.
Thinking keys and application differed: the baseline request enabled thinking and a tier proxy forced low; single-node runs used `--thinking on` and supplied `reasoning_effort: low` in the request body. The baseline request's exact thinking-key spelling is not recorded here.
The grader build differed; exact build identifiers are not recorded here. Single-node vision and control shared a grader build, and the same bank hash covered the eight own categories across the comparison.
Wrong-baseline pack sessions were re-run through a port forward after client network permissions interrupted the first attempt; single-node pack categories were collected with the other categories.
None of these differences was equalized afterwards.

## Results and the rewritten gates

The complete [worked example, condition and token tables](results.md#worked-example-mislabeled-two-node-baseline) should be read together.
In that mislabeled-baseline example, the vision build's own mean was 85.6 against Qwen3.8-Flash-Next's 90.0, a recorded -4.4 difference; pack mean 81.7 against 88.1, -6.4; vision 76.2 against 83.8, -7.5. These are historical arithmetic, not a two-to-one quality cost.
The original quality gate comparison and the rewritten gate were judged against the wrong baseline. The original own and vision thresholds each allowed -3; their arithmetic misses do not establish a quality loss against the intended two-node model.
No new safety failures were recorded, and both needle probes returned the code.

The historical rewrite used own >= -5, vision present and >= 70 absolute, and pack >= 80.
Its own threshold still compared against the wrong Qwen baseline. Meeting those rewritten thresholds did not validate the acceptance decision or establish equivalence to the intended pair. The absolute vision and pack observations remain reportable independently; they do not repair the wrong-baseline judgment.

## Why C9 is not a clean capability loss

One of six tasks reached the 900 s client timeout and scored 0. Run 1 became 81.2; run 2 was 96.5; median 88.9, spread 15.3.
The supplementary run was intended to double timeouts but the runner reset the timeout scale from the token budget.
Its stored header says x1.0. It scored 98.6 in 1,068 s and is evidence only of a successful re-run.
Ignoring the timed-out task would give 97.5 for run 1, but that is not the protocol score. No corrected relative-quality conclusion is drawn from the wrong-baseline column.

## What did not work, and the rule

A nominal effort label did not equalize generated reasoning. The vision build generated approximately 2x to 16x the control's completion tokens per category.
At low effort it was stronger in important categories, but at maximum effort the text-only control's seven non-vision own-category medians averaged 90.1 against 86.9 for vision at low.
The vision build was never run at the vendor's maximum-effort setting across the bank.

Needle recall with periodic filler at two depths is a plumbing check, not a long-context quality study.
At n = 40, a single vision item is 2.5 points. That score granularity does not make the wrong-baseline comparison valid.
The private bank cannot be reproduced from the aggregate tables or the synthetic fixtures.

**Rule:** establish the reference model identity, then publish original and rewritten gates, preserve per-run scores and spread, and report output budgets, timeouts, grader versions and realized thinking lengths alongside any comparison.
