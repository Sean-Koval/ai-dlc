# P0: Deliver and qualify the native Windows setup journey

## Problem and goal

Teammates cloning AI-DLC on Windows are routed toward Unix/WSL because the installer, provisioner, runtime paths and generated project steps assume Unix. Deliver a native Windows 11 x64 PowerShell journey from verified installation through selected core/Python preparation, project guidance and a meaningful acceptance check, with truthful unsupported-tool and qualification status. Authority: [product direction](../../../docs/product-direction.md). This packet is proposed implementation scope, not delivery or Windows qualification evidence.

Priority: **P0**. Change ID: `windows-native-setup`. Requirements: **WNS-01–WNS-08**, plus amended **BP-01**. `depends_on: [windows-portable-core]`. Consumer-onboarding guidance consumes this path; installed-client smoke qualification remains separately owned. Archive this change independently after its dependency is delivered. The [task artifact](tasks.md) remains the authoritative implementation checklist.

## Scope and non-goals

Scope: Windows 11 x64/local NTFS/inbox PowerShell 5.1; verified native bootstrap; user-local `.exe`/`Scripts` and activation; core Git/GitHub CLI and pinned Python/uv/mise; generic/Python generated projects; actual Windows CI/candidate/published-consumer replay and clean-account qualification. Preserve source/release identity, Unix behavior, source/template assets, authored content and local credentials.

No mandatory WSL, ARM64/network-share promise, whole-catalog support, new provider integrations, auto-login, shell translation, forced elevation, policy bypass, new orchestrator or implicit release publication. Native Antigravity instruction/skill/MCP recognition is a separate evidence slice; this issue cannot infer it from generated files.

## Acceptance checklist

- [ ] A fresh Windows 11 x64 account uses native PowerShell plan/bootstrap without preinstalled toolchain or POSIX environment, and unsupported hosts/policies get explicit diagnostics (WNS-01).
- [ ] Reviewed exact native prerequisites and release assets are integrity verified; corrupt downloads/manifests/archive paths fail before use, and interrupted/locked/concurrent publication preserves the selected working CLI (WNS-02).
- [ ] `.exe`/`Scripts`, spaces/Unicode, source-checkout provenance, explicit alias selection and owned new-terminal activation work without overwriting authored profile content (WNS-03).
- [ ] Minimal core/Python provisioning is selective, repeatable and non-upgrading; absent package manager/selected unsupported modules block honestly with a native recovery path (WNS-04).
- [ ] Generic team-owned and Python starter checks run natively; deliberate behavioral regression fails; adoption/retry preserve authored commands/tests/locks and managed-file conflicts (WNS-05).
- [ ] Native Windows CI and verified candidate/replay tests cover seed plus generated project with exact artifacts and receipts; Unix tests remain required and replay publishes nothing (WNS-06).
- [ ] A clean Windows 11 walkthrough records real positive/negative/recovery evidence and limits; hosted Windows Server and unobserved desktop recognition are not mislabeled (WNS-07).
- [ ] Canonical consumer/contributor, native setup and release guidance agree with packaged/source assets, with reviewed documentation dispositions and no personal downstream defaults (WNS-08).

## Implementation sequence

1. Tasks 1.1–1.4 confirm portable-core readiness and build/attack-test the verified native bootstrap.
2. Tasks 2.1–2.4 implement native locations, owned activation and selected core/Python recipes with explicit limitations.
3. Tasks 3.1–3.3 complete and test generated generic/Python consumer flows, preserving existing-project ownership.
4. Tasks 4.1–4.5 add CI/release-consumer jobs, run the clean Windows 11 matrix, update canonical guidance and complete ordinary delivery gates. Any release publication is separately authorized.

## Evidence matrix

| Requirement | Current evidence to inspect | Acceptance evidence |
| --- | --- | --- |
| WNS-01 | `scripts/bootstrap.sh:1-33`; `bootstrap/versions.sh:7-32` | Fresh native PowerShell plan/install; no POSIX dependency; wrong-host refusal |
| WNS-02 | `scripts/bootstrap.sh:49-127`; `src/ai_dlc/setup/templates.py:165-190`; canonical BP/RP requirements | Native verified cache/download/install, malicious/corrupt input refusal, interrupted/concurrent/open-handle recovery, exact manifest propagation |
| WNS-03 | `src/ai_dlc/environment/bootstrap.py:20-24,149-164`; source alias code in `scripts/bootstrap.sh` | Real fresh terminal resolution, native paths/provenance, profile/alias conflicts and explicit repointing |
| WNS-04 | `src/ai_dlc/setup/provision.py:85-93,123-160`; `modules/catalog.toml:1-10` | Selective plan/apply/readback, absent winget/policy recovery, selected unsupported module blocks |
| WNS-05 | `project-templates/project/ai-dlc.toml.jinja:38-79`; `project-templates/project/scripts/check_tests.py` | Windows and Unix generic/Python acceptance, behavioral regression, empty/skipped tests, lock/content preservation |
| WNS-06 | `.github/workflows/verify.yml:14-29`; `.github/workflows/release.yml` | Windows native jobs plus candidate/read-only published asset seed/generated consumers with exact identities |
| WNS-07 | No Windows 11/client evidence in reviewed PM input; existing platform qualification tracking #53 | Clean-account Windows 11 recorded matrix; client/native-host missing obligations explicitly open |
| WNS-08 | `README.md:59-81`; `docs/index.md`; `docs/release-verification.md`; packaged bootstrap templates | Updated current canonical owners, package parity and content-bound review dispositions |

## Open inputs and ownership

Maintainer and an affected teammate must supply the qualification host, exact installed client/shell versions, actual selected profile and corporate install restrictions. These unknowns do not block specification or implementation; they prevent unearned live qualification claims. Implementer must review the actual native uv/mise hashes, winget package/version identities and minimum compatible engine release before shipping. No hashes/version promises are fabricated here. Preserve failed observations when recording a later successful retry; measure time/manual steps at baseline without inventing product targets.
