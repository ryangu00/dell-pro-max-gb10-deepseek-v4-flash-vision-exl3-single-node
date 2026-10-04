# Switching, rollback and the outage

[Book](../README.md) · [Operational results](results.md#operational-evidence)

## Problem and mechanism

One serving machine is a single point of failure.
The recorded operation needed an initial cut-over, a draft-graft restart and, later, recovery from a power outage.
A correct model file is only part of that operation: stale processes, stolen ports and misleading checks can leave a switch in the wrong state.

The private switching script is not shipped. Its behavior is described generically because its remote hosts, service topology and fallback configuration are not portable prerequisites.
It acquired a mutual-exclusion lock directory, stopped the relevant service processes, started tier proxies before the engine, waited for the expected endpoints, and verified the model revision actually loaded.
Requests during restart windows were served by other configured fallback endpoints. This book provides no public reproduction of that private fallback chain.

## Procedure as run

On 2026-09-26 the text-only control was stopped, the vision build started, warmed and validated through the gateway with a long prompt, image and quality tier, then the bench copy was stopped.
The cut-over took about 8 minutes; loading and kernel self-tuning took about 7 minutes.

On 2026-09-27 the env file was backed up, the graft revision added and the switch executed.
The first attempt loaded the engine but the tier proxy could not bind because an internal engine process had taken a needed port.
The switch was changed to start the proxy first; the second attempt succeeded, taking about 7 minutes across the two attempts.
The [tier-proxy sibling](https://github.com/ryangu00/dell-pro-max-gb10-thinking-tier-proxy) contains that ordering pitfall; its private addresses are not reproduced here.

## Rollback

Keep both snapshots and a backup of the env file.
Stand the service down, restore `MODEL_REVISION=8347bfb8776287ef2dcab2b46e9f15c655825c3a`, then start the proxy and engine in the required order.
Removing the override uses the original default, but explicitly writing the original revision makes the rollback check less ambiguous.
Inspect container start time and the model's logged snapshot path, not only the alias returned by `/v1/models`.
The target snapshot is unchanged by the graft and remains available for this reversal.

These are the recorded generic steps, not a shipped multi-host switch command.
The original stop path could also stop work on the second machine; recovery therefore first confirmed that machine was idle.
A public reader must determine their own service ownership before adapting that behavior.

## Review findings

Four review rounds returned fix-first findings: 6 major and 1 minor; one blocker; 4 major and 2 minor; then one new major and one residual.
A final fix pass followed the fourth round without another review. No round found corrupted weights.
Self-tests ran against the bench, including proxy start and verified cleanup; those results are historical, not tests of a public switching script.

| Symptom | Mechanism | Repair recorded |
|---|---|---|
| Proxy existence always succeeds | search matches its own remote-shell command line | separate command, self-match-resistant pattern, exclude ancestors |
| Start prints success but port is not held | echo after backgrounding proves only shell progress | verify port ownership by process ID |
| Failed stop still advances state | error-swallowing shell suffix | propagate status through the gate |
| Re-running keeps wrong draft | idempotency checked mode only | compare revision and proxy state |
| Failure cleanup removes unrelated state | delete-by-name instead of ownership | delete only resources this invocation started, then verify disappearance |
| Interrupt releases lock twice | competing cleanup paths | one lock owner |

These findings make the switch's own side effects part of acceptance, not an afterthought to model health.

## The outage

On 2026-09-29, about 20:23-21:13 local, a site-wide power outage took the machines down. They returned at 21:13.
The launcher-started serving container had restart policy `no`; tier proxies were ordinary background processes.
The service ports stayed down for three days until 2026-10-02.
The monitor alerted only on state changes, so the initial outage produced one alert but the continuing outage did not repeat it.
Recovery was one switch command, about 5 minutes, after the second machine was confirmed idle.

The recipe compose file says `restart: unless-stopped`, but that was not the policy on the container actually launched.
Check the effective container policy rather than assuming compose intent carried through another launch path:

```bash
docker inspect ds4-mia-vision-k22-tp1 --format '{{.HostConfig.RestartPolicy.Name}}'
docker inspect ds4-mia-vision-k22-tp1 --format '{{.State.StartedAt}}'
```

A boot path was not added in the recorded work because an automatic restart loop after a maximum-thinking death was considered a risk.
That leaves an unresolved gap, not a completed reliability fix.
The 24-hour post-graft observation also has no closing record. The precise statement is: no incident was recorded.

## What failed and the rule

There was no boot-time service path and no repeated unacknowledged alert.
The absence of a later alert did not establish availability.
A rollback check based on alias or HTTP status could have accepted a stale process.

**Rule:** a production service needs a boot path and an alert that repeats until acknowledged; a switch must verify ownership, actual revision and cleanup. Those mechanisms remain to be implemented and validated for any new deployment.
