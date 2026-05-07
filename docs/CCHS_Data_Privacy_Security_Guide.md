# CCHS Tool Privacy and Security Overview

## Purpose

This document describes the current privacy and security posture of the CCHS Bootstrap Analysis Tool for pilot use by public health units and other approved organizations. It is written for a bring-your-own-data (BYOD) deployment model where each organization runs the tool locally, using its own CCHS extracts and infrastructure, without requiring internet connectivity during routine use.

This guide reflects the current implemented behavior of the application as of 2026-05-07.

## Executive Summary

The CCHS tool is designed as a local-first analytical application:

- It reads survey and bootstrap datasets from local files in the `data/` directory.
- It performs filtering, harmonization, and bootstrap analysis entirely on the local machine or local container.
- It does not contain application-level code that sends survey data to external APIs, cloud services, databases, or analytics platforms during normal runtime.
- Streamlit usage telemetry is explicitly disabled in both the application configuration and the Docker runtime environment.
- Results exports are generated in memory and downloaded directly to the local user session.

In practical terms, this supports a privacy-preserving BYOD model in which participating public health units can keep identifiable or sensitive survey microdata entirely within their own controlled environment.

At the same time, the tool should be understood as a local analytics application rather than a complete security platform. It does not currently provide built-in authentication, role-based access control, encryption at rest, audit logging, or automated disclosure controls beyond analytical quality flags. Those controls must be provided by the host environment and local operating procedures.

## Intended Deployment Model

The recommended deployment model for pilot partners is:

- Run the app locally on an analyst workstation or on an internally managed server.
- Store source CCHS files only on local encrypted storage or a local encrypted volume.
- Restrict access using device controls, operating system accounts, VPN, internal network segmentation, or equivalent local controls.
- Do not expose the Streamlit port to the public internet.
- Use the current modular application entrypoint for privacy-sensitive deployments.

Supported local deployment patterns:

- Analyst laptop or desktop
- Internal virtual machine
- Internal Docker host
- Air-gapped or network-restricted environment

## Data Classification Assumptions

The application is designed to process survey microdata and derived analytical outputs that may be:

- confidential
- sensitive
- subject to data sharing agreements
- subject to internal public health information governance requirements

This guide assumes that each participating organization remains the data custodian for the files it loads into the tool.

## What Data the Tool Uses

The codebase expects the following local inputs:

- Main survey data files such as `data/hs2024_on_distr.parquet`
- Bootstrap weight files such as `data/hs2024_on_bootwt.parquet`
- Variable description files such as `data/CCHS_2024_Recoded_Variables.csv`
- Local harmonization metadata under `harmonization/`

The tool reads these files locally using standard parquet, JSON, and CSV loading routines within the application.

## Privacy-by-Design Characteristics

### 1. Local file-based data access

The application reads data from local paths under `data/` and `harmonization/`. No application code requires a remote database, cloud bucket, SaaS platform, or remote inference service.

In practice:

- the application reads survey and bootstrap files from the local data directory
- harmonization files are read from local JSON resources bundled with the application
- precomputed harmonized datasets are stored and read from a local precomputed-data directory

### 2. No application-level outbound data transfer during normal use

The runtime application code does not implement outbound requests for:

- cloud storage
- remote databases
- external APIs
- analytics/telemetry SDKs
- LLM or AI services

Review of the current application implementation did not identify runtime integrations that would routinely transmit survey data to external services.

Important distinction:

- dependency installation still requires package download at build or setup time unless the environment is pre-provisioned
- Docker image creation also requires network access during image build unless dependencies are mirrored internally

These setup-time requirements are separate from routine analytical use. Once the environment is provisioned, the application can be run locally without internet access.

### 3. Telemetry disabled

Streamlit usage telemetry is disabled in two places:

- usage statistics collection is disabled in the application configuration
- usage statistics collection is also disabled in the container runtime configuration

This reduces the risk of usage metadata leaving the local environment through framework defaults.

### 4. In-memory export generation

