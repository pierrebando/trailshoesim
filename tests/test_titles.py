"""Title parsing on real-looking French and English retailer titles."""

import pytest

from pipeline.models import Gender
from pipeline.normalize.titles import parse_title

WP = {"waterproof"}
GTX = {"gore_tex", "waterproof"}

# (raw title, retailer brand field, expected key, expected gender, expected variants)
CASES = [
    # English, other-retailer style
    ("Hoka One One Speedgoat 6 GTX Men's Trail Running Shoes - Black", None, "hoka|speedgoat|6", Gender.MEN, GTX),
    ("On Cloudultra 2 Men's Trail Running Shoes", None, "on|cloudultra|2", Gender.MEN, set()),
    ("Women's Salomon Speedcross 6 Wide Noir/Blanc", None, "salomon|speedcross|6", Gender.WOMEN, {"wide"}),
    ("Inov-8 Trailfly Speed - Women's", None, "inov 8|trailfly speed|", Gender.WOMEN, set()),
    ("The North Face Vectiv Enduris 4 Chaussures de trail homme", None, "the north face|vectiv enduris|4", Gender.MEN, set()),
    # French, brand not first
    ("Chaussures de trail Hoka Speedgoat 6 Femme", None, "hoka|speedgoat|6", Gender.WOMEN, set()),
    ("HOKA Speedgoat 6 Homme", None, "hoka|speedgoat|6", Gender.MEN, set()),
    ("Scarpa Ribelle Run XT GTX Imperméable", None, "scarpa|ribelle run xt|", None, GTX),
    # Tradeinn style
    ("Salomon Chaussures de trail running XA Pro 3D V9 GORE-TEX®", "Salomon", "salomon|xa pro 3d|9", None, GTX),
    ("La Sportiva Chaussures de trail running Bushido III", "La sportiva", "la sportiva|bushido|3", None, set()),
    ("Mizuno Chaussures de trail running Wave Rider GORE-TEX® 3", "Mizuno", "mizuno|wave rider|3", None, GTX),
    ("Altra Chaussures de trail running Lone Peak 9+ GORE-TEX®", "Altra", "altra|lone peak|9+", None, GTX),
    ("Altra Chaussures de trail running Lone Peak 9 WP Mid", "Altra", "altra|lone peak|9", None, WP | {"mid"}),
    ("Altra Chaussures de trail running Olympus 275", "Altra", "altra|olympus 275|", None, set()),
    ("Altra Chaussures de trail running Mont Blanc Carbon", "Altra", "altra|mont blanc carbon|", None, set()),
    ("Altra Mont Blanc", None, "altra|mont blanc|", None, set()),
    ("New Balance Chaussures de trail running MT410v5", "New Balance", "new balance|410|5", None, set()),
    ("New Balance Chaussures de trail running Fresh Foam 410 v9", "New Balance", "new balance|410|9", None, set()),
    ("New Balance Chaussures de trail running Fresh Foam X Garoé v2", "New Balance", "new balance|garoe|2", None, set()),
    ("New Balance Chaussures de trail running Fresh Foam X GaroÉ V2", "New Balance", "new balance|garoe|2", None, set()),
    ("New Balance Chaussures de trail running larges Garoé v2", "New Balance", "new balance|garoe|2", None, {"wide"}),
    ("New Balance Chaussures de trail running extra larges DynaSoft Nitrel v6", "New Balance", "new balance|dynasoft nitrel|6", None, {"extra_wide"}),
    ("New Balance Chaussures de trail running Dynasoft Nitrel V6 GORE-TEXÂ®", "New Balance", "new balance|dynasoft nitrel|6", None, GTX),
    ("Joma Chaussures de trail running Sima 2610V Barefoot", "Joma", "joma|sima barefoot|", None, set()),
    ("Joma Chaussures de trail running TR-6", "Joma", "joma|tr|6", None, set()),
    ("Saucony Chaussures de trail running Ride TR2", "Saucony", "saucony|ride tr|2", None, set()),
    ("Saucony Chaussures de trail running Guide TR", "Saucony", "saucony|guide tr|", None, set()),
    ("Asics Chaussures de trail running GT-2000 15 TR", "Asics", "asics|gt 2000 tr|15", None, set()),
    ("NNormal Chaussures de trail running Tomir 02", "NNormal", "nnormal|tomir|2", None, set()),
    ("NNormal Chaussures de trail running Tomir 2.0 reconditionné", "NNormal", "nnormal|tomir|2", None, {"refurbished"}),
    ("Under Armour Chaussures de trail running Charged Bandit Trail 3", "Under Armour", "under armour|charged bandit tr|3", None, set()),
    ("Under Armour Chaussures de trail running Charged Bandit TR 3", "Under Armour", "under armour|charged bandit tr|3", None, set()),
    ("Merrell Chaussures de trail running Speed Strike 2 LTR", "Merrell", "merrell|speed strike|2", None, {"leather"}),
    ("Merrell Chaussures de trail running Agility Trail Waterproof", "Merrell", "merrell|agility tr|", None, WP),
    ("Puma Chaussures de trail running Fast-Trac NITRO™ 4 GORE-TEX®", "Puma", "puma|fast trac nitro|4", None, GTX),
    ("Merrell Chaussures de trail running Trail Glove 8", "Merrell", "merrell|trail glove|8", None, set()),
    ("Asics Gel-Nimbus 28 Trail", "Asics", "asics|gel nimbus tr|28", None, set()),
    ("Vibram Fivefingers Chaussures de trail running V-Alpha", "Vibram Fivefingers", "vibram fivefingers|v alpha|", None, set()),
    # Glisshop model names (colour already removed by the retailer), with gender markers
    ("Prodigio 2 Woman", "La Sportiva", "la sportiva|prodigio|2", Gender.WOMEN, set()),
    ("Bushido III Woman", "La Sportiva", "la sportiva|bushido|3", Gender.WOMEN, set()),
    ("Pyrox Hybrid Ms", "Tecnica", "tecnica|pyrox hybrid|", Gender.MEN, set()),
    ("Xplor 2 W", "Craft", "craft|xplor|2", Gender.WOMEN, set()),
    ("Ultra 100 V3 W", "Dynafit", "dynafit|ultra 100|3", Gender.WOMEN, set()),
    ("Ultra 50", "Dynafit", "dynafit|ultra 50|", None, set()),
    ("W's Supertrac RC 3", "Scott", "scott|supertrac rc|3", Gender.WOMEN, set()),
    ("Zorblax Mountain Runner 2", None, "?|zorblax mountain runner|2", None, set()),
]  # fmt: skip


