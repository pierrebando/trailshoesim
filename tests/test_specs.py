"""Phase 3: spec extraction, verification and product-page location (no network)."""

import datetime as dt
from pathlib import Path

import pytest
from pydantic import ValidationError

from pipeline.models import (
    CanonicalModel,
    Derivation,
    FoamFamily,
    ModelSpecs,
    Plate,
    Width,
)
from pipeline.specs.__main__ import empty_record, record_from_page
from pipeline.specs.extract import Found, extract, foam_family, verify
from pipeline.specs.locate import best_candidate, find_candidates, slug_tokens
from pipeline.specs.pagetext import page_text

FIXTURES = Path(__file__).parent / "fixtures" / "specs"


def extracted(name: str, women: bool = False) -> tuple[dict, str]:
    page = page_text((FIXTURES / name).read_text(encoding="utf-8"))
    found = extract(page.text, page.product_name, women)
    for field, value in found.items():
        assert verify(value, page.text), f"{field} does not verify"
    return {field: value.value for field, value in found.items()}, page.text


def test_list_layout() -> None:
    values, text = extracted("list_layout.html")
    assert values["drop_mm"] == 6.0
    assert (values["stack_heel_mm"], values["stack_forefoot_mm"]) == (24.0, 18.0)
    assert values["lug_depth_mm"] == 4.5
    assert values["weight_g"] == 255.0  # not 199 g from the related product
    assert values["midsole_foam"] == "ExampleFoam"
    assert values["midsole_foam_family"] is FoamFamily.OTHER
    assert values["outsole_rubber"] == "VIBRAM® Megagrip"
    assert values["plate"] is Plate.ROCK_PLATE
    assert "waterproof" not in values  # "Imperméables" is in the menu, not the product name
    assert "Vous aimerez aussi" not in text


def test_inline_layout_with_ounces_and_both_genders() -> None:
    values, _ = extracted("inline_layout.html")
    assert values["lug_depth_mm"] == 5.0
    assert values["drop_mm"] == 4.0
    assert (values["stack_heel_mm"], values["stack_forefoot_mm"]) == (30.0, 26.0)
    assert (values["weight_g"], values["weight_women_g"]) == (286.0, 249.0)  # grams as printed
    assert values["midsole_foam"] == "PWRRUN"
    assert values["outsole_rubber"] == "Vibram Megagrip"
    assert values["upper_notes"].startswith("CONÇUE POUR LE TRAIL")
    assert "width_options" not in values  # the JSON blob is ignored


def test_value_before_label_layout() -> None:
    page = page_text((FIXTURES / "value_first_layout.html").read_text(encoding="utf-8"))
    found = extract(page.text, page.product_name)
    assert found["weight_g"].value == 310.0
    assert found["weight_g"].derivation is Derivation.UNIT_FROM_LABEL
    assert "Taille: 42" in found["weight_g"].note
    assert found["drop_mm"].value == 6.0
    assert (found["stack_heel_mm"].value, found["stack_forefoot_mm"].value) == (30.0, 24.0)
    assert found["stack_heel_mm"].derivation is Derivation.ORDER_FROM_DROP
    assert found["midsole_foam"].value == "BOUNCE FOAM"


def test_table_layout() -> None:
    values, _ = extracted("table_layout.html")
    assert values["weight_g"] == 301.0
    assert values["drop_mm"] == 8.0
    assert values["lug_depth_mm"] == 5.0
    assert values["outsole_rubber"] == "VIBRAM MEGAGRIP"
    assert values["waterproof"] is True  # GORE-TEX in the product name
    assert values["width_options"] == [Width.STANDARD]
    assert "midsole_foam" not in values  # "Amorti | Faible" is a rating widget


def test_verify_rejects_values_that_are_not_on_the_page() -> None:
    text = "Poids : 265 g | Drop : 6 mm"
    assert verify(Found(265.0, "Poids : 265 g", "265 g"), text)
    assert not verify(Found(250.0, "Poids : 250 g", "250 g"), text)  # snippet not on page
    assert not verify(Found(6.0, "Poids : 265 g", "6 mm"), text)  # proof not in snippet


