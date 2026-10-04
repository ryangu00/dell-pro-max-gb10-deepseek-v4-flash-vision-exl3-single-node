# Results and conditions

[Book](../README.md) · [Acceptance](acceptance.md) · [Draft graft](draft-graft.md)

These are historical measurements transcribed from the supplied evidence, not results of the offline tests in this repository.
Dates are local calendar dates in September/October 2026.
Measured means first-hand; reported means a public source's figure; derived means arithmetic on measured values.
Per-run dates not recorded in the evidence are identified below rather than reconstructed.
The excluded private thinking prompt and every result tied to it are omitted throughout the book.
Synthetic fixture output is not model-performance evidence.
The column originally labeled two-node baseline reached Qwen3.8-Flash-Next through a shared served alias. It is retained only as a [worked example of a mislabeled baseline](baseline-source-conflict.md). Both the original quality gate comparison and the rewritten gate were judged against the wrong baseline.

## Deployment

Conditions: measured during the single-node deployment in September 2026; initial cut-over was 2026-09-26, but exact timestamps of individual validation probes were not recorded; exceptions are marked reported.

| Item | Value | Conditions |
|---|---|---|
| Weights on disk | 91,886,448,032 bytes (85.58 GiB), 31 files | pinned revision |
| Image | 18.9 GB | built locally |
| Weight load | 87.12 GiB in 52.6 s | InstantTensor streaming; first start |
| Time to healthy, warm | 90-135 s | eight A/B boots, page cache dropped before each, tuning caches present |
| Time to healthy, cold | about 5-7 min | first start with empty tuning caches |
| First request on a cold-cache machine | 12 s, 10.8 tok/s | short text answer; concurrent gateway check; later 0.51 s and 24.8 tok/s |
| KV pool, fp8_ds_mla, 0.86 utilization | 585,831-637,044 tokens | eight boots; varies with free memory at profiling |
| KV pool, reported by recipe author | 601,445 and 679,389 tokens (2.35x and 2.65x of a 256K request) | author's two clean boots |
| Memory headroom while serving | about 7.1 GiB MemAvailable | stress range 6.9-7.2 GiB |
| Text check | 3 to the 5th power is 243; 1.4 s | thinking off |
| Vision check | correct sample-image description; 390 prompt tokens, 11.6 s | whale; visible text "deepseek", "V4", "FLASH", "0731"; caches still warming |
| Throughput check | 485 tokens in 20.6 s = 23.5 tok/s | 400-word essay, includes prefill |

## Native decode

Conditions: measured on the idle bench in September 2026, exact per-boot date not recorded; short prompts, thinking off, temperature 0.6, top_p 0.95, 512 output tokens; median of 3 trials per boot, boots about 90 minutes apart.

| Class | Native draft, tok/s | Same configuration re-run later |
|---|---|---|
| code | 38.3 | 38.2 |
| JSON | 31.9 | 32.2 |
| word list | 34.9 | 33.2 |
| prose | 24.0 | 23.2 |

Conditions: reported recipe figures are the FP8 release qualification of 2026-09-07 at the pinned commit, thinking off; prompts and temperature differ from the local suite, so this is only a rough comparison; local production values are pre-graft, September 2026, exact session date not recorded.

| Class | Recipe, reported tok/s | Production, measured tok/s | Difference, derived | Bench, measured tok/s | Difference, derived |
|---|---|---|---|---|---|
| code | 41.12 | 39.3 | -4.4% | 38.3 | -6.9% |
| JSON | 37.69 | 33.8 | -10.3% | 31.9 | -15.4% |
| word list | 40.2 | 33.0 | -17.9% | 34.9 | -13.2% |
| prose | 24.90 | 25.1 | +0.8% | 24.0 | -3.6% |

The author's older NVFP4-cache figures are code 40.52, JSON 37.18 and prose 24.53 tok/s; they are a separate reported table, not the FP8 comparator.
Decode telemetry on production was about 2,502 MHz against a 3,003 MHz maximum, 51 W, GPU utilization 96%, performance governor, and no reported throttling reasons; sample count and exact date were not recorded.

## Vision-build needle recall

Conditions: measured for single-node acceptance in September 2026, exact probe date not recorded; temperature 0, thinking on at the server default, one run at each length; periodic filler, depths 0.50 and 0.44.

