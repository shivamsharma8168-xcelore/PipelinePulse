from datetime import datetime
from uuid import uuid4

from flask import Blueprint, jsonify, request, session

from .catalog import public_options
from .emissions import EmissionsLookupError, estimate_impact
from .extensions import db
from .models import Report, VisitorSession, utc_now
from .pricing import PricingLookupError, get_hourly_price

api = Blueprint("api", __name__, url_prefix="/api")


@api.before_request
def ensure_visitor_session():
    session_id = session.get("pipelinepulse_session_id")
    visitor_session = VisitorSession.query.get(session_id) if session_id else None
    if not visitor_session:
        visitor_session = VisitorSession(id=str(uuid4()))
        db.session.add(visitor_session)
        session["pipelinepulse_session_id"] = visitor_session.id
    visitor_session.last_seen_at = utc_now()
    db.session.commit()


@api.get("/health")
def health():
    return jsonify({"status": "ok", "timestamp": datetime.utcnow().isoformat() + "Z"})


@api.get("/options")
def options():
    return jsonify(public_options())


@api.get("/reports")
def reports():
    session_id = session["pipelinepulse_session_id"]
    rows = (
        Report.query.filter_by(session_id=session_id)
        .order_by(Report.created_at.desc())
        .limit(25)
        .all()
    )
    return jsonify({"reports": [row.to_dict() for row in rows]})


@api.post("/reports")
def create_report():
    payload = request.get_json(silent=True) or {}
    try:
        clean = _validate_report_payload(payload)
        pricing = get_hourly_price(
            clean["provider"],
            clean["region"],
            clean["instance_type"],
            clean["pricing_mode"],
        )
        impact = estimate_impact(
            clean["provider"],
            clean["region"],
            clean["instance_type"],
            clean["duration_minutes"],
            clean["cpu_utilization"],
        )
    except (ValueError, PricingLookupError, EmissionsLookupError) as exc:
        return jsonify({"error": str(exc)}), 400

    duration_hours = clean["duration_minutes"] / 60
    cost_usd = pricing["hourly_price_usd"] * duration_hours
    projections = _build_projections(clean, cost_usd, impact)

    report = Report(
        session_id=session["pipelinepulse_session_id"],
        pipeline_name=clean["pipeline_name"],
        repository=clean.get("repository"),
        branch=clean.get("branch"),
        commit_sha=clean.get("commit_sha"),
        provider=clean["provider"],
        region=clean["region"],
        instance_type=clean["instance_type"],
        duration_minutes=clean["duration_minutes"],
        cpu_utilization=clean["cpu_utilization"],
        cost_usd=cost_usd,
        energy_kwh=impact["energy_kwh"],
        emissions_gco2e=impact["emissions_gco2e"],
        avg_watts=impact["avg_watts"],
        hourly_price_usd=pricing["hourly_price_usd"],
        carbon_intensity_g_per_kwh=impact["carbon_intensity"]["carbon_intensity_g_per_kwh"],
        details={
            "pricing": pricing,
            "carbon": impact["carbon_intensity"],
            "recommendation": impact["recommendation"],
            "pricing_mode": clean["pricing_mode"],
            "report_type": _report_type(clean["pricing_mode"], pricing),
            "warning": _mode_warning(clean["pricing_mode"], pricing),
            "billing": projections["billing"],
            "carbon_projection": projections["carbon_projection"],
            "equivalents": projections["equivalents"],
            "efficiency": projections["efficiency"],
            "formula": {
                "cost": "hourly_price_usd * (duration_minutes / 60)",
                "energy_kwh": "(avg_watts * duration_hours) / 1000",
                "emissions_gco2e": "energy_kwh * carbon_intensity_g_per_kwh",
            },
        },
    )
    db.session.add(report)
    db.session.commit()
    return jsonify({"report": report.to_dict()}), 201


def _validate_report_payload(payload):
    required = ["provider", "region", "instance_type", "duration_minutes"]
    missing = [field for field in required if not payload.get(field)]
    if missing:
        raise ValueError(f"Missing required fields: {', '.join(missing)}")

    duration_minutes = _as_float(payload["duration_minutes"], "duration_minutes")
    if duration_minutes <= 0:
        raise ValueError("duration_minutes must be greater than zero.")

    cpu_utilization = _as_float(payload.get("cpu_utilization", 65), "cpu_utilization")
    if cpu_utilization < 0 or cpu_utilization > 100:
        raise ValueError("cpu_utilization must be between 0 and 100.")

    expected_runs_per_month = _as_float(
        payload.get("expected_runs_per_month", 300),
        "expected_runs_per_month",
    )
    if expected_runs_per_month < 0:
        raise ValueError("expected_runs_per_month must be zero or greater.")

    monthly_budget_usd = _as_float(payload.get("monthly_budget_usd", 25), "monthly_budget_usd")
    if monthly_budget_usd < 0:
        raise ValueError("monthly_budget_usd must be zero or greater.")

    pricing_mode = str(payload.get("pricing_mode") or "approximate").strip().lower()
    if pricing_mode not in {"approximate", "accurate"}:
        raise ValueError("pricing_mode must be approximate or accurate.")
    if pricing_mode == "accurate" and not str(payload.get("live_api_key") or "").strip():
        raise ValueError("Please enter Live API key for accurate pricing.")

    return {
        "pipeline_name": str(payload.get("pipeline_name") or "CI Pipeline")[:160],
        "repository": _optional_text(payload.get("repository"), 200),
        "branch": _optional_text(payload.get("branch"), 120),
        "commit_sha": _optional_text(payload.get("commit_sha"), 80),
        "provider": str(payload["provider"]).strip().lower(),
        "region": str(payload["region"]).strip(),
        "instance_type": str(payload["instance_type"]).strip(),
        "duration_minutes": duration_minutes,
        "cpu_utilization": cpu_utilization,
        "expected_runs_per_month": expected_runs_per_month,
        "monthly_budget_usd": monthly_budget_usd,
        "pricing_mode": pricing_mode,
    }


