# <img src="https://polybox.ethz.ch/index.php/s/c8uZqrzwk45wpBx/download?path=%2Fpng&files=zonda-high-resolution-logo-transparent.png" width="110" valign="middle" alt="zonda"/> Request

Backend service for generating ICON grids and EXTPAR data products for Zonda.

This repository contains the processing logic behind Zonda request handling. It exists to turn request configurations into generated grids, EXTPAR files, derived lat-lon products, visualizations, and packaged output for downstream use.

## Looking for Zonda?

If you want to use Zonda rather than work on its backend, start with the Zonda backend documentation:

https://zonda.ethz.ch/docs/backend

## What this repository does

At a high level, the request workflow:

- loads a request configuration
- prepares a workspace
- generates ICON grids
- runs EXTPAR
- optionally generates lat-lon grids
- creates visualizations
- collects and archives the output

The main orchestration entry point is `src/processing/process_request.py`.

## Repository structure

- `src/processing` – core request-processing workflow and managers for grids, EXTPAR, and output
- `src/utilities` – shared helper functions such as config loading and shell command utilities
- `src/visualization` – plotting/visualization code for generated data products
- `scripts` – operational helper scripts for reporting, config creation, archiving, cleanup, and hashing
- `jenkins` – CI/automation pipeline definitions

## Development

A minimal development environment is defined in `environment.yml`.

Typical starting points for contributors are:

- `environment.yml` for dependencies
- `src/processing/process_request.py` for the main processing flow
- `scripts/create_config_file.py` for request/config-related helper logic

## License

This project is licensed under the MIT License. See `LICENSE`.