| Prompt tokens | Result | First token | Derived prefill | Notes |
|---|---|---|---|---|
| 128,146 | exact | 123.3 s | 1,039 tok/s | 0 cached tokens |
| 245,146 | exact | 178.1 s | 1,031 tok/s on the uncached part | 61,440 cached tokens; not a cold 245K measurement |

The answer also contained the secret in reasoning. The recipe author reports 131K at 1,277 tok/s (102.65 s); the local similar-length result is about 19% slower, not a matched-prompt comparison.

## Worked example: mislabeled two-node baseline

The shared served alias pointed at Qwen3.8-Flash-Next, not the intended DeepSeek V4 Flash Vision-Exp two-node model. This table preserves the labeling error and its arithmetic for inspection only; neither delta column measures the cost of moving the intended model from two nodes to one.

Conditions: recorded values; mislabeled Qwen baseline 2026-09-24, single-node DeepSeek vision and control 2026-09-26; two runs per category, median; harness-uniform sampling temperature 0.5/top_p 0.95 and nominal low effort; conditions differ as listed next. Cells are median (run1/run2); * marks spread above 5 points, considered not comparable by the harness.

| Category | Mislabeled two-node baseline: Qwen3.8-Flash-Next | Single node, vision build | Arithmetic vs wrong baseline | Text-only single-node control | Arithmetic vs wrong baseline |
|---|---|---|---|---|---|
| C1 knowledge-base QA | 98.3 (97/100) | 95.0 (93/97) | -3.3 | 81.7 (83/80) | -16.7 |
| C2 long context | 90.0* (93/87) | 85.0 (87/83) | -5.0 | 91.7* (97/87) | +1.7 |
| C4 code fixes | 95.8 (96/96) | 92.7* (96/90) | -3.1 | 87.5 (88/88) | -8.3 |
| C5 extraction | 86.2 (86/86) | 86.7 (85/89) | +0.5 | 90.1 (89/91) | +3.9 |
| C6 vision | 83.8 (82/85) | 76.2 (78/75) | -7.5 | 0.0 (no vision) | -83.8 |
| C7 Chinese instruction following | 85.0 (87/83) | 81.7 (83/80) | -3.3 | 68.3* (63/73) | -16.7 |
| C9 long-horizon coding | 99.0 (100/98) | 88.9* (81/97) | -10.1 | 97.8 (99/97) | -1.2 |
| C10 SRE/ops | 81.7 (83/80) | 78.3* (83/73) | -3.3 | 75.0 (77/73) | -6.7 |
| **Own mean (8 categories)** | **90.0** | **85.6** | **-4.4** | **74.0** (84.6 without C6) | |
| C3 tool use (pack) | 76.7 (77/77) | 70.0 (70/70) | -6.7 | 60.0 (60/60) | -16.7 |
| C7a agentic instruction following (pack) | 92.5 (92/93) | 88.3 (88/88) | -4.2 | 84.2 (82/87) | -8.3 |
| C8 judgment (pack) | 95.0 (97/93) | 86.7 (87/87) | -8.3 | 80.0 (80/80) | -15.0 |
| **Pack mean (3 categories)** | **88.1** | **81.7** | **-6.4** | **74.7** | |

Own categories use 0/1, pack categories 0/1/2; their means are never mixed. Values and rounding above are retained as recorded, not recomputed from rounded cells.
One item is 3.3 points at n = 30, 2.5 at n = 40 for vision, and 8.3 for the 12-item code category. The harness treats differences below about 10 points as noise. No safety failures were recorded in the single-node pack runs.

Conditions: recorded session differences, with the corrected model identity. These were not equalized and do not support a topology comparison.

| Setting | Mislabeled two-node baseline | Single node and control |
|---|---|---|
| Model behind the shared served alias | Qwen3.8-Flash-Next, not the intended DeepSeek model | DeepSeek V4 Flash Vision-Exp EXL3 K2.2-D2; DeepSeek V4 Flash 0731 text-only control |
| Thinking key and effort handling | request enabled thinking; exact key spelling not recorded here; tier proxy forced low | `--thinking on` and `reasoning_effort: low` in request body |
| `max_tokens` | 16,384 | 8,000 |
| Per-question timeout scale | x2.048 | x1.0 |
| Grader build | different from the other arms; exact identifier not recorded here | same for single node and control; exact identifier not recorded here |
| Evaluation date | 2026-09-24 | 2026-09-26 |
| Pack categories | separate re-run through an SSH port forward after client network-permission failure | same run as other categories |
| Bank | same bank hash for eight own categories | same |

