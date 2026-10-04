# Deploying the pinned single-node build

[Book](../README.md) · [Complete results](results.md#deployment)

## Problem and scope

The vision-capable deployment occupied a tensor-parallel pair. The goal was to serve it on one Dell Pro Max with GB10 while retaining a 256K request ceiling and several concurrent sequences.
The recipe release could not be pulled anonymously on 2026-09-25 or 2026-09-26, both by tag and digest. The weights were also too large to treat acquisition and placement as incidental setup.

This chapter records the deployment that was run. Commands with generic paths are a reconstruction of that procedure; the offline fixtures exercise its file layout and request handling, not model loading.
No container is built or started by the offline tests.

## Components and provenance

| Component | Pin |
|---|---|
| Recipe | `tpurtell/ds4-mia-exl3-k2-1spark` at `b6b1ef44595ac995bd067d49c00960304c882a8a`, 2026-09-07, "Record FP8 release image" |
| Target | `wrldsuksgo2mars/DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1` at `8347bfb8776287ef2dcab2b46e9f15c655825c3a` |
| Local image | `ve-single:b6b1ef4`, 18.9 GB |
| Published release | `ghcr.io/tpurtell/ds4-mia-exl3-k2-1spark@sha256:6a2f23e95f969cbd468e367b05ece375f6abee75dece57af20ce73632aa4821e`, tag `2026-09-07-fp8-kv` |
| Runtime base | `ghcr.io/anemll/dspark-vllm-gx10@sha256:a83948492cf13df455170fb42885f5ef4db54fefe0feff0f841ecbff464ac9d8` |
| EXL3 source stage | `ghcr.io/tpurtell/deepseek-v4-flash-0731-exl3-k2-spark@sha256:bf383b32a03bdcfef19e42b52778df413c0c47d07c3f4d4e66c78002d17beb74` |
| Serving fork | `tpurtell/sparkinfer-glmrt` at `e0f439532ce3e72c193803c128ba57e46dfd8ea2` |
| Runtime | vLLM `0.25.2.dev0+g752a3a504.d20260714`, `instanttensor==0.1.5`, recipe hotfixes, dSpark, FP8 DS-MLA KV |

The recipe's license was checked on 2026-10-04: MIT, with a LICENSE file present. Target and donor cards describe their weights as MIT. The cookbook's own license is Apache-2.0; see [credits](credits.md).

## What K2.2-D2 means

The target model card reports that the routed experts of the 43 main decoder layers average exactly 2.2 bits per weight.
Every projection starts at K2. The highest weighted-error projections are re-encoded at K3 under a fixed gate/up/down allocation of 3:5:8.
The three built-in draft blocks remain uniform K2, hence D2.
Non-routed tensors retain source values, including the vision encoder, aligner and visual router biases.

Calibration used 1,426 prompts and 1,081,027 tokens, text only. The model card did not measure multimodal quality of the quantized experts.
The vision-category tests in this book are local evidence, not a claim of comprehensive validation of that quantization.

## Platform and prerequisites

Both machines were updated on 2026-09-18: DGX OS 7.6.0, kernel 7.0.0-1019-nvidia, driver 580.178.04.
Each Dell Pro Max with GB10 has 128 GB unified LPDDR5X, sm_121 and aarch64. Linux reported MemTotal 127,533,268 kB (121.6 GiB), with 16 GiB swap.
The bench had about 116 GB available before each start. Production and bench are roles on separate machines of the same class.

Docker and the NVIDIA container toolkit are required; their versions were not recorded.
The recipe compose file supplies `--gpus all`, `--network host`, `--ipc host`, `--shm-size 64g`, memlock=-1, nofile=1048576 and stack=67108864.
This is a record of the recipe settings, not evidence that a fresh machine is ready to load the model.

The weight download uses `huggingface_hub`; the shipped runtime tools otherwise use Python's standard library, with Bash/curl for shell wrappers.
The banner generator separately needs Pillow and is not part of the runtime or test path.
Build-time access to the two registries, GitHub and Hugging Face is required. The weights are not gated.
Exact host-side Python, curl and container-toolkit versions are unknown.

Weights occupy 91.9 GB (85.6 GiB), the image 18.9 GB and the graft adds 5.94 GB, before Docker build and kernel-tuning caches.
There was 2.4-2.7 TB free during the work. At least 150 GB free was a planning figure, not a measured minimum.

## Cache resolution and the reference environment

The entrypoint resolves the target through this structure:

```text
hf/
  hub/
    models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1/
      refs/main
      snapshots/8347bfb8776287ef2dcab2b46e9f15c655825c3a/
```

`refs/main` contains the pinned revision. `HF_CACHE` is the directory containing `hub/`, not the snapshot itself.
The recorded download used `snapshot_download(..., local_dir=...)`, followed by a move into that structure.
The author's documented `hf download <repo> --revision <rev>` writes cache layout directly, but that route was not run here.

[configs/reference.env](../configs/reference.env) retains the environment as run.
A blank `GPU_MEMORY_UTILIZATION` resolves to 0.86 for this model.
`MAX_MODEL_LEN=256000` is a decimal prompt-plus-output ceiling, not a reserved cache size.
`DSPARK_TOKENS` is absent: the entrypoint supplies 3.
`DEFAULT_THINKING=max` is significant; a small output budget can disappear entirely into reasoning.

The entrypoint accepts thinking off/low/high/max, probabilistic or greedy draft sampling, and one served-model-name string.
For the vision model it requires `DSPARK_TOKENS` divisible by 3; the derived experimental image in Chapter 5 changes only that check.
The default API port is 8888. A non-default port needs pass-through in the launcher/compose path, which was not supplied by the recipe by default.

## Procedure as run, with generic paths

Acquire the pinned recipe and build from its Dockerfile. The following acquisition commands are reconstructed; only the local image tag is recorded for the actual build invocation.

```bash
git clone https://github.com/tpurtell/ds4-mia-exl3-k2-1spark.git recipe
git -C recipe checkout b6b1ef44595ac995bd067d49c00960304c882a8a
(cd recipe && docker build --progress=plain -t ve-single:b6b1ef4 .)
mkdir -p models logs
python3 -c 'from huggingface_hub import snapshot_download as d; d("wrldsuksgo2mars/DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1", revision="8347bfb8776287ef2dcab2b46e9f15c655825c3a", local_dir="models/ve-k22-d2")' > logs/download.log 2>&1 && printf '%s\n' 'DL_EXIT=0' >> logs/download.log
bash scripts/ve-finalize-layout.sh models/ve-k22-d2 hf recipe logs/download.log
(cd recipe && ./launch.sh --nodes 1)
docker logs -f ds4-mia-vision-k22-tp1
bash scripts/ve-validate.sh http://127.0.0.1:8888 deepseek-v4-flash-vision-exp recipe/image.png results
bash scripts/run-ve-chain.sh http://127.0.0.1:8888
```

The marker is deliberately retained and documented: the finalizer requires a full log line `DL_EXIT=0`; write it only after a successful download.
It moves the completed directory, removes the download tool's `.cache`, writes `refs/main`, then writes `recipe/.env` from the reference configuration.
It overwrites that env file, so this is an initial-layout tool, not a general configuration merger.

The first build took roughly half an hour while sharing the link with a roughly 50-minute download. The download log retained only its success marker.
The Dockerfile's two bases pulled anonymously. It ended with "Mia runtime + EXL3 port verified", exit 0.

## Integrity and validation

The pinned manifest contains 31 files: 11 shards, the index, quantization metadata, tokenizer material and the complete `encoding/` directory, including the upstream license.
Ten shards are about 8.59 GB and the last 5.93 GB; the index is 12.6 MB and `quantize_config.json` 28.4 MB.
Use the manifest verifier optionally before launching:

```bash
python3 scripts/verify-assets.py ve-k22-d2 hf/hub/models--wrldsuksgo2mars--DeepSeek-V4-Flash-Vision-Exp-EXL3-K2.2-D2-v1/snapshots/8347bfb8776287ef2dcab2b46e9f15c655825c3a
```

Sizes are always checked; available SHA-256 values are checked by default. A null hash means no SHA-256 was supplied for that file, not that its contents were verified.
This manifest verification was not part of the original deployment. The copy to the bench was checked by identical size-and-path listings instead.
To regenerate the manifest, query Hugging Face file metadata at the pinned revision with file metadata enabled; retain name, size, LFS SHA-256 where present, git blob ID and revision-pinned resolve URL. Do not substitute a moving branch. This regeneration procedure was not run for this book.

Validation checks health and model metadata, sends a thinking-off arithmetic request, sends an image data URL, and measures a short essay including prefill.
The public wrapper now fails on missing expected model metadata or empty output. A nonempty response is not automatically a correct image description: inspect it against the image.
The complete historical results are in [the results ledger](results.md#deployment).

## Failure and rule

Anonymous pull failed; building the pinned Dockerfile worked.
Copying the whole cache with unprivileged `rsync` failed with exit 23 because root-owned b12x tuning caches were unreadable. Copy only snapshots; the destination pays the cold start.
The vision recipe's compose healthcheck worked; that observation does not validate a different image's port assumptions.

**Rule:** pin recipe and weights, satisfy the cache layout, then pass text, image and throughput checks before interpreting benchmark results.
