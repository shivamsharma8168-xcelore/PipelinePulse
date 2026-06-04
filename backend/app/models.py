from datetime import datetime, timezone
from uuid import uuid4

from .extensions import db


def utc_now():
    return datetime.now(timezone.utc)


class VisitorSession(db.Model):
    __tablename__ = "visitor_sessions"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)
    last_seen_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now)


class Report(db.Model):
    __tablename__ = "reports"

    id = db.Column(db.String(36), primary_key=True, default=lambda: str(uuid4()))
    session_id = db.Column(
        db.String(36),
        db.ForeignKey("visitor_sessions.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    pipeline_name = db.Column(db.String(160), nullable=False)
    repository = db.Column(db.String(200), nullable=True)
    branch = db.Column(db.String(120), nullable=True)
    commit_sha = db.Column(db.String(80), nullable=True)
    provider = db.Column(db.String(40), nullable=False)
    region = db.Column(db.String(80), nullable=False)
    instance_type = db.Column(db.String(120), nullable=False)
    duration_minutes = db.Column(db.Float, nullable=False)
    cpu_utilization = db.Column(db.Float, nullable=False)
    cost_usd = db.Column(db.Float, nullable=False)
    energy_kwh = db.Column(db.Float, nullable=False)
    emissions_gco2e = db.Column(db.Float, nullable=False)
    avg_watts = db.Column(db.Float, nullable=False)
    hourly_price_usd = db.Column(db.Float, nullable=False)
    carbon_intensity_g_per_kwh = db.Column(db.Float, nullable=False)
    details = db.Column(db.JSON, nullable=False)
    created_at = db.Column(db.DateTime(timezone=True), nullable=False, default=utc_now, index=True)

    def to_dict(self):
        return {
            "id": str(self.id),
            "session_id": str(self.session_id),
            "pipeline_name": self.pipeline_name,
            "repository": self.repository,
            "branch": self.branch,
            "commit_sha": self.commit_sha,
            "provider": self.provider,
            "region": self.region,
            "instance_type": self.instance_type,
            "duration_minutes": self.duration_minutes,
            "cpu_utilization": self.cpu_utilization,
            "cost_usd": self.cost_usd,
            "energy_kwh": self.energy_kwh,
            "emissions_gco2e": self.emissions_gco2e,
            "avg_watts": self.avg_watts,
            "hourly_price_usd": self.hourly_price_usd,
            "carbon_intensity_g_per_kwh": self.carbon_intensity_g_per_kwh,
            "details": self.details,
            "created_at": self.created_at.isoformat(),
        }
