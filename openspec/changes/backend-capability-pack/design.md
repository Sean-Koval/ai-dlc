# Backend capability design

Keep existing provider capabilities as defaults and add backend as an optional capability sharing the existing repeated CLI flag and Copier answers. It creates no provider role. Checks validate OpenAPI using openapi-spec-validator==0.7.2 for Python/generic/Rust and @redocly/cli@1.34.16 for Node. Setup warms these exact tool environments; checks request offline/no-install execution. Generic/Rust backend presets add pinned Python/uv runtimes. Existing project dependencies are never silently edited during adoption.

The Python-only drift script discovers src/<pkg>/app.py, skips absent apps and non-FastAPI modules, imports one FastAPI app through its project environment, and compares normalized app.openapi() against committed YAML with a unified JSON diff. Multiple candidate apps, broken imports and malformed contracts fail explicitly. No generated contract is overwritten.

The catalog explicitly lists docs/api/openapi.yaml and maps implementation source and the drift script. Skill guidance requires the contract and an artifacts.contract reference in the same reviewed work delivery. Scaffold tests cover all presets; a bounded real validator smoke check proves valid output, corrupt YAML refusal and offline reuse after setup.
