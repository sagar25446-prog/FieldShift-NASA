import json
from pathlib import Path
from urllib.parse import urlparse


CATALOG_PATH = Path(__file__).resolve().parents[1] / "data" / "crops.json"
REQUIRED_FIELDS = {"id", "name", "scientific_name", "family", "legume", "intended_role", "growing_seasons", "temperature_suitability", "water_requirement", "soil_constraints", "nutrient_characteristics", "rotation_compatibility", "pest_disease_restrictions", "evidence_quality", "source_ids"}


def load_catalog() -> dict:
    return json.loads(CATALOG_PATH.read_text(encoding="utf-8"))


def test_catalog_sources_are_complete_https_references() -> None:
    catalog = load_catalog()
    assert catalog["catalog_metadata"]["demonstration_region"]
    for source in catalog["sources"].values():
        assert source["title"] and source["access_date"]
        parsed = urlparse(source["url"])
        assert parsed.scheme == "https" and parsed.netloc


def test_crops_have_required_fields_and_resolvable_sources() -> None:
    catalog = load_catalog()
    valid_source_ids, seen_ids = set(catalog["sources"]), set()
    for crop in catalog["crops"]:
        assert REQUIRED_FIELDS <= crop.keys(), crop.get("id")
        assert crop["id"] not in seen_ids
        seen_ids.add(crop["id"])
        assert isinstance(crop["legume"], bool) and crop["growing_seasons"]
        assert crop["source_ids"] and set(crop["source_ids"]) <= valid_source_ids


def test_water_temperature_units_sources_and_unknowns_are_explicit() -> None:
    catalog = load_catalog()
    valid_source_ids = set(catalog["sources"])
    for crop in catalog["crops"]:
        temperature, water = crop["temperature_suitability"], crop["water_requirement"]
        assert temperature["unit"] == "degC"
        assert temperature["status"] in {"unknown", "documented_ecocrop"}
        if temperature["status"] == "unknown":
            assert temperature["value"] is None and temperature["evidence_needed"]
        else:
            assert temperature["tmin_absolute"] < temperature["tmin_optimal"]
            assert temperature["tmin_optimal"] <= temperature["tmax_optimal"]
            assert temperature["tmax_optimal"] < temperature["tmax_absolute"]
        assert set(temperature["source_ids"]) <= valid_source_ids
        assert water["unit"] == "mm per crop period"
        assert set(water["source_ids"]) <= valid_source_ids
        if water["status"] == "unknown":
            assert water["range_min"] is None and water["range_max"] is None
            assert water["evidence_needed"]
        else:
            assert water["status"] == "documented_approximation"
            assert water["range_min"] < water["range_max"]
            assert water["method_context"] and water["source_ids"]