def test_unlabelled_stack_pair_without_drop_is_skipped() -> None:
    found = extract("Hauteur de semelle : 22 mm / 30 mm | Poids : 250 g", "Shoe")
    assert "stack_heel_mm" not in found and "drop_mm" not in found


def test_ounces_only_are_converted_and_flagged() -> None:
    found = extract("Weight : 10 oz | Lugs : 4 mm", "Shoe")
    assert found["weight_g"].value == 283
    assert found["weight_g"].derivation is Derivation.OZ_TO_G


def test_pair_weight_is_skipped_with_a_reason() -> None:
    skipped: dict = {}
    assert "weight_g" not in extract("Poids (g) : | 620", "Lifestyle Shoe", skipped=skipped)
    assert "not plausible for one shoe" in skipped["weight_g"]


@pytest.mark.parametrize(
    "text",
    [
        "• Semelle intérieure composée à 30 % de mousse EVA intégrée recyclée | • Poids : 185 g",
        "• Assise plantaire amovible en mousse EVA 50 % recyclée | • Poids : 300 g",
    ],
)
def test_insole_foam_is_not_the_midsole(text: str) -> None:
    assert "midsole_foam" not in extract(text, "Barefoot Shoe")


def test_total_height_is_a_stack_label() -> None:
    found = extract("• Hauteur totale : 23,5-19,5 mm | • Drop : 4 mm", "Shoe")
    assert (found["stack_heel_mm"].value, found["stack_forefoot_mm"].value) == (23.5, 19.5)


def test_outsole_sentence_is_not_a_rubber_name() -> None:
    assert "outsole_rubber" not in extract("Semelle extérieure : en caoutchouc durable", "Shoe")


def test_last_segment_only_ignores_folders() -> None:
    url = "https://x.com/fr_FR/homme/chaussures/tomir/nnormal-kboix-N2ZKXM1-001"
    assert "tomir" in slug_tokens(url)
    assert slug_tokens(url, last_segment_only=True) == ["nnormal", "kboix"]


@pytest.mark.parametrize(
    ("name", "family"),
    [
        ("PWRRUN PB", FoamFamily.PEBA),
        ("Pebax® foam", FoamFamily.PEBA),
        ("LOWA® DYNAEVA®", FoamFamily.EVA),
        ("eTPU beads", FoamFamily.TPU),
        ("EVA + TPU blend", FoamFamily.HYBRID),
        ("FloatPro™", FoamFamily.OTHER),  # trade name: no guess about its chemistry
    ],
)
def test_foam_family_from_name_only(name: str, family: FoamFamily) -> None:
    assert foam_family(name) is family


def test_slug_tokens_stop_at_codes_and_split_glued_versions() -> None:
    assert slug_tokens("https://x.com/FR/fr_FR/ride-tr3/61276M.html") == [
        "fr",
        "fr",
        "fr",
        "ride",
        "tr",
        "3",
    ]
    assert slug_tokens("https://x.com/products/spin-ultra-2-trail-33068-351-2") == [
        "products",
        "spin",
        "ultra",
        "2",
        "trail",
    ]
    assert slug_tokens("https://x.com/fr/tomir-2-0") == ["fr", "tomir", "2"]


PAGES = {
    "https://x.com/FR/fr_FR/peregrine-16/1001M.html": "sitemap",
    "https://x.com/FR/fr_FR/peregrine-16/1002W.html": "sitemap",
    "https://x.com/FR/fr_FR/peregrine-16-gtx/1003M.html": "sitemap",
    "https://x.com/FR/fr_FR/peregrine-15/0999M.html": "sitemap",
    "https://x.com/FR/fr_FR/kjerag-2/1100M.html": "sitemap",
}