CSV and Excel exports are created in memory using `BytesIO` before being returned to the user through Streamlit download controls.

In practice:

- export files are created in memory first
- downloads are provided directly to the active local user session

This means the application does not need to write exports to a shared server-side directory as part of normal export behavior. Final file persistence occurs where the local user chooses to save the download.

### 5. Session-scoped analysis state

Interactive analysis state is stored in Streamlit session state, including:

- filtered data
- merged data
- selected variables
- combined results

In practice:

- active analysis state is retained within the running user session

This helps keep active analysis state within the running session rather than automatically publishing results elsewhere.

## Security Considerations

### Runtime architecture

The supported privacy-first runtime configuration uses the current modular application. It:

- loads local data
- applies geographic and inclusion filters
- merges bootstrap weights locally
- runs bootstrap calculations locally
- renders results in the local Streamlit session

The Docker container exposes port `8501` and binds Streamlit to `0.0.0.0` inside the container. This is normal for containerized operation, but security depends on how the host publishes that port.

Implication:

- safe on `localhost` or internal-only bindings
- not appropriate to publish openly to the internet without compensating controls

### Caching and local persistence

The application uses local caching extensively in loader and preprocessing functions. This improves performance, but cached artifacts may persist locally on the host where Streamlit stores its cache.

Operational implication:

- source data or derived subsets may remain in local cache beyond a single click or screen refresh

The user interface includes cache-clearing actions in some workflows, but there is no comprehensive secure-delete workflow in the application.

### Precomputed data storage

For multi-cycle performance, the tool can create precomputed local files in `data/precomputed`, including:

- harmonized parquet datasets
- harmonized bootstrap parquet datasets
- metadata files

In practice:

- the application can create local precomputed harmonized files for faster multi-cycle analysis

This is a local performance optimization. It does not send data externally, but it does create additional local copies of transformed data that must be governed as sensitive analytical artifacts.

### Serialization format note

Metadata for precomputed cycles is serialized using Python pickle format.

Security implication:

- the pickle format is acceptable for trusted local workflows
- the pickle format should not be treated as safe for untrusted file exchange
- pilot sites should only load precomputed metadata that they generated themselves or obtained from a trusted internal source

This is an important trust boundary and should be documented clearly for pilot participants.

## Controls Not Currently Built Into the Application

The current codebase does not provide built-in:

- user authentication
- role-based access control
- per-user authorization
- audit logging of user actions
- encryption at rest
- key management
- automated retention enforcement
- secure wipe or purge workflow
- automatic small-cell suppression or privacy threshold suppression for exports
- server-side approval workflow before export

This does not make the tool unsuitable for pilot use. It means those controls must be implemented through the local hosting environment, organizational procedures, or both.

## Residual Privacy and Security Risks

### 1. Host/device compromise risk

If the workstation, VM, or server is compromised, local survey data and outputs may be exposed. The application relies on host security controls rather than embedding endpoint protection itself.

### 2. Multi-user exposure risk if shared insecurely

If a Streamlit instance is exposed on a shared network without authentication or network restrictions, unauthorized users may be able to access loaded data or outputs.

### 3. Local artifact sprawl

Sensitive data may exist in more than one place locally:

- original parquet files
- precomputed parquet files
- Streamlit cache
- downloaded CSV or Excel outputs
- container volumes or host-mounted directories

### 4. Disclosure through exports

Users can export analysis results as CSV or Excel. If local governance rules require suppression, rounding, or disclosure review before release, those checks must happen outside the current application unless the organization adds additional controls.

### 5. Trusted-file assumption for precomputed metadata

Because pickle is used for metadata, only trusted locally generated metadata files should be loaded.

## BYOD Pilot Security Position

For pilot partners proposing a bring-your-own-data model, the strongest defensible statement is:

> The CCHS tool can be deployed in a local-only configuration where each public health unit retains custody of its own survey microdata, runs the application entirely within its own environment, and does not need to transmit analytical data to a central service or internet-based platform during routine use.

That statement is supported by the current architecture, subject to the following conditions:

