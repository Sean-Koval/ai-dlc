## Decision
Keep component schema1 unchanged. Trusted ProviderDefinition metadata supplies root-level configuration requirements (path and full-match pattern) and an explicit inactive flag. GitHub SCM uses the existing core executable requirement and scm.repository owner/repo contract; provider-local substitutes do not satisfy it. The none deployment choice is inactive, not an available deployment implementation. Unknown or role-incompatible choices still block.

The shared readiness path interprets metadata without vendor branches. A valid repository and available executable remain local prerequisites, never gh authentication or merged-CI evidence. Inactive choices have no health-qualification probe/claim.

Existing machine enrollment already records a reviewed Git profile/ref and emits the actual machine TOML path; setting paths.vault there feeds project readiness. Documentation provides those exact steps and preserves shared project ownership. No new --machine route or automatic profile selection is introduced.
