# Design

A nonempty workflow_dispatch verify_published_tag selects read-only consumer replay; artifact_base_url remains required for candidate compatibility and is ignored in replay mode. Package is skipped for replay; publish requires a push event and tag ref, so manual dispatch at a tag cannot publish. Consumer conditions survive skipped dependencies through !cancelled(), while normal tag consumers still require package and publish success.

Pass the selected tag through RELEASE_TAG and quote it in gh arguments. Consumers initialize the seed locally, generate a demo, compare the retained manifest, and run the demo release-mode bootstrap locally before explicit github-actions checks. The demo initializes and commits its own Git repository after setup so receipts identify the standalone fixture rather than a parent checkout. GITHUB_PATH publication is independent of the selected setup target. No change to the production stale-generated rejection.

Retain failed original publication-run links and digests. A later replay proves only its tested assets, workflow revision and runners. Clean-machine/container/cloud-client, provider and human-evaluation qualifications remain explicit.
