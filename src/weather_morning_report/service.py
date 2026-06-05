"""Application orchestration."""

from weather_morning_report.config import Config
from weather_morning_report.providers.wttr import WttrProvider
from weather_morning_report.recommendations import recommend
from weather_morning_report.rendering.text import render_text


def preview(config: Config) -> str:
    snapshot = WttrProvider(
        location_name=config.location_name,
        location_query=config.location_query,
        timezone=config.timezone,
    ).fetch()
    return render_text(snapshot, recommend(snapshot))

