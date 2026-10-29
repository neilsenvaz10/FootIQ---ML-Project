# Phase 4.14: why the FootIQ-Backend supervisor keeps disappearing

Status: investigation done with non-disruptive checks. The healthy backend (pid 6688) was never restarted or stopped, Bundesliga and La Liga syncing was not interrupted, PL/SA/FL1 are not active, production data, models and Git are untouched (production hash unchanged, request ledger unchanged at 7 lines).

## Findings
| Question | Evidence | Answer |
|---|---|---|
| Crashing, exiting normally or terminated? | `supervisor.log` has no "supervisor stopped" line for either supervisor (20620, 13724); `data\run\supervisor-8000.pid` and `backend-8000.pid` were left behind (the `finally` cleanup never ran); task `LastTaskResult` = 0xC000013A (STATUS_CONTROL_C_EXIT, a console control event); the backend (pid 17636 shim / 6688) kept running after its parent vanished | **Terminated from outside.** Not a script error (the `finally` block would have logged), not a normal exit (`exit` paths log first) |
| Who terminated it? | Nothing in the repo kills PowerShell (searched tests, app, scripts); the Task Scheduler operational log is **disabled**, so no record exists; parent of the supervisor was `svchost` (Task Scheduler), not the editor. Both disappearances happened while the Claude desktop session was active; the result code fits a closed or signalled hidden console | **Not proven.** The cause is outside FootIQ's code; I could not identify the sender |
| Does Task Scheduler restart it? | Task settings: RestartCount 3, RestartInterval 1 min, MultipleInstances IgnoreNew, single trigger **at log on**. After the termination the task sat in "Ready" with no next run and nothing restarted it | **No.** The restart setting did not apply; there is no other trigger, so after any termination nothing starts it until the next log-on |
| Can it monitor an existing backend without a duplicate? | Private-port experiment (8123, private copy, sync off) and then production (below) | **Yes.** `run` sees the port owner, logs "not starting a second backend, waiting 15 s", and takes over within one 15 s cycle if the backend dies. The one-scheduler lock and the supervisor mutex stay intact |
| Side effect of a dead supervisor | experiment step 4 reproduced the exact production state: status "Supervisor NOT running" while the backend answers; `start` and `restart` refuse ("port in use ... stop it first") | A killed supervisor leaves an unsupervised backend that the helper commands cannot adopt |

## Verification results
- **Experiment** (`data/supervised/phase4/p414/supervisor_experiment.ps1`, evidence in `experiment_evidence.txt`): orphan backend alive, then supervisor started: no second backend (1 listener); orphan killed: supervisor started its own within 15 s (1 listener); supervisor hard-killed alone: backend survived, no "stopped" line, pid file left, status NOT running, `start` refused: **this reproduces production's signature**; a new supervisor adopted the survivor without a duplicate. Production hash, listener (6688) and ledger unchanged.
- **Production**: I started the existing task (`Start-ScheduledTask FootIQ-Backend`); supervisor pid 15620 (parent svchost) logged "port 8000 is already in use by process 6688: not starting a second backend". Listener still 6688, 1 scheduler thread, lock held, next check 23:00:36Z, 0 failed cycles, ledger unchanged (no request). State: **supervisor running again**.
- A passive watcher (`liveness_watch.ps1`, reads only, one line a minute for 8 hours) writes `data/supervised/phase4/p414/liveness.log`. If the supervisor dies again, the log will show when, whether other PowerShell/Claude processes changed at the same moment, and whether the backend survived.

## Root cause
The supervisor process is being **killed by an external console/session event** (not by a crash, a normal exit or FootIQ code), and the task configuration has **no mechanism to bring it back**: the only trigger is log-on and the "restart on failure" setting did not fire. The backend and the scheduler are independent of it and survive, which is why synchronisation never stopped. The exact sender is unknown (Task Scheduler history is off).

## Recommended smallest safe correction (NOT applied; needs your approval because it edits the Task Scheduler task)
1. **Add a repeating trigger** (every 5 minutes, no end) to the existing `FootIQ-Backend` task, keeping `MultipleInstances IgnoreNew`. A killed supervisor is then restarted within 5 minutes; a live one makes the extra start a no-op (mutex), and a new supervisor adopts the running backend as verified above. It never restarts or interrupts the backend. Reversible: remove the trigger.
   ```powershell
   $t = Get-ScheduledTask -TaskName 'FootIQ-Backend'
   $rep = New-ScheduledTaskTrigger -Once -At (Get-Date).AddMinutes(1) -RepetitionInterval (New-TimeSpan -Minutes 5)
   Set-ScheduledTask -TaskName 'FootIQ-Backend' -Trigger @($t.Triggers[0], $rep)
   ```
2. If the watcher still shows deaths that are not revived, **enable the Task Scheduler history** (`wevtutil set-log Microsoft-Windows-TaskScheduler/Operational /enabled:true`, needs an elevated prompt) to see who ends the task, and consider running the supervisor without a console (`conhost --headless powershell ...`) so a closed window cannot signal it.
3. Optional script tidy-up (code change, separate approval): let `footiq_service.ps1 start` start a supervisor in adopt mode when an unsupervised backend already owns the port, instead of refusing; and have `status` say "backend running, unsupervised".
Nothing else needs to change: the adoption behaviour, mutex and scheduler lock already do the right thing.
