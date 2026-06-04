PROVIDER_CATALOG = {
    "aws": {
        "label": "Amazon Web Services",
        "regions": {
            "us-east-1": {
                "label": "US East (N. Virginia)",
                "carbon_intensity": 379,
                "location": "US East (N. Virginia)",
            },
            "us-west-2": {
                "label": "US West (Oregon)",
                "carbon_intensity": 162,
                "location": "US West (Oregon)",
            },
            "eu-west-1": {
                "label": "Europe (Ireland)",
                "carbon_intensity": 124,
                "location": "EU (Ireland)",
            },
            "ap-south-1": {
                "label": "Asia Pacific (Mumbai)",
                "carbon_intensity": 632,
                "location": "Asia Pacific (Mumbai)",
            },
        },
        "instances": {
            "t3.small": {"vcpu": 2, "memory_gb": 2, "watts": 35, "fallback_hourly_price": 0.0208},
            "t3.medium": {"vcpu": 2, "memory_gb": 4, "watts": 45, "fallback_hourly_price": 0.0416},
            "m6i.large": {"vcpu": 2, "memory_gb": 8, "watts": 65, "fallback_hourly_price": 0.096},
            "c6i.large": {"vcpu": 2, "memory_gb": 4, "watts": 70, "fallback_hourly_price": 0.085},
        },
    },
    "azure": {
        "label": "Microsoft Azure",
        "regions": {
            "eastus": {"label": "East US", "carbon_intensity": 367, "location": "eastus"},
            "westus2": {"label": "West US 2", "carbon_intensity": 158, "location": "westus2"},
            "westeurope": {"label": "West Europe", "carbon_intensity": 238, "location": "westeurope"},
            "centralindia": {"label": "Central India", "carbon_intensity": 632, "location": "centralindia"},
        },
        "instances": {
            "Standard_B1s": {"vcpu": 1, "memory_gb": 1, "watts": 22, "fallback_hourly_price": 0.0104},
            "Standard_B2s": {"vcpu": 2, "memory_gb": 4, "watts": 46, "fallback_hourly_price": 0.0416},
            "Standard_D2s_v5": {"vcpu": 2, "memory_gb": 8, "watts": 66, "fallback_hourly_price": 0.096},
            "Standard_F2s_v2": {"vcpu": 2, "memory_gb": 4, "watts": 70, "fallback_hourly_price": 0.085},
        },
    },
    "gcp": {
        "label": "Google Cloud Platform",
        "regions": {
            "us-central1": {"label": "Iowa", "carbon_intensity": 393, "location": "us-central1"},
            "us-west1": {"label": "Oregon", "carbon_intensity": 134, "location": "us-west1"},
            "europe-west1": {"label": "Belgium", "carbon_intensity": 111, "location": "europe-west1"},
            "asia-south1": {"label": "Mumbai", "carbon_intensity": 632, "location": "asia-south1"},
        },
        "instances": {
            "e2-small": {"vcpu": 2, "memory_gb": 2, "watts": 33, "fallback_hourly_price": 0.0168},
            "e2-medium": {"vcpu": 2, "memory_gb": 4, "watts": 43, "fallback_hourly_price": 0.0336},
            "n2-standard-2": {"vcpu": 2, "memory_gb": 8, "watts": 66, "fallback_hourly_price": 0.0971},
            "c3-standard-4": {"vcpu": 4, "memory_gb": 16, "watts": 126, "fallback_hourly_price": 0.2088},
        },
    },
}


def public_options():
    return {
        "providers": [
            {
                "id": provider_id,
                "label": provider["label"],
                "regions": [
                    {"id": region_id, "label": region["label"]}
                    for region_id, region in provider["regions"].items()
                ],
                "instances": [
                    {
                        "id": instance_id,
                        "label": instance_id,
                        "vcpu": spec["vcpu"],
                        "memory_gb": spec["memory_gb"],
                    }
                    for instance_id, spec in provider["instances"].items()
                ],
            }
            for provider_id, provider in PROVIDER_CATALOG.items()
        ]
    }


def get_provider(provider_id):
    return PROVIDER_CATALOG.get(provider_id)


def get_instance(provider_id, instance_type):
    provider = get_provider(provider_id)
    if not provider:
        return None
    return provider["instances"].get(instance_type)


def get_region(provider_id, region_id):
    provider = get_provider(provider_id)
    if not provider:
        return None
    return provider["regions"].get(region_id)
