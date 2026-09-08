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
