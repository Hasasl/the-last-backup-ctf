# Northstar UI update — 10 October 2026

The local project now uses a custom Northstar CTFd theme and a matching design across the OSINT archive, evidence portal and final verifier.

## Changes

- Dark charcoal surfaces, warm white typography, lime accents and a shared Northstar identity.
- A story-led landing page with a visual evidence map, six-stage overview and a clear start/continue action.
- Redesigned sign-in and registration pages, challenge cards, challenge dialogs, tables and navigation.
- Matching archive and investigation pages with a visible return-to-challenges link.
- Clear validation feedback; transaction, audit and verification inputs are retained after incorrect submissions.
- Mobile layouts, visible keyboard focus, readable status labels and reduced-motion support.
- The startup script initializes a new event only when appropriate, preserves existing event progress and activates the saved Northstar theme.

## Verified after the redesign

- 21 automated tests passed (`test-results/pytest-ui.xml`).
- 65 live CTFd checks passed (`test-results/ui-ctfd-live.json`), including registration, prerequisite enforcement, flags, duplicate solves, hints and cumulative scoring.
- 31 live HTTP/evidence checks passed (`test-results/ui-live-http.json`).
- Desktop visual checks completed for the homepage, login, challenge dialog, archive, portal and verifier.
- Six narrow-screen layouts inspected: home, login, registration, archive, portal and verifier. At a 375 CSS-pixel content width, none overflowed the document horizontally (`test-results/ui-responsive.json`).
- A deliberate incorrect portal submission displayed its error and preserved both entered values in the browser.
- The six key released evidence assets match the original hashes (`test-results/ui-evidence-integrity.json`).

All screenshots are in `design-preview/`. The CTFd administrator workspace retains its standard administrative interface; the redesigned theme covers the player-facing site.

This supplements the earlier full deployment test report. The earlier browser-verification limitation has been resolved for these redesigned screens; the four-VM, HTTPS and independent blind-solve limitations still apply.

Open http://localhost:8001 to use the redesign. If an already-open page has cached the old styling, refresh it with Ctrl+F5.
