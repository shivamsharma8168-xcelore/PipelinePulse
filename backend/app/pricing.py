import requests
from flask import current_app

from .cache import cache_get, cache_set
from .catalog import get_instance, get_region


class PricingLookupError(ValueError):
    pass


def get_hourly_price(provider_id, region_id, instance_type, pricing_mode="approximate"):
    use_live_pricing = pricing_mode == "accurate" and current_app.config["ENABLE_LIVE_PRICING"]
    cache_key = f"pricing:v3:{pricing_mode}:{provider_id}:{region_id}:{instance_type}"
    cached = cache_get(cache_key)
    if cached:
        return cached

    instance = get_instance(provider_id, instance_type)
    region = get_region(provider_id, region_id)
    if not instance or not region:
        raise PricingLookupError("Unsupported provider, region, or instance type.")

    result = None
    if use_live_pricing:
        if provider_id == "aws":
            result = _aws_price(region_id, instance_type)
        elif provider_id == "azure":
            result = _azure_price(region_id, instance_type)

    if not result:
        result = {
            "hourly_price_usd": instance["fallback_hourly_price"],
            "currency": "USD",
            "source": "Estimated local cloud catalog",
            "is_estimate": True,
            "confidence": "approximate",
        }
    else:
        result["is_estimate"] = False
        result["confidence"] = "live"

    cache_set(cache_key, result, current_app.config["PRICING_CACHE_TTL_SECONDS"])
    return result


def _aws_price(region_id, instance_type):
    region = get_region("aws", region_id)
    if not region:
        return None

    base_url = current_app.config["AWS_PRICING_BASE_URL"].rstrip("/")
    url = f"{base_url}/{region_id}/index.json"
    try:
        response = requests.get(url, timeout=8)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None

    for sku, product in data.get("products", {}).items():
        attributes = product.get("attributes", {})
        if (
            attributes.get("instanceType") == instance_type
            and attributes.get("operatingSystem") == "Linux"
            and attributes.get("tenancy") == "Shared"
            and attributes.get("preInstalledSw") == "NA"
            and attributes.get("capacitystatus") == "Used"
        ):
            terms = data.get("terms", {}).get("OnDemand", {}).get(sku, {})
            price = _first_usd_price(terms)
            if price is not None:
                return {"hourly_price_usd": price, "currency": "USD", "source": "AWS Price List API"}
    return None


def _first_usd_price(terms):
    for term in terms.values():
        for dimension in term.get("priceDimensions", {}).values():
            price = dimension.get("pricePerUnit", {}).get("USD")
            if price is not None:
                return float(price)
    return None


def _azure_price(region_id, instance_type):
    params = {
        "$filter": (
            "serviceName eq 'Virtual Machines' "
            f"and armRegionName eq '{region_id}' "
            f"and armSkuName eq '{instance_type}' "
            "and priceType eq 'Consumption'"
        )
    }
    try:
        response = requests.get(current_app.config["AZURE_RETAIL_PRICES_URL"], params=params, timeout=8)
        response.raise_for_status()
        data = response.json()
    except requests.RequestException:
        return None

    linux_prices = [
        item
        for item in data.get("Items", [])
        if "windows" not in item.get("productName", "").lower()
        and item.get("unitOfMeasure", "").lower() == "1 hour"
    ]
    if not linux_prices:
        return None

    selected = min(linux_prices, key=lambda item: float(item.get("retailPrice", 0) or 0))
    return {
        "hourly_price_usd": float(selected["retailPrice"]),
        "currency": selected.get("currencyCode", "USD"),
        "source": "Azure Retail Prices API",
    }
