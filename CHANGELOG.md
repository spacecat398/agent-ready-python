# Changelog

All notable changes to this project are documented here in a concise
[Keep a Changelog](https://keepachangelog.com/en/1.1.0/) format.

## [0.1.0] - Release candidate (not published)

### Added

- Foundation services for configuration, errors, logging, secrets, and lifecycle management.
- Selectable modules for text generation, documents, retrieval, embeddings, artifacts, and
  pipelines.
- Explicit project generation with composition roots, Adapter selection, and static module
  descriptors.
- Offline `fake` and local Adapters, with remote Providers requiring explicit selection and
  configuration.
- Static `minimal`, `text-cli`, `rag-local`, and `artifact-pipeline` presets, plus the legacy
  `retrieval` preset.
- Offline safety checks that avoid Provider calls, API-key requirements, and `.env` creation or
  overwrite during assembly and tests.
- Distribution acceptance for wheel and sdist generation, isolated wheel installation, and
  post-install project generation.
- MIT licensing and confirmed author and repository metadata for distribution.
