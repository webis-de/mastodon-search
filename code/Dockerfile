FROM python:3.12-alpine3.18

WORKDIR /workspace/

COPY pyproject.toml ./
RUN pip --no-cache-dir install .

COPY fediverse_analysis fediverse_analysis/

ENTRYPOINT ["python3.12", "-m", "fediverse_analysis"]
