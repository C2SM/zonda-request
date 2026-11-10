# <img src="img/zonda_logo.png" width="110" valign="middle" alt="Zonda"/> Request

**Zonda Request** is the backend of
[Zonda](https://zonda.ethz.ch/), the C2SM web service that generates ICON grids
and their external parameters. It takes a request submitted as a GitHub issue,
processes it with ICON-Tools and EXTPAR on `iacdipl-7.ethz.ch`, and posts a
download link back to the issue.

User-facing documentation is available at
<https://zonda.ethz.ch/docs/backend>. This README describes how the backend
works and how to operate it.

## The Zonda Ecosystem

| Component | Role |
|---|---|
| [zonda-frontend](https://github.com/C2SM/zonda-frontend) | Web UI where users configure their grids and export the request as JSON |
| **zonda-request** (this repo) | Request intake via GitHub issues, orchestration on iacdipl-7, status reporting |
| [ICON-Tools](https://gitlab.dkrz.de/dwd-sw/dwd_icon_tools) and [EXTPAR](https://github.com/C2SM-RCM/extpar) | Grid generation and external parameter computation, run as podman containers |

## How It Works

```text
Issue labeled 'data request'    'rerun request' comment    workflow_dispatch
            |                              |                       |
            +--------------> process_request.yml <-----------------+
                                       |  GitHub-hosted runner
                                       |  validate JSON, check out backend_tag,
                                       |  rsync to iacdipl-7 via fog.ethz.ch,
                                       |  launch detached, exit
                                       v
                          iacdipl-7 (l_c2sm), scripts/run_pipeline.sh
                          wait for a slot, process, archive, report
                                       |
                                       v
                     comment and status label on the issue (as Zonda-Bot)
```

> [!IMPORTANT]
> The request pipeline runs **detached**. A green `process_request` run only
> means that the pipeline was launched. The actual result of a request is shown
> by the labels and comments on its issue.

### Step by step

1. **Submit a request.** The user opens an issue with the
   [data request template](.github/ISSUE_TEMPLATE/data_request.md) and pastes
   the JSON exported by the frontend into its `json` code block. The template
   applies the `data request` label.

2. **Validate and launch.** The label triggers
   [`process_request.yml`](.github/workflows/process_request.yml), which:
   - sets the `submitted` label and removes any previous status label,
   - reads the JSON from the issue body. If it is missing or invalid, the
     workflow comments the `jq` error on the issue, sets `invalid` and stops,
   - reads `.zonda.backend_tag` from the JSON and checks out this repository
     at that ref. Without a tag, the latest release is used. Release tags older
     than `MIN_BACKEND_TAG` are raised to it, with a comment on the issue,
   - creates a run directory on iacdipl-7 and copies the checkout into it with
     `rsync`. GitHub-hosted runners cannot reach ETH-internal hosts directly,
     so all ssh traffic goes through the `fog.ethz.ch` bastion,
   - starts [`scripts/run_pipeline.sh`](scripts/run_pipeline.sh) with
     `setsid nohup` and exits within seconds.

3. **Process on iacdipl-7.** `run_pipeline.sh` then:
   - waits for one of 6 slots (see [Concurrency](#concurrency)),
   - installs the locked environment with `uv sync --frozen`,
   - hashes the run ID into a 16-character, non-guessable path component,
   - fetches the request JSON from the issue again and writes `config.json`,
   - runs [`src/processing/process_request.py`](src/processing/process_request.py),
     which generates the grids with ICON-Tools, runs EXTPAR and creates the
     visualizations. The whole step is limited to 24 hours.

4. **Report.** When the pipeline ends, successfully or not,
   [`scripts/archive_output.py`](scripts/archive_output.py) moves the output
   zip and the log file to `/net/co2/c2sm-services/zonda-request/<hash>/`,
   served as `https://data.iac.ethz.ch/zonda/<hash>`.
   [`scripts/report.py`](scripts/report.py) then comments on the issue with
   the download link or a pointer to the log files and replaces `submitted`
   with `completed`, `failed` or `aborted`. If only the archiving fails, a
   successful run is reported as `failed` with a dedicated message, so that no
   dead link is posted. Finally, an `EXIT` trap removes the workspace.

5. **Rerun.** A comment starting with `rerun request` on an open issue
   that does not carry `submitted` triggers `process_request.yml` again. Every
   run reads the current issue body, so edits to the JSON take effect.

6. **Expiry.** Output is available for 7 days.
   [`cleanup_iacdipl7.yml`](.github/workflows/cleanup_iacdipl7.yml) deletes
   older output every night, and
   [`close_old_data_request_issues.yml`](.github/workflows/close_old_data_request_issues.yml)
   closes data request issues older than 7 days.

### Why detached

GitHub-hosted runners stop a job after 6 hours, while large requests take
longer. The pipeline therefore runs on iacdipl-7 independently of the
Actions job. This has four consequences:

- The workflow's `GITHUB_TOKEN` expires when the job ends. The pipeline
  reports back as the [`Zonda-Bot` GitHub App](#zonda-bot-github-app).
- No GitHub-side timeout applies. `run_pipeline.sh` enforces its own limit of
  24 hours and reports `aborted` when it is reached.
- There is no `if: always()` teardown. The workspace is removed in an `EXIT`
  trap, and the daily cleanup removes run directories left by runs that died
  before the trap ran.
- A run that dies without reporting leaves its issue on `submitted`. The log
  in its run directory (see [Run directories](#run-directories)) shows why.

### Concurrency

At `OMP_NUM_THREADS=24` on a 128-core machine, more than about 5 concurrent
requests oversubscribe iacdipl-7. `run_pipeline.sh` therefore takes one of
`n_slots=6` `flock` slots under `~/.zonda/slots/` before it starts working.
Further requests wait on iacdipl-7, already labeled `submitted`, until a slot
becomes free. Waiting costs nothing, as detached runs are not bound to any job
timeout.

## Testsuite

[`testsuite.yml`](.github/workflows/testsuite.yml) runs a fixed set of
requests with the code under review and reports a regular pass/fail check.
Unlike request processing, it runs synchronously, and nothing is archived,
published or reported to the issues (`run_pipeline.sh --testsuite`).

It is triggered by adding the `run testsuite` label to a pull request, every
night at 01:17 (Europe/Zurich) on `main`, and via `workflow_dispatch`. The
label is removed when the run finishes, so adding it again starts a new run.
Pull requests from forks have no access to the ssh secrets and are skipped.

| Issue | Case |
|---|---|
| [#1697](https://github.com/C2SM/zonda-request/issues/1697) | DWD ICON-D2 |
| [#1698](https://github.com/C2SM/zonda-request/issues/1698) | MCH ICON-CH2 |
| [#1699](https://github.com/C2SM/zonda-request/issues/1699) | CORDEX EUR-12 |
| [#1700](https://github.com/C2SM/zonda-request/issues/1700) | DWD ICON-Global-Eu |
| [#1701](https://github.com/C2SM/zonda-request/issues/1701) | Input grid with nesting |
| [#1702](https://github.com/C2SM/zonda-request/issues/1702) | Circular domain over North Pole |

These issues carry the `testsuite` label instead of `data request`, so they
never trigger request processing. They only hold the reference JSON, which is
fetched at test time like for a real request.

## Repository Structure

```text
.
|-- .github/
|   |-- ISSUE_TEMPLATE/
|   |   |-- bug_report.yml
|   |   |-- data_request.md                    # Template for data requests
|   |   `-- feature_request.yml
|   |-- actions/
|   |   `-- configure-ssh/action.yml           # ssh keys and config for the fog -> iacdipl-7 hop
|   `-- workflows/
|       |-- process_request.yml                # Launches a request on iacdipl-7 (detached)
|       |-- testsuite.yml                      # Runs the fixture requests synchronously
|       |-- cleanup_iacdipl7.yml               # Daily cleanup of output, run directories and podman
|       |-- close_old_data_request_issues.yml  # Daily closing of request issues older than 7 days
|       |-- ping_devs_on_issue.yml             # Pings maintainers on bug reports and feature requests
|       `-- shellcheck.yml                     # Lints scripts/*.sh on pull requests
|-- img/
|   `-- zonda_logo.png
|-- scripts/
|   |-- run_pipeline.sh                        # Detached entrypoint on iacdipl-7
|   |-- pipeline_functions.sh                  # Pipeline steps, slot handling, reporting
|   |-- env.sh                                 # Shared constants (paths, threads, slots, App ids)
|   |-- hash.py                                # Hashes the run ID for the download path
|   |-- create_config_file.py                  # Fetches the request JSON from the issue
|   |-- archive_output.py                      # Moves output zip and log to the data server
|   |-- report.py                              # Comments and sets labels as Zonda-Bot
|   `-- cleanup_data_server.py                 # Deletes expired output
|-- src/
|   |-- processing/                            # Grid generation, EXTPAR, output handling
|   |-- utilities/
|   `-- visualization/
|-- pyproject.toml                             # Python dependencies
`-- uv.lock                                    # Locked dependency versions
```

## Issue Status Labels

| Label | Meaning |
|---|---|
| ![submitted](https://img.shields.io/badge/submitted-yellow) | The request is queued or being processed |
| ![invalid](https://img.shields.io/badge/invalid-lightblue) | The JSON in the issue is missing or invalid |
| ![completed](https://img.shields.io/badge/completed-green) | The data is ready for download |
| ![failed](https://img.shields.io/badge/failed-red) | Processing or publishing failed, see the log files |
| ![aborted](https://img.shields.io/badge/aborted-lightgray) | The run hit the 24-hour limit or was terminated |

## Operations

### Versioning

Each request is processed with the backend version given in
`.zonda.backend_tag` of its JSON, which the frontend fills in. Branch names
are accepted as well, which is useful for testing. To retire old releases,
raise `MIN_BACKEND_TAG` in `process_request.yml`.

### Secrets and variables

The ssh hop uses two accounts, `ti16102` on `fog.ethz.ch` and `l_c2sm` on
`iacdipl-7.ethz.ch`. Both usernames and the host keys are hardcoded in
[`configure-ssh`](.github/actions/configure-ssh/action.yml). Configure the keys
under **Settings > Secrets and variables > Actions**:

| Name | Type | Purpose |
|---|---|---|
| `FOG_SSH_KEY` | Secret | Private key for `ti16102` on `fog.ethz.ch` (bastion hop only) |
| `IACDIPL7_SSH_KEY` | Secret | Private key for `l_c2sm` on `iacdipl-7.ethz.ch` |

Set them from a file, for example
`gh secret set FOG_SSH_KEY --repo C2SM/zonda-request < ~/.ssh/id_ed25519_iac_ti`,
so that the trailing newline is kept. Setting secrets requires admin
permission on the repository. See
[#2914](https://github.com/C2SM/zonda-request/issues/2914) for details.

### Zonda-Bot GitHub App

The detached pipeline accesses GitHub as the org-owned `Zonda-Bot` App, so
comments are authored by `zonda-bot[bot]`.

| Property | Value |
|---|---|
| App ID | `4546985` |
| Installation ID | `152656376` |
| Installed on | `C2SM/zonda-request` only |
| Permissions | Issues: read and write |
| Private key | `~/.config/zonda/bot.pem` on iacdipl-7, owner `l_c2sm`, mode 600 |
| Master copy | C2SM password manager |

The two ids are not secret and are set in [`scripts/env.sh`](scripts/env.sh).
The private key is deliberately not a repository secret, so it never passes
through a workflow. `report.py` exchanges it for an installation token that is
valid for one hour, right before it posts.

App private keys do not expire, so there is nothing to rotate. To replace a
lost or leaked key:

1. On the App settings page (`C2SM` org > Settings > Developer settings >
   GitHub Apps > Zonda-Bot), generate a new private key and store it in the
   password manager.
2. Write it to `~/.config/zonda/bot.pem` on iacdipl-7, mode 600.
3. Delete the old key on the App settings page.

### Host setup on iacdipl-7

One-time setup as `l_c2sm`, reached with
`ssh -J <eth-user>@fog.ethz.ch l_c2sm@iacdipl-7.ethz.ch`:

- Install [`uv`](https://docs.astral.sh/uv/) to `~/.local/bin/uv`. The
  scripts call it by absolute path, as non-interactive ssh sessions do not
  source `~/.bashrc`. `uv` downloads Python 3.12 on first use if needed.
- Ensure write access to `/ssd/c2sm-services/` and
  `/net/co2/c2sm-services/zonda-request/`, and read access to
  `/net/co2/c2sm-data/extpar-input-data/`.
- Place the Zonda-Bot private key as described above.
- Make the ICON-Tools image available in the local podman store as
  `execute:<icontools_tag>`. Pulling it requires `podman login` to the DKRZ
  registry with DKRZ credentials. The EXTPAR image is pulled from Docker Hub
  (`docker.io/c2sm/extpar`) automatically.

Paths, thread count and slot count are defined in
[`scripts/env.sh`](scripts/env.sh).

### Run directories

Each run gets its own directory on iacdipl-7:

```text
/ssd/c2sm-services/zonda-request-runs/
|-- request-<issue>/run-<n>-<run_id>[-<attempt>][-debug]/
|   |-- workspace/      # Removed at the end of the run, unless debug
|   `-- pipeline.log    # Kept
`-- testsuite/run-<issue>-<run_id>-<attempt>/
```

`<n>` counts the runs of an issue. The path is printed as a notice in the
summary of each workflow run. `cleanup_iacdipl7.yml` removes run directories
older than 7 days, except debug runs, which have to be removed by hand.

### Manual runs

`process_request.yml` can (re-)process an existing data request issue:

```bash
gh workflow run process_request.yml --repo C2SM/zonda-request \
  -f issue_number=<issue> [-f debug=true]
```

The JSON is always read from the issue, never from the inputs. Comments from
manual runs are marked with a note linking to the workflow run. With
`debug=true`, the workspace is kept for inspection.

`cleanup_iacdipl7.yml` defaults to a dry run when started manually:

```bash
gh workflow run cleanup_iacdipl7.yml --repo C2SM/zonda-request -f dry_run=false
```

### Container runtimes

Requests are processed with podman. For use outside this pipeline,
`process_request.py --apptainer` runs the containers with Apptainer instead.
The images must then be present in the workspace as `icon_tools.sif` and
`extpar.sif`.

## Scripts

All scripts are called by `run_pipeline.sh` on iacdipl-7 and run with
`uv run --frozen python ...` from the repository root. The scripts that access
GitHub read the App identity from `ZONDA_APP_ID`, `ZONDA_APP_INSTALLATION_ID`
and `ZONDA_APP_KEY` (default `~/.config/zonda/bot.pem`), or from
`--app-id`, `--installation-id` and `--app-key`.

### `scripts/hash.py`

```bash
python scripts/hash.py --run-id <run_id> --hash-file hash.txt
```

Writes a 16-character SHA-256 hash of the run ID to `hash.txt`, used as the
non-guessable directory name on the data server.

### `scripts/create_config_file.py`

```bash
python scripts/create_config_file.py --config config.json --issue-id <issue>
```

Fetches the issue body, extracts the `json` code block and writes it to
`config.json`.

### `src/processing/process_request.py`

```bash
PYTHONPATH=src python src/processing/process_request.py --config config.json \
  --workspace <dir> --extpar-raw-data <dir> [--logfile <file>] [--apptainer]
```

Generates the grids, runs EXTPAR, creates the visualizations and zips the
output as `zonda_output_<request_name>.zip` in the workspace.

### `scripts/archive_output.py`

```bash
python scripts/archive_output.py --config config.json --workspace <dir> \
  --destination /net/co2/c2sm-services/zonda-request/ --hash-file hash.txt \
  [--logfile <file>]
```

Moves the output zip and copies the log file to `<destination>/<hash>/`.

### `scripts/report.py`

```bash
python scripts/report.py --config config.json --hash-file hash.txt \
  --issue-id <issue> [--note <markdown>] [--no-logs] \
  (--success | --failure | --aborted | --publish-failure)
```

Comments the result on the issue and replaces `submitted` with `completed`,
`failed` or `aborted`. `--publish-failure` reports a successful run whose
output could not be archived. `--no-logs` omits the link to the log files.

### `scripts/cleanup_data_server.py`

```bash
python3 scripts/cleanup_data_server.py --path <dir> --threshold 7 \
  [--dry-run] [--exclude <dir> ...]
```

Deletes files and directories under `--path` older than `--threshold` days.
It only uses the standard library, so `cleanup_iacdipl7.yml` runs it with the
system Python.

## Contribution

Please use the following issue templates:

- [Report a bug](https://github.com/C2SM/zonda-request/issues/new?template=bug_report.yml)
- [Request a new feature](https://github.com/C2SM/zonda-request/issues/new?template=feature_request.yml)

## License

This project is licensed under the MIT License. See `LICENSE`.
