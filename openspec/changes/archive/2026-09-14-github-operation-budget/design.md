# GitHub operation timeout design

The registry already constructs the trusted bundled GitHub Issues executable with its child configuration serialized separately. Apply the 120-second fallback only to the parent transport configuration after serializing that child configuration. Existing explicit timeout values remain authoritative in both layers. This avoids changing the shared configuration schema, fingerprints or per-request behavior and leaves every completion/readback check active.

Tests simulate a 35-second compound operation at the subprocess boundary, asserting that it completes under the default, still fails under an explicit 30-second limit, and that child request configuration is unchanged. A separate boundary test proves an operation exceeding the new bound still times out. Existing custom and Jira provider defaults remain 30 seconds.