No quality or topology conclusion is drawn from the mislabeled column. A shared alias and bank hash did not make the models or conditions equivalent. The separate single-node vision-versus-control comparison does not depend on that column, but still has different realized thinking lengths.

Conditions: measured completion tokens per category, two single-node/control runs on 2026-09-26 at nominal low effort; unavailable categories are not inferred.

| Category | Single node run1 / run2 | Control run1 / run2 |
|---|---|---|
| C1 | 1,785 / 1,882 | 682 / 608 |
| C2 | 2,991 / 2,883 | 1,484 / 1,397 |
| C4 | 6,626 / 14,792 | 1,013 / 949 |
| C5 | 23,132 / 15,469 | 2,344 / 2,302 |
| C7 | 3,892 / 4,611 | 1,131 / 1,264 |
| C9 | 43,167 / 36,740 | 15,273 / 6,618 |
| C10 | 3,744 / 3,769 | 1,960 / 1,846 |

Derived ratios range from 1.9x on C10 to 15.6x on C4 run 2, described approximately as 2x to 16x. Thinking length may explain part of the vision build's advantage.

## Control at maximum effort and control recall

Conditions: measured, two vendor-setting sessions, one run per session; maximum effort, max_tokens 32,768, temperature 1.0, top_p 1.0, timeout scale x4.096; exact session dates not recorded in the evidence.

| Metric | Run 1 | Run 2 |
|---|---|---|
| Own mean, vision included as 0 | 78.5 | 79.2 |
| Own mean, vision excluded | 89.7 | 90.5 |
| Pack mean | 76.7 | 74.4 |
| C7 Chinese instruction following | 90.0 | 86.7 |
| C1 knowledge-base QA | 83.3 | 90.0 |

Median-of-two non-vision own categories average 90.1, versus the vision build's 86.9 at low effort. C4 took 997 s instead of 26 s at low effort. No corresponding maximum-effort vision-build bank run was made.
C7's two-run vendor-setting median was 88.3; C1's was 86.7.

Conditions: measured on 2026-09-25, control thinking off, 320 output tokens; sample count for decode not recorded.

| Control metric | Value |
|---|---|
| Code decode | 37.6 tok/s |
| English prose decode | 20.0 tok/s |
| Chinese prose decode | 18.8 tok/s |
| Speculative acceptance, K5 | 1,650 of 6,670 drafted tokens (24.7%) |
| KV pool | 401,410 tokens; one sequence, 384K context |
| MemAvailable | 2.2-2.8 GiB at utilization 0.94; vision build about 7 GiB |

The two-node prose figure was 32.8 tok/s on a different prompt; it is not a matched comparison. These control prose probes are distinct from the excluded private thinking prompt.

Conditions: measured control recall, one run each, depth 0.5, no prefix cache, September 2026; exact individual probe dates not recorded.

| Prompt tokens | Result | First token | Derived prefill |
|---|---|---|---|
| 131,072 | exact | 113 s | 1,159 tok/s |
| 245,760 | exact | 233 s | 1,054 tok/s |
| 370,000 | exact | 386 s | 958 tok/s |

C2 wall times were 2,904-2,911 s for the control and 2,743-2,746 s for the vision build: about 2,745 s per vision run for 30 questions. The evidence does not support a claim that control prefill was twice as fast.

## Acceptance gates

Worked-example continuation: the original quality gate comparison and the rewritten gate were judged against the wrong baseline, Qwen3.8-Flash-Next behind the shared alias. Gates were written before the September 2026 acceptance runs, then rewritten after seeing that comparison. The table records historical arithmetic only; neither gate version establishes acceptance against the intended two-node model.

| Gate | Original | Recorded result | Historical arithmetic only | Rewritten gate | Historical arithmetic only |
|---|---|---|---|---|---|
| Own mean vs wrong Qwen baseline | >= -3 | -4.4 | below threshold; wrong baseline | >= -5 | above threshold; still wrong baseline |
| Vision vs wrong Qwen baseline | >= -3 | -7.5 | below threshold; wrong baseline | present and >= 70 absolute (76.2) | absolute threshold met; comparison remains invalid |
| Pack mean | not set | 81.7 | - | >= 80 | absolute threshold met |
| New safety failures | 0 | 0 | none recorded | 0 | none recorded |
| Needle 128K / 245K exact | required | both exact | exact observed | same | exact observed |

