# CCHS Tool Privacy and Security Overview

## Purpose and deployment model

The CCHS Bootstrap Analysis Tool is designed for public health analysts and
epidemiologists using a bring-your-own-data (BYOD) model. Each organization runs
the application locally with CCHS extracts it is authorized to use.

The project does not provide a hosted service or container deployment. It does
not include authentication, multi-user access controls, or an internet-facing
production configuration.

## Local-only defaults

The committed `.streamlit/config.toml`:

- binds the Streamlit server to `127.0.0.1`
- disables Streamlit usage-statistics collection
- runs headlessly on port `8501`

Routine analysis reads local files and performs filtering, harmonization,
bootstrap calculations, visualization, and export generation on the local
machine. Dependency installation requires network access unless packages are
provided through an organizational mirror or offline cache.

## Local data locations

The application can read or create sensitive or restricted files in:

- `data/` for source parquet files and bootstrap weights
- `data/precomputed/` for local harmonized parquet files and JSON metadata
- the user's chosen download location for CSV or Excel exports
- local Streamlit and Python caches

These paths are excluded from Git. Git ignore rules do not replace endpoint
security, access controls, encryption, retention, backup, or secure-deletion
requirements.

## Precomputed data

Precomputed files are additional local copies of transformed respondent-level
data. They must receive the same protection as the source CCHS files. Metadata
uses JSON rather than executable pickle serialization.

## Session and exports

Interactive analysis state is held in the active Streamlit process. CSV and
Excel exports are assembled in memory and delivered through the local browser.
Users control where downloaded files are saved and must protect those outputs
according to organizational policy.

## Operational safeguards

- Run the application only on an approved workstation or controlled analytical
  environment.
- Keep `server.address = "127.0.0.1"` unless an approved secured deployment adds
  authentication, TLS, authorization, and network controls.
- Never commit CCHS data, bootstrap weights, precomputed outputs, or codebooks.
- Do not load data or metadata obtained from an untrusted source.
- Apply operating-system updates and review dependency security alerts.
- Remove local source, precomputed, cache, and export files according to the
  organization's retention schedule.

## Scope limitation

This document describes application behavior, not a complete privacy or threat
assessment. Each deploying organization is responsible for its own legal,
privacy, security, and CCHS agreement review.