@pytest.mark.parametrize(("title", "brand", "key", "gender", "variants"), CASES)
def test_parse_title(title: str, brand, key: str, gender, variants: set[str]) -> None:
    parsed = parse_title(title, brand)
    assert parsed.key == key
    assert parsed.gender == gender
    assert parsed.variants == variants


def test_there_are_at_least_25_title_cases() -> None:
    assert len(CASES) >= 25


def test_display_keeps_original_spelling() -> None:
    assert parse_title("Asics Gel-Nimbus 28 TR").model == "Gel-Nimbus TR"
    assert parse_title("Joma Chaussures de trail running TR-6").model == "TR"
    assert parse_title("New Balance MT410v5").model == "MT410"
    assert parse_title("NNormal Cadí GORE-TEX®").model == "Cadí"


def test_categories() -> None:
    assert (
        parse_title("adidas Chaussures de trail pour enfants Terrex Agravic BOA CP").category
        == "kids"
    )
    gravel = parse_title("Salomon Chaussures de running pour gravier Aero Blaze 4 GORE-TEX®")
    assert gravel.category == "gravel" and gravel.key == "salomon|aero blaze|4"


def test_warnings() -> None:
    assert parse_title("Zorblax Mountain Runner 2").warnings[0].startswith("unknown brand")
    coded = parse_title("New Balance Chaussures de trail running MTTTRRG1 Tektrel", "New Balance")
    assert coded.key == "new balance|tektrel|"
    assert "title contains a product code" in coded.warnings


def test_short_brand_alias_is_only_removed_once() -> None:
    # "on" is a brand and an English word: only the brand occurrence goes.
    assert parse_title("On Cloud Slip On 2").model_key == "cloud slip on"