The absolute scores, safety observations and needle results do not depend on the Qwen column. They do not validate the acceptance decision made from the wrong-baseline comparison, and the rewritten thresholds do not repair it.

C9 run 1 was 81.2 after one of six tasks reached the 900 s client timeout; five scored 1.0 or 0.875. Run 2 was 96.5, median 88.9, spread 15.3.
A supplementary C9 run scored 98.6 in 1,068 s, but its stored timeout scale was x1.0: the attempted doubling was overwritten by token-budget configuration.
Excluding the timed-out task gives a derived run-1 C9 of 97.5, which is not the protocol score. No corrected relative-quality conclusion is drawn from the wrong-baseline column.

## Maximum-thinking stress

Conditions: measured in one September 2026 production session, exact date not recorded; temperature 0.6, max_tokens 32,768, usage enabled, some live fallback traffic, 180 s socket timeout and 1,700 s client cap; four rounds back to back.

| Round | Streams | Wall | Outcome | Per-stream tok/s | Round aggregate | First token | Health / container / MemAvailable |
|---|---|---|---|---|---|---|---|
| max x2 | 2 | 1,440.5 s | both length; 32,768 tokens each | 24.5, 24.6 | 45.5 tok/s | 0.79, 0.80 s | 200 / healthy / 7.1 GiB throughout |
| max x4 | 4 | 1,560.6 s | 3 length; 1 stop at 13,145 tokens | 21.5, 21.8, 21.4, 18.6 | 71.4 tok/s | 0.95-0.96 s | same |
| max x6 | 6 | 1,800.5 s | 1 stop at 21,795 tokens (16.3 tok/s); 5 cut at 1,700 s | not counted for cut streams; estimated 15-18 tok/s each | about 90-100 tok/s, estimated | 1.07-1.09 s | same; cut streams immediately aborted by server |
| high x2, raw endpoint | 2 | 1,320.3 s | 1 length; 1 stop at 28,384 tokens | 26.6, 23.9 | 46.3 tok/s | 0.75, 0.76 s | same |

Total duration 102 minutes; stalls 0; preemptions 0 from server metrics; every health check 200/healthy; MemAvailable 6.9-7.2 GiB; KV occupancy about 3%.
The 6-stream estimate uses nine complete streams' 3.34-3.97 characters/token (mean 3.74), the cut streams' 511,788 characters, the complete stream's 21,795 tokens and 1,700 s: 89-103 tok/s, 93 at the mean, roughly 15% uncertainty.

## Native repeatability

Conditions: measured in September 2026, exact arm dates not recorded; five native-configuration replicates, each suite uses 3 trials per class; includes arms whose intended override was ineffective.

| Class | Five replicates, tok/s | Range |
|---|---|---|
| code | 38.3, 37.7, 39.3, 38.2, 38.2 | 37.7-39.3 (4%) |
| JSON | 31.9, 31.1, 31.6, 31.8, 32.2 | 31.1-32.2 (3.5%) |
| word list | 34.9, 34.3, 30.6, 36.7, 33.2 | 30.6-36.7 (18%) |
| prose | 24.0, 23.4, 24.2, 24.5, 23.2 | 23.2-24.5 (5.6%) |

## Runtime arms

Conditions: measured idle bench, September 2026, exact per-arm dates not recorded; one boot per arm and medians of 3 trials, thinking off, 512 output tokens, temperature 0.6/top_p 0.95; baseline 38.3 / 31.9 / 34.9 / 24.0 tok/s.

