# vim: shiftwidth=4 tabstop=4 noexpandtab

FROM python:3.12

WORKDIR /workspace/

COPY pyproject.toml ./

RUN \
	--mount=type=cache,target=/root/.cache/pip \
	pip install -e .

COPY fediverse_analysis fediverse_analysis/

ENTRYPOINT ["python3.12", "-m", "fediverse_analysis"]
