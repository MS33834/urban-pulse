# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- **Performance**: gzip / Brotli response compression middleware and SQLite PRAGMA tuning.
- **Security**: enhanced security headers (HSTS preload, CSP report-only), dependency vulnerability audit script.
- **Observability**: structured JSON logging, request tracing (`X-Request-ID`), and request metrics middleware.
- **Testing**: API contract tests against OpenAPI schema and Playwright E2E browser tests infrastructure.
- **CI/CD**: GitHub Actions workflow with lint, typecheck, multi-Python test, contract, E2E, security audit, and Pages deploy; GitCode CI pipeline with lint, test, security, and Pages deploy.
- **OpenAPI**: request/response examples for major endpoints and `scripts/export_openapi.py` to generate `openapi.json` / `openapi.yaml`.

## [1.0.0] - 2026-06-26

### Added

- Initial release of Urban Pulse city economic intelligence platform.
- REST API built with FastAPI covering cities, analysis, forecast, health index, and competitiveness index.
- Zero-build frontend dashboard.
- Docker support and static site builder for GitHub / GitCode Pages.
