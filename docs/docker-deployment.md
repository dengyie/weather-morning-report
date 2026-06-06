# Docker Deployment

Docker Compose provides a persistent runtime volume for delivery settings and
weather snapshots. The container runs as a non-root user.

## Prepare

```bash
git clone https://github.com/dengyie/weather-morning-report.git
cd weather-morning-report
cp .env.example .env
docker compose build
```

Edit `.env` and provide the location and SMTP delivery settings. Keep `.env`
private; it is excluded from Git and the Docker build context. When delivery
settings will be saved through the browser page instead, remove the blank
delivery variables from `.env` because environment variables take priority
over stored settings.

## Validate and Send

```bash
docker compose run --rm report preview
docker compose run --rm report validate-config
docker compose run --rm report send
```

The `weather-report-data` volume persists the latest valid weather snapshot and
settings between one-shot container runs.

## Configure Through the Settings UI

```bash
docker compose up settings
```

Open <http://127.0.0.1:8766>. The container listens on all container
interfaces, but Compose publishes the page only on the host loopback address.
Stop it with `Ctrl+C`.

Settings saved through the page are stored in the same persistent Docker
volume used by the report service. Environment variables from `.env` override
stored settings.

## Schedule Daily Delivery

Use the host scheduler to run the one-shot container. For example, add this
cron entry on a host configured for the `Asia/Shanghai` timezone:

```cron
30 8 * * * cd /opt/weather-morning-report && /usr/bin/docker compose run --rm report send >> /var/log/weather-morning-report.log 2>&1
```

Alternatively, use a systemd timer to invoke the same `docker compose run`
command. Confirm the host scheduler timezone before enabling automated sends.

## Update

```bash
git pull --ff-only
docker compose build --pull
docker compose run --rm report preview
```

The named volume remains intact when images and containers are replaced.
