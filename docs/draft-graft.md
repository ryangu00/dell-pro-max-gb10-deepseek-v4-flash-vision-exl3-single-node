# Grafting the text sibling's draft

[Book](../README.md) · [Speed](results.md#draft-graft-speed) · [Capability](results.md#graft-capability-gate)

## Problem and hypothesis

The vision target's native draft accepted about 2.5 tokens per step in the local suite.
The public discussion suggested that the text sibling's draft accepted more, including on a photo-description workload reported by `Unkto`.
The question was whether its tensors could be substituted while leaving the target, image and entrypoint unchanged at K3.
This is a specific same-family compatibility experiment, not a general claim that arbitrary drafts are interchangeable.

## Header compatibility

Target: `wrldsuksgo2mars/DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1`, revision `8347bfb8776287ef2dcab2b46e9f15c655825c3a`.
Donor: `wrldsuksgo2mars/DeepSeek-V4-Flash-0731-EXL3-K2.1-D2.2-calibrated-v3`, revision `7827301eed170e2a5e394f45a13cc66561c601ed`.
The public model cards describe both as MIT.

Both checkpoints have draft blocks `mtp.0` through `mtp.2`, target layer IDs [40, 41, 42], block size 5, Markov rank 256 and the same noise token.
The vision draft adds only three key names: `mtp.N.ffn.gate.bias_vl`.
There are 461 shape differences in draft expert tensors because donor D2.2 is mixed K2/K3: 1,843 projections at K2 and 461 at K3 out of 2,304.
The target draft is uniform K2.
Those shape differences are why copying bytes without updating storage metadata is insufficient.

The donor's draft tensors occupy shards 2, 10 and 11 of 11.
The recorded inventory, re-checked against the public donor headers on 2026-10-03, is 9,313 tensors, 5.94 GB and three contiguous payload range requests.
Header and metadata requests are additional; "three" is not the total HTTP request count.

## The transformation, enough to implement independently

1. Read each shard's initial little-endian header length and JSON header with byte ranges. Select every `mtp.*` tensor, retaining dtype, shape and source offsets.
2. Sort selected tensors by shard and source position. Coalesce nearby payload ranges and construct a new safetensors header whose offsets address their packed output bytes.
3. Write the new header and copied source bytes to a partial file. Append each `mtp.N.ffn.gate.bias_vl` by copying the corresponding newly written donor `gate.bias` bytes.
4. Build a staging snapshot next to the original. Point unchanged files back to the original with relative symlinks, so cache relocation inside a container does not break them.
5. Rewrite every `mtp.*` entry in `model.safetensors.index.json` to `model-mtp-draft0731-d22.safetensors`. The image's index-trusting patch prevents old embedded draft tensors from being loaded.
6. Sum the byte extents of the tensors actually referenced by the final map to recompute `metadata.total_size`; do not sum all physical shard contents.
7. Replace the target's `mtp.*` quantization storage entries with the donor's 2,304 entries. Copy `ds4rt_inline_mixed_namespaces.mtp` into both quantization metadata locations.
8. Set `num_nextn_predict_layers` from the donor, which is 1. Publish the complete directory by a rename. Refuse an already-existing destination revision.

The synthetic revision `0731d22a00000000000000000000000000000001` is a local cache identifier, not an upstream commit or provenance claim.
It lets offline resolution select the sibling snapshot. The original revision is never modified.
The public script accepts target path, donor identity, shard names and new revision as arguments; a source-base override exists for a pinned mirror or local fixture.

## Byte-range invariants

A successful download status alone is insufficient: an ignored Range request can return a file head of plausible length containing the wrong bytes.
Every range response must be HTTP 206, with a full-string `Content-Range` matching requested start/end and a legal total greater than the end offset.
The same file must keep the same total length across requests.
The received header and payload lengths must match the requested intervals; trailing payload bytes are rejected.
Failures close their response, truncate back to the start of that payload group and retry the group rather than appending corrupted partial data.

The original index undercounted referenced bytes by 483,393,536: 91,822,259,960 versus 92,305,653,496.
That was a metadata accounting defect, not evidence that the recorded graft had corrupted tensor payloads.
The verifier independently fetches donor bytes from the pinned source, compares SHA-256 per tensor, and checks all three derived visual biases against their source biases.

Sample mode uses the largest ten tensors plus a seeded random 40; the union can be smaller on a tiny fixture.
`--all` checks every source draft tensor. A mismatch gives a nonzero exit.
The historical sample checked 50 tensors, 0.45 GB, with 0 mismatches; full verification checked 9,313 tensors, 5.94 GB, with 0 mismatches and all 3 biases equal.
The production and bench copies also had identical whole-file SHA-256 values.
These are historical results, separate from the synthetic test performed for this publication.

## Procedure as run and public commands

The dry-run still fetches metadata and headers when aimed at the public donor; it is not a no-network mode.
To exercise it with no network, use the [offline fixture instructions](reproduce.md).
For actual previously acquired target weights, the generic path form is:

```bash
TARGET=hf/hub/models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1/snapshots/8347bfb8776287ef2dcab2b46e9f15c655825c3a
python3 scripts/graft0731.py --target "$TARGET" --dry-run
python3 scripts/graft0731.py --target "$TARGET"
LOCAL=hf/hub/models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1/snapshots/0731d22a00000000000000000000000000000001/model-mtp-draft0731-d22.safetensors
python3 scripts/verify_graft_bytes.py --local "$LOCAL" --n 40
python3 scripts/verify_graft_bytes.py --local "$LOCAL" --all
```

The recorded sequence was dry-run, build, sample verification, full verification, bench speed A/B, width sweep, high-effort check, capability subset, then production switch.
The production switch on 2026-09-27 added `MODEL_REVISION=0731d22a00000000000000000000000000000001` to a backed-up env file.
The selected K3 kept the image and entrypoint unchanged. Its acceptance mean increased from 2.51 to 2.84 and 2.90 on two boots.
The effective revision in startup logs identifies the graft; "DSpark draft model loaded: 111 params" alone does not.

## Width sweep and the gate that missed

K4 and K5 need [Dockerfile.k5](../configs/Dockerfile.k5), which disables the entrypoint's divisible-by-3 check.
The grafted config declares one next-layer, so vLLM accepts these widths. K6 already satisfies the original entrypoint check.
The Dockerfile's grep guard makes a moved or changed source line fail the build rather than silently producing an unchanged experimental image.
The offline test executes the sed substitution and its guard on a toy entrypoint; it does not build a container image.

```bash
docker build -f configs/Dockerfile.k5 -t ve-single:b6b1ef4-k5 .
RECIPE_DIR=./recipe bash scripts/arm.sh graft-k5 MODEL_REVISION=0731d22a00000000000000000000000000000001 DSPARK_TOKENS=5 RECIPE_IMAGE=ve-single:b6b1ef4-k5
```

[The full width table](results.md#graft-width-sweep) distinguishes two K3 boots from single boots at K4/K5/K6.
The pre-set speed rule required prose +15% or code +20%, and no class worse than -5%.
Selected K3 gave prose +11.4% and code +13.7%, so it missed.
K5 passed as written with code +24% and worst class -4.6%, but prose regressed.
K3 was shipped for gains in every shape, the best measured thinking result among tested thinking widths, and no image/entrypoint change.
K5 and K6 were not measured in thinking mode. Code-heavy, low-entropy traffic was the stated reason a reader might test them separately.

## Capability, production and limits

The graft subset was one run at harness-uniform/low against native two-run medians.
Vision scored 80.0 versus 76.2, but n = 40 means one item is 2.5 points; +3.8 is inside this evidence's noise.
The capability rule required vision >= 75.2, every own subset category at least incumbent minus 1, and a re-run if the difference exceeded 3.
C1's 93.3 was 1.7 below the native median, strictly missing the minus-1 rule. It equaled native run 1 and was judged single-item noise, without a re-run.
The recorded subset was not a clean unconditional pass of every stated rule.

Speculative decoding is theoretically lossless with respect to the target distribution, but no byte-level greedy-output equality test was run here.
The observed vision scores do not prove equality. The arithmetic text check returned 243 for 3 to the 5th power.
Production gains were measured under live traffic and differed from the bench; [all publishable rows](results.md#production-after-the-graft) retain that condition.

The 24-hour observation was opened but never closed in writing; no incident was recorded before the later outage.
The replacement thinking prompt was not benchmarked on a model. No measurements establish graft gains at 100K-token contexts or six-way concurrency.
A kernel-plus-graft experiment could not run because the newer kernels would not start.

**Rule:** inspect compatibility, update index and quantization metadata together, verify copied bytes, then evaluate speed and capability before switching the production revision.
