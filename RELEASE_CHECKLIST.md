# Release Checklist

This checklist describes the engineering state and remaining publication steps for release
`0.1.0`. It does not claim that the package has been published to PyPI.

## Verified technical items

- [x] Root `uv` environment passes Ruff and pytest without a remote Provider.
- [x] `uv build` produces a wheel and sdist from the project metadata.
- [x] The sdist includes the package catalog, `CHANGELOG.md`, and `RELEASE_CHECKLIST.md`.
- [x] A wheel installs into an isolated virtual environment without the source checkout on its
      import path.
- [x] The installed `create-ai-app --list-presets` command reads the packaged preset catalog.
- [x] Installed-wheel generation creates `minimal` and `rag-local` in a temporary directory.
- [x] Generated `minimal` and `rag-local` projects pass pytest using offline smoke tests.
- [x] CI does not upload artifacts, require repository secrets, or call a remote Provider.
- [x] Assembly does not create or overwrite `.env`; API keys must not be written to configuration.

## Maintainer decisions and remaining publication checks

- [x] Confirm the MIT License and include it in the repository and source distribution.
- [x] Confirm `spacecat398` as the author identity in the package metadata.
- [x] Confirm the GitHub repository and README documentation URLs.
- [ ] Check that the PyPI project name `agent-ready-python` is available and resolve any naming
      conflict before publishing.
- [x] Confirm final version `0.1.0`, publish the release notes, and create matching tag `v0.1.0`.
- [ ] Confirm the publication credentials and trusted-publishing configuration, including the
      repository, environment, permissions, and PyPI project ownership.
- [ ] Review the final wheel and sdist contents from a clean checkout before upload.
- [ ] Confirm that no API key or other provider credential is present in configuration, workflow
      files, source distributions, wheels, or committed documentation.
