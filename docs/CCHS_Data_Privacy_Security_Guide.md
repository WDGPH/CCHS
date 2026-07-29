# CCHS Tool Privacy and Security Overview

## Purpose

This document describes the current privacy and security posture of the CCHS Bootstrap Analysis Tool for pilot use by public health units and other approved organizations. It is written for a bring-your-own-data (BYOD) deployment model where each organization runs the tool locally, using its own CCHS extracts and infrastructure, without requiring internet connectivity during routine use.

This guide reflects the current implemented behavior of the application as of 2026-05-07.

## Executive Summary

The CCHS tool is designed as a local-first analytical application:

- It reads survey and bootstrap datasets from local files in the `data/` directory.
- It performs filtering, harmonization, and bootstrap analysis entirely on the local machine or local container.
- Streamlit usage telemetry is explicitly disabled in both the application configuration and the Docker runtime environment.
- Results exports are generated in memory and downloaded directly to the local user session.

## What Data the Tool Uses

The codebase expects the following local inputs:

- Main survey data files such as `data/hs2024_on_distr.parquet`
- Bootstrap weight files such as `data/hs2024_on_bootwt.parquet`
- Variable description files such as `data/CCHS_2024_Recoded_Variables.csv`
- Local harmonization metadata under `harmonization/`

The tool reads these files locally using standard parquet, JSON, and CSV loading routines within the application.

## Privacy-by-Design Characteristics

### 1. Local file-based data access

The application reads data from local paths under `data/` and `harmonization/`.

In practice:

- the application reads survey and bootstrap files from the local data directory
- harmonization files are read from local JSON resources bundled with the application
- precomputed harmonized datasets are stored and read from a local precomputed-data directory

### 2. No application-level outbound data transfer during normal use

Important distinction:

- dependency installation still requires package download at build or setup time unless the environment is pre-provisioned
- Docker image creation also requires network access during image build unless dependencies are mirrored internally

These setup-time requirements are separate from routine analytical use.

### 3. Telemetry disabled

Streamlit usage telemetry is disabled in two places:

- usage statistics collection is disabled in the application configuration
- usage statistics collection is also disabled in the container runtime configuration

### 4. In-memory export generation

CSV and Excel exports are created in memory using `BytesIO` before being returned to the user through Streamlit download controls.

In practice:

- export files are created in memory first
- downloads are provided directly to the active local user session

The application does not write exports to a server-side shared directory as part of normal export behavior. Final file persistence occurs where the local user chooses to save the download.

### 5. Session-scoped analysis state

Interactive analysis state is stored in Streamlit session state, including:

- filtered data
- merged data
- selected variables
- combined results

In practice:

- active analysis state is retained within the running user session

## Security-Relevant Behavior

### Runtime architecture

The current modular application:

- loads local data
- applies geographic and inclusion filters
- merges bootstrap weights locally
- runs bootstrap calculations locally
- renders results in the local Streamlit session

The Docker container exposes port `8501` and binds Streamlit to `0.0.0.0` inside the container.

### Caching and local persistence

The application uses local caching extensively in loader and preprocessing functions.

### Precomputed data storage

For multi-cycle performance, the tool can create precomputed local files in `data/precomputed`, including:

- harmonized parquet datasets
- harmonized bootstrap parquet datasets
- metadata files

In practice:

- the application can create local precomputed harmonized files for faster multi-cycle analysis

This is a local performance optimization and creates additional local copies of transformed data.

### Serialization format note

Metadata for precomputed cycles is serialized using Python pickle format.

Pickle is used for metadata serialization.

## Data Persistence and Output Behavior

The application can create or retain data in multiple local locations, including:

- source parquet files in the local data directory
- precomputed parquet files in `data/precomputed`
- local cache artifacts created by the application runtime
- downloaded CSV outputs
- downloaded Excel outputs
- container-mounted local volumes when run in Docker

## Summary

Based on the current codebase, the application processes locally stored survey data, performs analysis locally, disables Streamlit usage telemetry, uses local caching, supports local precomputed data files, and generates CSV and Excel outputs for local download.