- the organization uses the local modular runtime
- the deployment does not intentionally expose the app beyond the organization’s trusted environment
- the host device or server is appropriately secured
- local files, caches, volumes, and exported outputs are governed as sensitive data

## Recommended Minimum Controls for Pilot Sites

Each participating organization should implement the following minimum controls.

### Device and host controls

- Full-disk encryption on analyst laptops and desktops
- Managed endpoint protection
- Current OS security patching
- Screen lock and session timeout
- Strong local account passwords or enterprise identity controls

### Storage controls

- Store `data/` and `data/precomputed/` only on encrypted local or encrypted network-backed storage approved for sensitive data
- Restrict file system permissions to authorized analysts
- Avoid syncing raw datasets to consumer cloud drives

### Network controls

- Run on `localhost` where possible
- If hosted on an internal server, restrict access with firewall rules, reverse proxy authentication, VPN, or internal network segmentation
- Do not publish the Streamlit port directly to the public internet

### Operational controls

- Define who may load source data
- Define who may run exports
- Define disclosure review expectations for small cells and unstable estimates
- Clear caches and remove temporary/precomputed artifacts when the analysis period ends
- Maintain local backup and restoration procedures appropriate to the organization’s data classification rules

### Governance controls

- Execute a local privacy review before production use
- Document the lawful authority and data sharing basis for each site
- Keep a site-level record of approved datasets, users, and retention periods

## Recommended Deployment Patterns

### Option 1. Single analyst workstation

Best for:

- early pilot work
- one or a few trained analysts
- highly restricted datasets

Controls:

- local-only execution
- encrypted disk
- no inbound firewall exceptions

### Option 2. Internal shared server

Best for:

- a small analyst team
- centrally managed infrastructure

Controls:

- reverse proxy with authentication
- internal-only network access
- restricted host volumes
- server hardening and logging managed by the host organization

### Option 3. Local Docker deployment

Best for:

- reproducible installation
- internal IT-managed deployment

Controls:

- bind only the required local port
- mount local data volumes with least privilege
- keep container host internal
- treat mounted volumes as sensitive data stores

## Offline / No-Internet Operation

Routine analysis can be performed without internet access once the runtime environment is already provisioned.

To support a fully offline operating mode, pilot sites should:

- preinstall Python and dependencies or use an internally approved container image
- preload required CCHS data files locally
- avoid legacy entrypoints or local customizations that reference remote assets
- test startup and analysis on a disconnected network segment before pilot launch

## Suggested Language for Privacy Reviews or Partner Briefings

Use the following wording if helpful:

> The CCHS Bootstrap Analysis Tool supports a decentralized BYOD deployment model. Participating public health units can run the application entirely within their own environment using locally stored CCHS files. The tool does not require a central database, cloud analytics service, or internet connectivity for routine analytical use once installed. Analytical processing, harmonization, filtering, and exports occur locally. Each pilot site retains custody and control of its own data and is responsible for applying its own workstation, server, network, and governance safeguards.

## Summary Assessment

In summary:

- the tool is privacy-preserving by architecture because data remains local by default
- the main security considerations relate to local environment governance rather than hidden cloud integrations
- the application is appropriate for pilot use where organizations want to keep data entirely in-house
- additional enterprise controls can be layered around the application if the pilot expands

## Recommended Future Enhancements

If the pilot moves toward broader production deployment, the next security improvements to consider are:

- optional authentication in front of Streamlit
- export suppression rules for small cells and disclosure control
- replacement of pickle metadata with JSON
- explicit cache management and purge controls
- deployment hardening guidance for reverse proxies and internal TLS
- structured audit logging for administrative actions

## Conclusion

The current CCHS tool supports a credible BYOD, local-only, privacy-preserving deployment model for pilot use by public health units. It processes locally stored survey data without requiring routine outbound internet access and without application-level integrations that transmit analytical data externally. Its primary privacy strength is architectural data locality. Its primary limitation is that environmental and administrative safeguards remain the responsibility of the hosting organization.
