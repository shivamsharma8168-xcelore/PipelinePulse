from flask import current_app

from .cache import cache_get, cache_set
from .catalog import PROVIDER_CATALOG, get_instance, get_region


class EmissionsLookupError(ValueError):
    pass


def estimate_impact(provider_id, region_id, instance_type, duration_minutes, cpu_utilization):
    instance = get_instance(provider_id, instance_type)
    region = get_region(provider_id, region_id)
    if not instance or not region:
        raise EmissionsLookupError("Unsupported provider, region, or instance type.")

    duration_hours = duration_minutes / 60
    utilization = max(0.05, min(cpu_utilization / 100, 1))

    avg_watts = instance["watts"] * (0.35 + (0.65 * utilization))
    energy_kwh = (avg_watts * duration_hours) / 1000
    carbon_intensity = get_carbon_intensity(provider_id, region_id)
    emissions_gco2e = energy_kwh * carbon_intensity["carbon_intensity_g_per_kwh"]

    recommendation = _best_region_recommendation(provider_id, region_id, energy_kwh)

    return {
        "energy_kwh": energy_kwh,
        "avg_watts": avg_watts,
        "carbon_intensity": carbon_intensity,
        "emissions_gco2e": emissions_gco2e,
        "recommendation": recommendation,
    }


def get_carbon_intensity(provider_id, region_id):
    cache_key = f"carbon:{provider_id}:{region_id}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    region = get_region(provider_id, region_id)
    if not region:
        raise EmissionsLookupError("Unsupported provider or region.")

    result = {
        "carbon_intensity_g_per_kwh": region["carbon_intensity"],
        "source": "regional carbon intensity catalog",
    }
    cache_set(cache_key, result, current_app.config["CARBON_CACHE_TTL_SECONDS"])
    return result


def _best_region_recommendation(provider_id, current_region_id, energy_kwh):
    provider = PROVIDER_CATALOG[provider_id]
    current_region = provider["regions"][current_region_id]
    best_region_id, best_region = min(
        provider["regions"].items(),
        key=lambda item: item[1]["carbon_intensity"],
    )
    if best_region_id == current_region_id:
        return {
            "message": "This is already the lowest-carbon region in the current provider catalog.",
            "potential_savings_gco2e": 0,
        }

    current_emissions = energy_kwh * current_region["carbon_intensity"]
    best_emissions = energy_kwh * best_region["carbon_intensity"]
    savings = max(current_emissions - best_emissions, 0)
    return {
        "message": (
            f"Running in {best_region_id} ({best_region['label']}) could reduce this run by "
            f"{savings:.2f} gCO2e using the current regional catalog."
        ),
        "recommended_region": best_region_id,
        "potential_savings_gco2e": savings,
    }
