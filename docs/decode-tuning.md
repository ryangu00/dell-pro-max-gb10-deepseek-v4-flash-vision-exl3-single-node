# Where decode speed goes

[Book](../README.md) · [Runtime arms](results.md#runtime-arms) · [Repeatability](results.md#native-repeatability)

## Problem

The single node decoded short-prompt prose at about 24-25 tok/s and code at about 39 tok/s with thinking off.
The goal was more decode speed without giving up vision. The first question was whether runtime settings or speculative acceptance limited progress.

## Mechanism: step cost versus accepted tokens

A speculative step costs time regardless of how many proposed tokens survive target verification.
Reported recipe numerics at the pinned commit give a median 82.08 ms cycle and 3.71 emitted tokens on a fixed 512-token prompt, or 45.17 tok/s.
A no-speculation control reports 19.7 tok/s, implying about 50 ms for a target step.
These reported figures are workload-specific and are not measurements from the local suite.

The author's controlled K3/K4/K5 sweep is reproduced in [results](results.md#reported-speculation-mechanism).
At K4, fourth-position acceptance falls to 13.3%; at K5, the final positions are 11.6% and 5.8%.
More proposals therefore need not produce more useful tokens per unit time.
`BPAM`'s public per-workload table and `alexbi29`'s acceptance question motivated measuring acceptance before changing kernels.
See [credits](credits.md) for exact public handles and source links.

## Suite implementation

[suite.py](../scripts/suite.py) preserves the code, structured JSON, numbered-word-list and prose prompts.
Each request gets a random 6-hex prefix to reduce prefix-cache reuse.
The measured short-prompt mode uses temperature 0.6, top_p 0.95, thinking off and 512 output tokens.
One warm-up precedes three trials per class. The reported class value is the median trial rate, not a rate recomputed from medians of duration and token count.

A trial rate is `completion_tokens / (wall - time_to_first_token)`.
This excludes prefill and differs from the essay validation rate, which includes it.
The public script requires usage: it no longer falls back to counting deltas when usage is absent.
The offline tests use canned timings to check the arithmetic independently of wall-clock jitter.

`--think high` selects two prompts at 1,024 output tokens.
The English warehouse-routing prompt is preserved; the other is a neutral English synthetic replacement of similar scale.
No historical measurement is attached to that replacement. It needs a fresh bench run before any model-rate claim can be made.

## Per-arm environment and procedure

The launcher sources its selected env file after the caller's environment.
Passing `DRAFT_SAMPLE_METHOD=greedy` as a parent-shell override was insufficient when `.env` still set probabilistic.
Three purported arms initially ran the baseline: single sequence, greedy sampling and NVFP4 KV.
The clue was the unchanged KV pool, about 626-627K tokens.

[arm.sh](../scripts/arm.sh) now creates a separate env file for every label, selects it through `ENV_FILE`, and preserves launch and container logs.
Overrides change only the arm copy. Labels and variable names are checked before file creation.
The script stops/removes the named container, starts through the recipe launcher, waits for health, prints effective arguments and runs the suite.
A failed launch or an exited container captures its full log before returning nonzero.
Read the emitted arguments yourself: printing them does not mechanically prove every override took effect.

```bash
python3 scripts/suite.py --base http://127.0.0.1:8888 --trials 3 --label baseline --out results/arms.jsonl
RECIPE_DIR=./recipe ARM_DIR=./results/arms bash scripts/arm.sh greedy DRAFT_SAMPLE_METHOD=greedy
RECIPE_DIR=./recipe ARM_DIR=./results/arms bash scripts/arm.sh kv-nvfp4 KV_CACHE_DTYPE=nvfp4_ds_mla
```

The historical procedure dropped page cache before each boot. The public wrapper makes that optional through `DROP_CACHES=1`; it requires Linux and working noninteractive sudo.
With the default disabled, record that condition difference when comparing a fresh run to the historical boot timings.
The script's output location, recipe directory, container and base URL are configurable. Defaults use relative paths and the recipe's loopback endpoint.

The recorded arm order was baseline, clock lock, single sequence, greedy draft sampling, one next-layer, NVFP4 KV, corrected repeats of ineffective arms, then two newer kernel builds.
Each valid arm required confirmation from effective startup arguments.
Experiments ran on the idle bench, not the production service.

## Results and failures

All measured runtime arms and their effective-status caveats are in [the full table](results.md#runtime-arms).
The native acceptance mean was 2.51 tokens per step; greedy gave 2.52 and NVFP4 KV 2.59, each based on 18-20 log samples.
No runtime arm established a gain.
Setting `num_nextn_predict_layers=1` alone was ignored by the loader; the same "draft model loaded: 111 params" line appeared.
That line proves a draft loaded, not which checkpoint supplied it.

The clock-lock command was accepted at 3,003 MHz, but its post-run reading was not retained.
The corrected single-sequence attempt failed initialization; the root cause was lost when the next arm removed the container.
The public wrapper's failure-log capture addresses that measurement gap; it cannot recover the lost historical reason.

The b12x main build at `7fcc094e` failed on missing `file_source_tensor` and `vllm.utils.b12x`.
The older `d27805ae` build failed on `ProjectionTrellisTierWeights` from `b12x.moe.fused_moe.trellis`.
The pinned engine and mixed-quantization adapter depended on the older API. A kernel change would require porting the adapter.
Both experimental images were deleted. No kernel speed result exists.

## Noise, unrun work and rule

Five native replicates span 4% for code, 3.5% for JSON, 18% for words and 5.6% for prose.
The word-list class cannot resolve an effect smaller than about 15% in these measurements.
A production thinking prompt gave 12.4 tok/s under load versus 26-30 on the idle bench; production traffic is a material condition, not a nuisance to omit.

Planned but not run: batch-token limits 4096/16384, explicit CUDA-graph capture sizes and `DSPARK_ENFORCE_EAGER`.
The recursive K3+K3 idea was not tried locally; the recipe reports that it was investigated and rejected.
A graft plus newer kernels was not tested because the newer kernels would not start.

**Rule:** measure acceptance, retain native replicates, print effective settings, and preserve startup failures. The recorded runtime knobs left acceptance effectively unchanged, which motivated changing the draft itself.
