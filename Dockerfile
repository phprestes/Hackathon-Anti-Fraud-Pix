FROM python:3.11-slim AS base

# Never run as root.
RUN adduser --system --no-create-home user

ENV VIRTUAL_ENV=/opt/venv
RUN python3 -m venv "$VIRTUAL_ENV"
ENV PATH="$VIRTUAL_ENV/bin:$PATH"

# requirements first: the dependency layer stays cached while they do not change.
COPY requirements.txt /requirements.txt
RUN pip install --upgrade pip && pip install -r /requirements.txt

WORKDIR /app
COPY src /app

FROM base AS api
RUN chown -R user /app
USER user

# --no-server-header: do not advertise the uvicorn version.
CMD uvicorn app:app --host 0.0.0.0 --port 3000 --no-server-header


# Cold path: the api image plus numpy, kept out of the hot path.
FROM base AS worker
COPY requirements-worker.txt /requirements-worker.txt
RUN pip install -r /requirements-worker.txt
RUN chown -R user /app
USER user

CMD ["python", "-m", "worker"]
