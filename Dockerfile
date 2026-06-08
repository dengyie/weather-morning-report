FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN useradd --create-home --uid 10001 weather-report

COPY pyproject.toml README.md LICENSE ./
COPY src ./src

RUN python -m pip install --no-cache-dir . \
    && mkdir -p /data \
    && chown -R weather-report:weather-report /data

USER weather-report

ENTRYPOINT ["weather-report"]
CMD ["serve-ui"]