def test_find_candidates_respects_versions() -> None:
    urls = {c.url for c in find_candidates("peregrine", "16", PAGES, r"\.html$")}
    assert all("peregrine-16" in url for url in urls) and len(urls) == 3
    assert find_candidates("kjerag", None, PAGES, r"\.html$") == []  # "kjerag-2" is version 2
    assert find_candidates("peregrine", "14", PAGES, r"\.html$") == []


def test_find_candidates_decodes_urls_and_knows_synonyms() -> None:
    pages = {
        "https://x.com/fr/pd/trail-voyage-nitro%C2%A04-homme/311041": "s",  # non-breaking space
        "https://x.com/FR/agility-trail/60972M.html": "s",
        "https://x.com/products/golden-gate-2-all-terrain-shoe-33085-351-10": "s",
        "https://x.com/FR/agility-trail-trek/60974U.html": "s",
    }
    assert [c.url for c in find_candidates("voyage nitro", "4", pages, "pd")] == [
        "https://x.com/fr/pd/trail-voyage-nitro%C2%A04-homme/311041"
    ]
    assert find_candidates("voyage nitro", "3", pages, "pd") == []  # versions stay strict
    agility = find_candidates("agility tr", None, pages, r"\.html$")  # retailer's "TR"
    assert best_candidate(agility, None, None).url.endswith("/agility-trail/60972M.html")
    assert len(find_candidates("golden gate 2 atr", None, pages, "products")) == 1


def test_best_candidate_prefers_base_model_and_mens_page() -> None:
    candidates = find_candidates("peregrine", "16", PAGES, r"\.html$")
    best = best_candidate(candidates, r"M\.html$", r"W\.html$")
    assert best.url.endswith("/peregrine-16/1001M.html")


MODEL = CanonicalModel.model_validate(
    {
        "id": "fictional-ridge-2",
        "key": "fictional|ridge|2",
        "brand": "Fictional",
        "model": "Ridge",
        "version": "2",
        "category": "trail",
        "gender_variants": ["men"],
        "variants": {},
        "match_confidence": "exact",
        "is_latest_version": None,
        "is_discounted_old_version": False,
        "newer_version_id": None,
        "retailers": ["glisshop"],
        "offers": [
            {
                "retailer": "glisshop",
                "url": "https://example.com/p",
                "retailer_product_id": None,
                "raw_title": "Ridge 2",
                "title_key": "fictional|ridge|2",
                "gender": "men",
                "variant": {},
                "price_eur": 100,
                "in_stock": None,
                "rating": None,
                "review_count": None,
                "retrieved_at": "2026-10-28",
            }
        ],
        "buyer_rating": {
            "review_count_total": 0,
            "raw_mean_0_5": None,
            "bayesian_mean_0_5": None,
            "prior_mean_0_5": 4.3,
            "prior_strength": 20,
        },
        "review_flags": [],
    }
)


def test_record_from_page_keeps_provenance_and_snippets() -> None:
    html = (FIXTURES / "list_layout.html").read_text(encoding="utf-8")
    record, rejected = record_from_page(
        MODEL, "https://example.com/ridge-2", html, dt.date(2026, 10, 28), page_is_women=False
    )
    assert rejected == []
    assert record.weight_g.value == 255.0
    assert record.weight_g.source_url.host == "example.com"
    assert "255 g" in record.weight_g.raw_snippet
    assert record.waterproof.value is None
    assert record.waterproof.missing_reason == "not stated on the manufacturer page"
    assert record.lab_fallback.lug_depth_mm.value is None  # separate, filled later


def test_empty_record_and_snippet_rule() -> None:
    record = empty_record(MODEL, "manufacturer site not collected: test")
    assert record.manufacturer_url is None and record.drop_mm.value is None
    data = record.model_dump()
    data["manufacturer_url"], data["manufacturer_url_missing_reason"] = "https://example.com", None
    data["drop_mm"] = {
        "value": 6.0,
        "source_name": "x",
        "source_url": "https://example.com",
        "retrieved_at": "2026-10-28",
    }
    with pytest.raises(ValidationError, match="raw_snippet"):
        ModelSpecs.model_validate(data)
