## Decision
Keep component schema1 unchanged. Trusted ProviderDefinition metadata supplies root-level configuration requirements (path and full-match pattern) and an explicit inactive flag. GitHub SCM uses the existing core executable requirement and scm.repository owner/repo contract; provider-local substitutes do not satisfy it. The none deployment choice is inactive, not an available deployment implementation. Unknown or role-incompatible choices still block.

The shared readiness path interprets metadata without vendor branches. A valid repository and available executable remain local prerequisites, never gh authentication or merged-CI evidence. Inactive choices have no health-qualification probe/claim.

Existing machine enrollment already records a reviewed Git profile/ref and emits the actual machine TOML path; setting paths.vault there feeds project readiness. Documentation provides those exact steps and preserves shared project ownership. No new --machine route or automatic profile selection is introduced.

## Review repair: explicit component compatibility
Readiness checks both the selected trusted component and the configured runtime definition. Applicable requirements accumulate; a component override cannot erase root configuration. A known runtime must support the selected role. An unknown runtime cannot borrow a trusted built-in component, except Registry's explicit executable/Python transports retain the existing extension contract and the borrowed requirements. Digest-verified custom components retain their existing metadata-only behavior without loading providers. A mismatched runtime never receives inactive credit.

Registry owns canonical aliases and extension transport identifiers. Readiness reuses those aliases instead of duplicating a vendor allowlist. The GitHub runtime definition includes its existing SCM and deployment interface; the packaged GitHub component remains SCM-only. This does not introduce new scaffold deployment choices or deployment qualification. Existing knowledge aliases retain the same private vault requirement.
