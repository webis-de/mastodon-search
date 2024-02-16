FROM python:3.11

WORKDIR /workspace/
ADD pyproject.toml pyproject.toml

ARG PSEUDO_VERSION=1
RUN \
    --mount=type=cache,target=/root/.cache/pip \
    SETUPTOOLS_SCM_PRETEND_VERSION=${PSEUDO_VERSION} \
    pip install -e .

RUN \
    --mount=source=.git,target=.git,type=bind \
    --mount=type=cache,target=/root/.cache/pip \
    pip install -e .

ADD . .

ENTRYPOINT ["python", "-m", "mastodon_search"]
