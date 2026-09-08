# Release candidate preparation evidence

The remaining-issue audit found that the manual release workflow produced a wheel
and constraints but not the manifest consumed by release-mode bootstrap. The
candidate generator now validates engine filename and embedded name/version,
requires one wheel and nonempty constraints, validates an explicit HTTPS base URL,
and exclusively creates a manifest using actual artifact SHA256 values. The manual
workflow invokes it after the existing real constrained wheel-installation check.
No release URL is asserted to exist and no asset is published by generation.

The first nine generator cases failed before the script existed. The implementation
then passed all nine, including shell consumption, version/name/ambiguity refusal,
missing constraints, existing-output preservation and invalid URLs. Independent
review found separate metadata validation and pathname hashing could authenticate
a replacement wheel under the old identity. A new scheduling regression replaced
the actual pathname immediately after ZIP validation and failed before the repair.
The generator now validates and hashes one captured byte sequence; replacement can
only cause a later download hash mismatch, not pin a wrong validated identity.

The existing release-mode shell bootstrap also received three characterization
cases: successful engine selection/project setup, corrupted wheel refusal, and
corrupted constraints refusal. Both corruption cases preserve the selected CLI and
refuse before engine installation. These tests run the actual shell script with
controlled uv/package transport fixtures; they do not establish live hosting or
installation of a real release wheel. No bootstrap behavior change was needed.

The combined generator/bootstrap set passed **28 tests in8.02seconds**. Scoped
format/lint passed, and all23 strict OpenSpec validations passed. Required integrated
checks, final review and actual candidate artifact observations are recorded by the
coordinator separately; these scoped results do not claim a published release.

## Actual candidate observation

Clean integrated `3d78ddb6e952be66f76c28bd72c943a777a84c8b` passed all five
required checks in the reused Ubuntu24.04.3 ARM64 container with networking
disconnected: **1,899 passed,9 skipped in110.37seconds**. The expanded conformance
package passed independent review and22 focused checks, including actual copied
package subprocess execution. No new provider-test image was built; qualification
of that expanded image remains separate.

The same revision built a real wheel offline and exported locked hashed
constraints, then generated a candidate manifest using the explicit reserved
`https://example.test/unpublished/3d78ddb` URL. This URL is test input, not a
published destination. Wheel SHA256:
`584fec8f323b104db664bc5460cdd91e54b0ddbde26f85589b0f2059b64082e1`.
Constraints SHA256:
`2c827c82bfa1bd6132189ac5b0eb877c25a6d209af2adde0e8141b1f92c57dcd`.

The first isolated dependency installation stopped offline because annotated-doc
was absent from the cache. A separately recorded attempt temporarily attached the
container network, installed dependencies with required hashes, installed the
actual wheel without dependencies, ran CLI help and scaffolded623 files with no
skips. The container was disconnected afterward and inspection returned no attached
networks. Both attempts remain in local evidence. This verifies candidate wheel
installation/scaffolding on a reused environment; it is not a release download,
factory-clean setup, hosted-client session or publication claim.