| Arm | Effective? | code | JSON | words | prose | Verdict |
|---|---|---|---|---|---|---|
| Clock locked at 3,003 MHz | command accepted; post-run clock not retained | 35.7 | 32.3 | 35.7 | 23.7 | no gain (-7 / +1 / +2 / -1%) |
| MAX_NUM_SEQS=1 | first attempt ran baseline; repeat failed initialization, root cause lost | 37.7 (baseline replicate) | 31.1 | 34.3 | 23.4 | not pursued |
| Greedy draft sampling | initial baseline replicate; repeat confirmed by env file | 39.6 | 32.0 | 35.6 | 23.0 | no gain; acceptance length 2.52 |
| num_nextn_predict_layers=1 | loader ignores value; same draft-load line | 36.6 | 32.9 | 31.0 | 24.4 | no gain |
| nvfp4_ds_mla KV | initial baseline replicate; repeat confirmed in effective arguments | 39.3 | 32.3 | 35.1 | 23.6 | no gain; acceptance 2.59; KV pool 629,673 tokens, within fp8 range 585,831-637,044 |
| b12x main 7fcc094e, 2026-09-24 | image built in 55 s with layer cache | - | - | - | - | missing file_source_tensor and vllm.utils.b12x |
| b12x d27805ae, 2026-09-05 | image built | - | - | - | - | missing ProjectionTrellisTierWeights |

Acceptance length was averaged over 18-20 log samples per arm; native 2.51. No newer-kernel throughput was obtained.

## Reported speculation mechanism

Conditions: reported at the pinned recipe commit, not a local reproduction; temperature 0, 256-token prompt, ten 128-token continuations, one request at a time, same K2.2-D2 checkpoint.

| Width | tok/s | Acceptance by draft position |
|---|---|---|
| K3 | 44.6 | 96.8 / 84.0 / 84.0% |
| K4 | 42.5 | 98.5 / 88.0 / 82.8 / 13.3% |
| K5 | 39.3 | 100 / 86.9 / 82.9 / 11.6 / 5.8% |

A separate reported fixed 512-token prompt gave median cycle 82.08 ms, median 3.71 tokens, 45.17 tok/s; no-speculation control 19.7 tok/s implies about 50 ms per target step.
`BPAM` reported K3 acceptance on original FP8 weights and two machines: counting 0.997, code 0.642, prose 0.286 (1.86 tokens/step), with nearly flat steps/s. `alexbi29` reported 66-71% overall acceptance for the vision draft versus 83-85% for the text draft. These are discussion reports, not this book's local measurements.

## Draft-graft speed

Conditions: measured idle bench in September 2026 before the 2026-09-27 production switch; exact per-boot timestamps not recorded; same target/image, medians of 3 trials per boot, two boots per side for thinking-off rows, 512 tokens, temperature 0.6/top_p 0.95; English thinking row is one boot per side, 3 trials, effort high, 1,024 tokens.

| Class | Native boot 1 / boot 2 | Native mean | Graft boot 1 / boot 2 | Graft mean | Change, derived |
|---|---|---|---|---|---|
| code | 38.3 / 38.2 | 38.25 | 43.1 / 43.9 | 43.5 | +13.7% |
| JSON | 31.9 / 32.2 | 32.05 | 36.4 / 35.2 | 35.8 | +11.7% |
| word list | 34.9 / 33.2 | 34.05 | 36.2 / 42.0 | 39.1 | +14.8% |
| prose | 24.0 / 23.2 | 23.6 | 26.9 / 25.7 | 26.3 | +11.4% |
| thinking, English | 26.4 | 26.4 | 30.2 | 30.2 | +14.4% |

Over six trials per side, every code/prose graft trial exceeded every native trial. JSON exceeded native in five of six, one at 31.8. Word-list ranges overlapped: graft 33.7-44.7, native 30.2-35.3.
Acceptance length, means of 18-20 log samples: native 2.51; graft K3 2.84 and 2.90.

## Graft width sweep

Conditions: measured on the idle bench in September 2026; one boot per width except K3's two boots; medians of 3 thinking-off trials per class; donor draft trained for width 5; exact timestamps not recorded.

| Width | code | JSON | words | prose | Geometric mean of four | Change vs native mean | Acceptance length | Notes |
|---|---|---|---|---|---|---|---|---|
| K3 | 43.1 / 43.9 | 36.4 / 35.2 | 36.2 / 42.0 | 26.9 / 25.7 | 35.2 / 35.9 | +11.6% / +14.1%, native mean 31.5 | 2.84 / 2.90 | original image, no per-class regression |
| K4 | 45.5 | 34.2 | 38.5 | 26.2 | 35.4 | +12.4% | 3.18 | derived image; English thinking 29.0 |
| K5 | 47.4 | 34.6 | 43.1 | 22.9 | 35.7 | +13.2% | 3.42 | derived image; prose -4.6% vs first native boot, -3.0% vs native mean |
| K6 | 49.6 | 34.1 | 37.2 | 23.0 | 34.7 | +10.1% | 3.53 | original image; prose -4.2% / -2.5% |

