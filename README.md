# <img src="img/zonda_logo.png" width="110" valign="middle" alt="Zonda"/> Request

**Zonda Request** is the backend of [Zonda](https://zonda.ethz.ch/), the C2SM
web service that generates ICON grids and their external parameters. You
configure your domains on the Zonda website, submit the exported request as a
GitHub issue in this repository, and receive a download link on the same issue
once the data is ready.

## The Zonda Ecosystem

| Component | Role |
|---|---|
| [Zonda website](https://zonda.ethz.ch/) | Web UI where you configure your grids and export the request as JSON |
| **zonda-request** (this repo) | Receives requests as GitHub issues, processes them and reports the result |
| [ICON-Tools](https://gitlab.dkrz.de/dwd-sw/dwd_icon_tools) and [EXTPAR](https://github.com/C2SM-RCM/extpar) | Grid generation and external parameter computation |

## Submitting a Request

1. Configure your grids on [zonda.ethz.ch](https://zonda.ethz.ch/) and copy
   the request to the clipboard.
2. Open a new issue with the
   [data request template](https://github.com/C2SM/zonda-request/issues/new?template=data_request.md),
   give it a meaningful title and paste the request into the `json` code block.
3. Create the issue. Processing starts automatically, and the issue is
   labeled `submitted`.
4. When processing has finished, a comment on the issue links to your data,
   or to the log files if processing failed. Large requests can take several
   hours, and requests may wait in a queue when the server is busy.

The data is available for **7 days**. Afterwards, it is deleted and the issue
is closed.

To process a request again, for example after correcting the JSON in the
issue description, write a comment containing only `rerun request`. This works
on open issues that are not currently `submitted`, and always uses the JSON in
the current issue description.

## Status Labels

| Label | Meaning |
|---|---|
| ![submitted](https://img.shields.io/badge/submitted-yellow) | The request is queued or being processed |
| ![invalid](https://img.shields.io/badge/invalid-lightblue) | The JSON in the issue is missing or invalid. Correct it and comment `rerun request` |
| ![completed](https://img.shields.io/badge/completed-green) | The data is ready for download |
| ![failed](https://img.shields.io/badge/failed-red) | Processing failed, see the log files linked in the comment |
| ![aborted](https://img.shields.io/badge/aborted-lightgray) | The request hit the 24-hour limit or was terminated |

## Documentation

- [Zonda documentation](https://zonda.ethz.ch/docs/): how to use the website,
  and a description of the [output files](https://zonda.ethz.ch/docs/backend).
- [C2SM internal documentation](https://intranet.c2sm.ethz.ch/docs/webtools/zonda/zonda-request/)
  (C2SM members only): how the backend works and how to operate it.

## Getting Help

If your request fails and the log files do not explain why, mention a
maintainer (`@stelliom` or `@mjaehn`) on your request issue and include the
relevant lines of the log files.

For anything else, please use the issue templates:

- [Report a bug](https://github.com/C2SM/zonda-request/issues/new?template=bug_report.yml)
- [Request a new feature](https://github.com/C2SM/zonda-request/issues/new?template=feature_request.yml)

## License

This project is licensed under the MIT License. See `LICENSE`.