def _as_float(value, field_name):
    try:
        return float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"{field_name} must be a number.") from exc


def _optional_text(value, max_length):
    if value is None:
        return None
    value = str(value).strip()
    return value[:max_length] if value else None


def _mode_warning(pricing_mode, pricing):
    if pricing_mode == "accurate" and not pricing.get("is_estimate"):
        return None
    if pricing_mode == "accurate":
        return "Live pricing was requested, but the app used fallback pricing. Check the API key/provider setup."
    return "Approximate estimate: use Live API keys to get more accurate pricing results."


def _report_type(pricing_mode, pricing):
    if pricing_mode == "accurate" and not pricing.get("is_estimate"):
        return "Accurate live pricing report"
    return "Approximate estimate report"


def _build_projections(clean, cost_usd, impact):
    runs_per_month = clean["expected_runs_per_month"]
    runs_per_year = runs_per_month * 12
    monthly_cost = cost_usd * runs_per_month
    yearly_cost = cost_usd * runs_per_year
    monthly_energy = impact["energy_kwh"] * runs_per_month
    yearly_energy = impact["energy_kwh"] * runs_per_year
    monthly_emissions_g = impact["emissions_gco2e"] * runs_per_month
    yearly_emissions_g = impact["emissions_gco2e"] * runs_per_year
    monthly_budget = clean["monthly_budget_usd"]
    recommendation = impact["recommendation"]
    monthly_savings_g = recommendation.get("potential_savings_gco2e", 0) * runs_per_month

    return {
        "billing": {
            "expected_runs_per_month": runs_per_month,
            "monthly_budget_usd": monthly_budget,
            "projected_monthly_cost_usd": monthly_cost,
            "projected_yearly_cost_usd": yearly_cost,
            "cost_per_minute_usd": cost_usd / clean["duration_minutes"],
            "budget_remaining_usd": monthly_budget - monthly_cost,
            "budget_status": "over_budget" if monthly_budget and monthly_cost > monthly_budget else "within_budget",
        },
        "carbon_projection": {
            "projected_monthly_energy_kwh": monthly_energy,
            "projected_yearly_energy_kwh": yearly_energy,
            "projected_monthly_emissions_gco2e": monthly_emissions_g,
            "projected_yearly_emissions_gco2e": yearly_emissions_g,
            "projected_monthly_emissions_kgco2e": monthly_emissions_g / 1000,
            "projected_yearly_emissions_kgco2e": yearly_emissions_g / 1000,
            "estimated_monthly_region_savings_gco2e": monthly_savings_g,
            "estimated_monthly_region_savings_kgco2e": monthly_savings_g / 1000,
        },
        "equivalents": {
            "smartphone_charges_per_run": impact["energy_kwh"] / 0.012,
            "driving_km_per_run": impact["emissions_gco2e"] / 120,
            "tree_days_to_absorb_run": impact["emissions_gco2e"] / 60,
        },
        "efficiency": {
            "score": _efficiency_score(cost_usd, impact["emissions_gco2e"], clean["duration_minutes"]),
            "label": _efficiency_label(cost_usd, impact["emissions_gco2e"], clean["duration_minutes"]),
        },
    }


def _efficiency_score(cost_usd, emissions_gco2e, duration_minutes):
    cost_pressure = min((cost_usd / max(duration_minutes, 1)) / 0.02, 1)
    carbon_pressure = min((emissions_gco2e / max(duration_minutes, 1)) / 80, 1)
    score = 100 - ((cost_pressure * 45) + (carbon_pressure * 55))
    return round(max(0, min(score, 100)))


def _efficiency_label(cost_usd, emissions_gco2e, duration_minutes):
    score = _efficiency_score(cost_usd, emissions_gco2e, duration_minutes)
    if score >= 80:
        return "Efficient"
    if score >= 55:
        return "Moderate"
    return "Needs attention"