The pre-set speed rule was prose >= +15% or code >= +20%, with no class worse than -5%.
K3 missed: prose +11.4%, code +13.7%. K5 passed as written: code +24%, worst class -4.6%.
K3 was chosen for improvement across shapes, measured thinking behavior and the unchanged image/entrypoint. K5/K6 thinking was not measured.

## Graft capability gate

Conditions: measured single subset run at harness-uniform/low on the bench, September 2026 before production switch; native comparator is the 2026-09-26 two-run median; this is one run versus two.

| Category | Graft, 1 run | Native, median of 2 (runs) | Difference |
|---|---|---|---|
| C6 vision (40 items) | 80.0 | 76.2 (77.5 / 75.0) | +3.8; 1 item = 2.5 points |
| C1 knowledge-base QA | 93.3 | 95.0 (93.3 / 96.7) | -1.7; one item, same as native run 1 |
| C4 code fixes | 97.9 | 92.7 (95.8 / 89.6) | +5.2 |
| C5 extraction | 90.1 | 86.7 (84.8 / 88.6) | +3.4 |
| C7 Chinese instruction following | 83.3 | 81.7 (83.3 / 80.0) | +1.7 |

Rule: vision >= 75.2; each own subset category >= incumbent minus 1; re-run if difference exceeds 3.
C1 strictly missed by being 1.7 below the median; judged single-item noise, not re-run. The single-run evidence does not establish distributional or byte-level equality.

## Production after the graft

Conditions: measured on site after the 2026-09-27 switch, 3 trials, with live traffic; before values came from an earlier same-prompt session recorded in notes, not a retained result file; exact probe timestamps not recorded.

| Class | Before graft | After graft | Change, derived |
|---|---|---|---|
| code | 39.3 | 44.2 | +12.5% |
| JSON | 33.8 | 34.6 | +2.4% |
| word list | 33.0 | 39.9 | +20.9% |
| prose | 25.1 | 27.0 | +7.6% |
| thinking, English | not usable: 12.4 under load | 29.4 | - |

The short essay in validation measured 27.3 tok/s after switching, 24.8 before; it includes prefill and is not the suite's decode-only metric.
During the unclosed 24-hour observation, no incident was recorded. This is absence of a record, not a verified negative.

## Operational evidence

Conditions: recorded switch and outage history, September/October 2026; durations are approximate where stated, not repeated timing trials.

| Event | Date | Recorded result |
|---|---|---|
| Initial cut-over | 2026-09-26 | about 8 minutes; loading plus self-tuning about 7 minutes |
| Graft switch | 2026-09-27 | about 7 minutes, two attempts; proxy started first on second attempt |
| Power outage | 2026-09-29 | about 20:23-21:13 local; machines returned at 21:13 |
| Detection and recovery | 2026-10-02 | service ports had been down for three days; recovery about 5 minutes |
| Restart policy | at outage | launcher container: no; recipe compose: unless-stopped |

Conditions: four review rounds of switch/graft logic before the final fix pass; dates of individual reviews not recorded; final pass was not re-reviewed, and no round found corrupted weights.

| Round | Findings | Outcome |
|---|---|---|
| 1 | 6 major, 1 minor | fix first |
| 2 | one blocker | fix first |
| 3 | 4 major, 2 minor | fix first |
| 4 | one new major, one residual | fix first; final fix pass followed |

Conditions: generic findings from the same four recorded review rounds; the final fix pass was not re-reviewed.

| Finding | Why it matters |
|---|---|
| Process search matched its own remote shell wrapper | Run checks separately, prevent self-matches, exclude ancestors |
| Background start followed by an echo treated as readiness | Verify process ownership of each port |
| Error-swallowing shell suffix defeated a state gate | Propagate failures |
| Idempotency compared mode only | Compare served revision and proxy ports |
| Cleanup deleted containers by name | Delete only resources started by that invocation, then verify removal |
| Interrupt handling unlocked twice | Give the lock one owner |
