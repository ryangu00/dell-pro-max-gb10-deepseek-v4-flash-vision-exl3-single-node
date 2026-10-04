# Reproduce it without the original infrastructure

[Book](../README.md) · [Deployment](deployment.md) · [Graft mechanism](draft-graft.md)

There are two different activities here: exercise the publication's tools with synthetic fixtures, or reproduce the historical model experiment on suitable hardware.
The first needs no model, GPU, Docker daemon, private bank, credentials or network access.
The second requires the pinned upstream assets and the hardware/prerequisites recorded in the deployment chapter.
Synthetic fixture numbers are arbitrary test inputs and are never the historical benchmark results.

## Offline tests

From the repository root, run:

```bash
PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -p test_offline.py -v
PYTHONDONTWRITEBYTECODE=1 python3 tests/test_graft_range.py
```

The suite creates its temporary trees inside the repository and removes them afterwards.
It uses an in-memory HTTP transport: the actual fixture server's request handlers run against byte buffers, so no listening socket is required.
Subprocess tools receive the same transport through the offline runner; shell wrappers use stub executables in a temporary PATH.
A standalone loopback server is also supplied for environments that permit binding, but real socket serving was not validated during this publication.

The public adaptations also make missing benchmark usage and missing safety fields explicit, close needle responses, and return nonzero for failed probes; historical tables remain unchanged.

The tests exercise successful and corrupted grafts, sample/full verification, strict range status/header/length checks, stable source length, source immutability, relative links, index accounting and both mixed namespaces.
They also cover asset size/hash failures, cache finalization and its marker, validation/model metadata, needle/shuffle behavior, benchmark medians and missing usage, streaming silence/client caps, arithmetic-only aggregate comparison without quality-gate verdicts, shell syntax and arm failure logs.
The derived-image test runs its exact sed replacement and grep guard on a toy entrypoint. It does not build an image.

## Build reusable synthetic fixtures

```bash
python3 fixtures/build.py fixtures/generated
```

The fixture tree contains small safetensors-format byte files, donor/target JSON metadata, a blank PNG, an asset manifest and aggregate result rows.
The `synthetic-reference` result label contains arbitrary test scores; it represents neither the mislabeled historical Qwen baseline nor a valid two-node baseline.
They are deliberately not runnable model weights, private evaluation data or a published derivative snapshot.
The following target path is synthetic even though it uses the same revision-shaped directory convention:

```bash
TARGET=fixtures/generated/snapshots/8347bfb8776287ef2dcab2b46e9f15c655825c3a
SOURCE=http://127.0.0.1:8888
```

## Exercise the graft without a socket

The offline runner intercepts urllib requests and passes them to the fixture handlers in memory. It rejects non-loopback destination names.
Its source directory is the synthetic donor folder. The source URL selects the fixture transport; nothing listens at that address.

```bash
python3 fixtures/offline.py fixtures/generated/donor scripts/graft0731.py --target "$TARGET" --source-base "$SOURCE" --dry-run
python3 fixtures/offline.py fixtures/generated/donor scripts/graft0731.py --target "$TARGET" --source-base "$SOURCE"
LOCAL=fixtures/generated/snapshots/0731d22a00000000000000000000000000000001/model-mtp-draft0731-d22.safetensors
python3 fixtures/offline.py fixtures/generated/donor scripts/verify_graft_bytes.py --local "$LOCAL" --source-base "$SOURCE" --all
```

The dry-run reports a synthetic inventory. The full run publishes a separate synthetic snapshot and refuses to overwrite it on a second run.
A verifier success here proves that fixture bytes and derived biases match. It is not the historical 9,313-tensor verification.
The unit test deliberately corrupts a copied bias and checks for a nonzero verifier exit.

## Exercise the probes and comparison

```bash
python3 fixtures/offline.py fixtures/generated scripts/suite.py --base "$SOURCE" --trials 3 --label synthetic --out fixtures/generated/arms.jsonl
python3 fixtures/offline.py fixtures/generated scripts/suite.py --base "$SOURCE" --trials 3 --label synthetic-thinking --think high --out fixtures/generated/arms.jsonl
python3 fixtures/offline.py fixtures/generated scripts/v3_1m_needle.py --base "$SOURCE" --model deepseek-v4-flash-vision-exp --tokens 128000 --shuffle --out fixtures/generated/needle.jsonl
python3 fixtures/offline.py fixtures/generated scripts/ve_stress.py --rounds 8888:2 --health-url "$SOURCE/health" --heartbeat 1 --out fixtures/generated/stress
python3 scripts/g2_compare.py --runs fixtures/generated/runs --baseline synthetic-reference --vision vision --control control
python3 scripts/verify-assets.py ve-k22-d2 fixtures/generated/assets --manifest fixtures/generated/manifest.json
bash scripts/run-ve-chain.sh --dry-run
```

Fixture responses echo the synthetic needle, return synthetic usage and terminate normally. Their wall times and rates are meaningless as model measurements.
The `OFFLINE_MODE` environment variable can select `silent`, `long` or `missing-usage` for failure-path exercises through the offline runner.
The tests already assert silence detection, missing-usage rejection and client-cap behavior using short synthetic timings.
The shell validator and finalizer are exercised with isolated fake files by the test suite.
The arm wrapper is exercised with stub docker, curl, sudo and python3 executables, including an exited-container failure and log capture.

## Optional real loopback stub

On a machine that permits local listening, start the fixture server in one terminal:

```bash
python3 fixtures/server.py fixtures/generated --port 8888
```

In another terminal, the ordinary validator can use the synthetic image:

```bash
bash scripts/ve-validate.sh http://127.0.0.1:8888 deepseek-v4-flash-vision-exp fixtures/generated/image.png fixtures/generated/validation
```

Stop the server with an interrupt when finished. This checks request transport against a stub, not image understanding.
Use `fixtures/generated/donor` as the server root for actual-loopback graft tests; the in-memory commands above need no server at all.

## What is required for the real experiment

Follow [deployment](deployment.md) for pinned acquisition, the local Dockerfile build, cache placement, reference env, warm-up and validation.
Those steps need upstream registry/GitHub/Hugging Face access. The published release's anonymous availability was a dated failure, not checked again here.
The exact Docker/toolkit versions and some probe dates were not recorded; do not silently fill them in.

Run the needle probes with actual usage reporting and distinguish a warm prefix from a cold prefill.
Choose an evaluation harness and publish its effective headers. The private 11-category bank is unavailable, so the historical scores cannot be regenerated from this repository.
The public comparison script can process aggregate rows from another harness, but those rows answer that harness's question, not the private bank's.
It labels deltas as arithmetic and does not judge quality gates because aggregate rows cannot establish model identity or matched conditions. The cookbook's [mislabeled-baseline example](baseline-source-conflict.md) shows why: a shared served alias reached Qwen3.8-Flash-Next, and both the original quality gate comparison and the rewritten gate were judged against the wrong baseline.

For decode work, use the idle bench, preserve a native replicate, and inspect every arm's effective settings.
For the graft, build beside the original snapshot, verify bytes, run the speed/capability gates, and preserve their misses as well as any exceptions.
A replacement thinking prompt must be measured anew; the public book does not assign it the omitted private prompt's result.
No equality test, 100K-context graft test, six-way graft test or closed 24-hour observation is available here.

## Publication checks and deliberate gaps

The banner source is provided at `docs/make_banner.py`;
The README retains the requested image reference for later rendering.
LICENSE and .gitignore are unchanged copies of the supplied templates.
No private switching script, boot unit, fallback topology or private evaluation wrapper is shipped.
