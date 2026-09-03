# Required: a reviewed uv + Python >=3.12 Linux image with Git, pinned by digest.
# Run the README preflight before Docker resolves FROM. No floating default exists.
ARG BASE_IMAGE
FROM ${BASE_IMAGE}
ARG BASE_IMAGE
RUN python -c 'import os,re,sys; assert re.fullmatch(r"[^\s]+@sha256:[0-9a-f]{64}", os.environ.get("BASE_IMAGE", "")), "BASE_IMAGE must be digest-pinned"; assert sys.version_info >= (3,12), "Python >=3.12 required"'
RUN uv --version
RUN git --version
WORKDIR /kit
ENV UV_PROJECT_ENVIRONMENT=/opt/ai-dlc-venv \
    UV_PYTHON_DOWNLOADS=never \
    UV_LINK_MODE=copy \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTEST_DISABLE_PLUGIN_AUTOLOAD=1 \
    PATH=/opt/ai-dlc-venv/bin:$PATH \
    TMPDIR=/work \
    HOME=/work
COPY pyproject.toml uv.lock README.md /kit/
COPY src /kit/src
COPY tests/test_providers.py tests/test_workflow.py /kit/tests/
COPY templates /kit/templates
COPY profiles /kit/profiles
COPY modules /kit/modules
COPY agents /kit/agents
COPY project-templates /kit/project-templates
COPY contracts /kit/contracts
COPY targets /kit/targets
COPY playbook /kit/playbook
COPY bootstrap /kit/bootstrap
RUN uv sync --locked --no-editable --group dev
RUN ai-dlc-conformance --list
RUN mkdir /work && chmod 1777 /work && chmod -R a+rX /kit /opt/ai-dlc-venv
USER 65534:65534
# No entrypoint: sandbox.py supplies ai-dlc-conformance <target> explicitly.
CMD ["ai-dlc-conformance", "all"]
