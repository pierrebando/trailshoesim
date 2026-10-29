"""Pydantic models of the final shoe record shipped to the web app.

These models are the single source of truth for the data format: the JSON Schemas in
`schema/` are generated from them (`python -m pipeline.build.export_schema`).

Two project rules are enforced here rather than left to discipline:

* "Never invent data": a spec value is either known (and then carries its provenance)
  or missing (and then carries a `missing_reason`). See `SourcedValue`.
* "Only short excerpts": any third-party text is limited to `MAX_EXCERPT_WORDS` words.
"""

import datetime as dt
from enum import StrEnum
from typing import Annotated, Generic, Self, TypeVar

from pydantic import AfterValidator, BaseModel, ConfigDict, Field, HttpUrl, model_validator

MAX_EXCERPT_WORDS = 30
"""Longest third-party excerpt we allow ourselves to store (copyright rule)."""


def _check_excerpt_length(text: str) -> str:
    """Reject excerpts longer than MAX_EXCERPT_WORDS words."""
    word_count = len(text.split())
    if word_count > MAX_EXCERPT_WORDS:
        raise ValueError(f"excerpt has {word_count} words, max is {MAX_EXCERPT_WORDS}")
    return text


# The JSON Schema cannot count words, so max_length is a rough character guard for
# non-Python readers; the word limit itself is enforced by the validator.
Excerpt = Annotated[str, Field(min_length=1, max_length=250), AfterValidator(_check_excerpt_length)]
Score0To10 = Annotated[float, Field(ge=0, le=10)]
Fraction = Annotated[float, Field(ge=0, le=1)]


class StrictModel(BaseModel):
    """Base class: unknown fields are an error, so a typo cannot silently drop data."""

    model_config = ConfigDict(extra="forbid")


# ---------------------------------------------------------------------------
# Vocabularies
# ---------------------------------------------------------------------------


class Gender(StrEnum):
    """Gender variants a shoe is sold in."""

    MEN = "men"
    WOMEN = "women"
    UNISEX = "unisex"


class Width(StrEnum):
    """Foot width options."""

    NARROW = "narrow"
    STANDARD = "standard"
    WIDE = "wide"
    EXTRA_WIDE = "extra_wide"


class Plate(StrEnum):
    """Type of plate in the midsole."""

    NONE = "none"
    ROCK_PLATE = "rock_plate"
    CARBON = "carbon"
    OTHER = "other"


class LugSpacing(StrEnum):
    """Qualitative spacing between outsole lugs (rarely published as a number)."""

    TIGHT = "tight"
    MEDIUM = "medium"
    WIDE = "wide"


class Retailer(StrEnum):
    """Retailers that define which shoes are in the catalogue (see docs/sources.md)."""

    LE_PAPE = "le_pape"
    IRUN = "irun"
    TRADEINN = "tradeinn"
    GLISSHOP = "glisshop"


class Criterion(StrEnum):
    """The eight scoring criteria (see docs/scoring-spec.md, section 2)."""

    CUSHIONING = "cushioning"
    PROTECTION = "protection"
    GRIP = "grip"
    STABILITY = "stability"
    RESPONSIVENESS = "responsiveness"
    LIGHTNESS = "lightness"
    DURABILITY = "durability"
    FIT_WIDTH = "fit_width"


class ConfidenceLevel(StrEnum):
    """How much the user should trust the scores of a shoe."""

    HIGH = "high"
    MEDIUM = "medium"
    LOW = "low"


class FoamFamily(StrEnum):
    """Normalised family of a midsole foam (phase 3), read from the foam's own name."""

    PEBA = "peba"
    EVA = "eva"
    TPU = "tpu"
    HYBRID = "hybrid"
    OTHER = "other"


class SpecSource(StrEnum):
    """Which kind of source a resolved spec value comes from (phase 6 priority order)."""

    MANUFACTURER = "manufacturer"
    MANUAL = "manual"  # read on a product page by the student (data/manual/missing_specs.csv)
    LAB_MEASUREMENT = "lab_measurement"  # measured by a review source (RunRepeat)
    RETAILER = "retailer"  # shown on a retailer product page (lower confidence)


class Derivation(StrEnum):
    """Documented ways a stored value may differ from the text of the page."""

    OZ_TO_G = "oz_to_g"  # weight converted from ounces (1 oz = 28.3495 g)
    COMPUTED_FROM_STACKS = "computed_from_stacks"  # drop = heel stack - forefoot stack
    UNIT_FROM_LABEL = "unit_from_label"  # number written alone, unit given by the label
    ORDER_FROM_DROP = "order_from_drop"  # unlabelled stack pair, heel/forefoot set by the drop
    FAMILY_FROM_NAME = "family_from_name"  # foam family from words in the foam name
    FROM_SITEMAP_URL = "from_sitemap_url"  # width option seen in a product URL of the sitemap


# ---------------------------------------------------------------------------
# Values with provenance
# ---------------------------------------------------------------------------

T = TypeVar("T")


class SourcedValue(StrictModel, Generic[T]):
    """A value together with where it came from, or why it is missing.

    Either `value` is set and the provenance fields are filled, or `value` is null and
    `missing_reason` explains why (e.g. "not listed on manufacturer page").
    """

    value: T | None = None
    source_name: str | None = Field(
        default=None, description="e.g. 'hoka.com' or 'derived from stack heights'"
    )
    source_url: HttpUrl | None = None
    retrieved_at: dt.date | None = None
    missing_reason: str | None = None
    note: str | None = Field(
        default=None, description="Context needed to interpret the value, e.g. the size weighed."
    )
    raw_snippet: Excerpt | None = Field(
        default=None, description="Verbatim text of the source page that contains the value."
    )
    derivation: Derivation | None = Field(
        default=None, description="How the value was obtained when it is not copied as-is."
    )

    @model_validator(mode="after")
    def _known_value_has_provenance_missing_value_has_reason(self) -> Self:
        if self.value is None:
            if not self.missing_reason:
                raise ValueError("a missing value must say why (missing_reason)")
        elif self.source_name is None or self.source_url is None or self.retrieved_at is None:
            raise ValueError("a known value needs source_name, source_url and retrieved_at")
        return self


# Named subclasses give readable names in the generated JSON Schema.
class SourcedFloat(SourcedValue[float]):
    """A sourced number (grams or millimetres)."""


class SourcedInt(SourcedValue[int]):
    """A sourced integer."""


class SourcedStr(SourcedValue[str]):
    """A sourced free-text value."""


class SourcedBool(SourcedValue[bool]):
    """A sourced yes/no value."""


class SourcedPlate(SourcedValue[Plate]):
    """A sourced plate type."""


class SourcedLugSpacing(SourcedValue[LugSpacing]):
    """A sourced lug spacing."""


class SourcedWidthList(SourcedValue[list[Width]]):
    """A sourced list of available widths."""


class SourcedFoamFamily(SourcedValue[FoamFamily]):
    """A sourced foam family."""


# ---------------------------------------------------------------------------
# Record parts
# ---------------------------------------------------------------------------


class RetailOffer(StrictModel):
    """One product page at one retailer."""

    retailer: Retailer
    url: HttpUrl
    price_eur: float = Field(gt=0)
    price_date: dt.date = Field(description="Day the price was read.")
    rating: float | None = Field(
        default=None, ge=0, le=5, description="Average buyer rating, normalised to a 0-5 scale."
    )
    review_count: int | None = Field(default=None, ge=0)

    @model_validator(mode="after")
    def _rating_needs_review_count(self) -> Self:
        # A rating without its review count cannot be Bayesian-averaged (spec section 4).
        if self.rating is not None and not self.review_count:
            raise ValueError("a rating requires a positive review_count")
        return self


class Specs(StrictModel):
    """Technical specs. Every field is required so the builder must decide value-or-reason."""

    weight_g: SourcedFloat = Field(description="Weight of one shoe, men's reference size.")
    weight_women_g: SourcedFloat = Field(description="Weight of one shoe, women's reference size.")
    stack_heel_mm: SourcedFloat
    stack_forefoot_mm: SourcedFloat
    drop_mm: SourcedFloat
    lug_depth_mm: SourcedFloat
    lug_spacing: SourcedLugSpacing
    platform_width_heel_mm: SourcedFloat
    platform_width_forefoot_mm: SourcedFloat
    midsole_softness_ac: SourcedFloat = Field(
        description="Midsole hardness measured by a lab (Asker C durometer): LOWER = softer."
    )
    energy_return_forefoot_pct: SourcedFloat = Field(
        description="Share of the impact energy the forefoot gives back, measured by a lab."
    )
    midsole_foam: SourcedStr
    plate: SourcedPlate
    outsole_rubber: SourcedStr
    waterproof: SourcedBool
    upper_notes: SourcedStr
    width_options: SourcedWidthList
    fit_width_tag: SourcedStr = Field(
        description="The retailer's own fit class, verbatim (e.g. 'Pied large'): an opinion."
    )
    sources: dict[str, SpecSource] = Field(
        description="For each KNOWN field, the kind of source it was taken from "
        "(priority: manufacturer > lab_measurement > retailer)."
    )


class AspectAssessment(StrictModel):
    """What one expert review says about one criterion, as extracted by the NLP step."""

    score_0_10: Score0To10
    evidence_excerpt: Excerpt
    mention_count: int = Field(ge=1, description="Sentences of the review about this criterion.")


class ExpertReview(StrictModel):
    """One test by a specialist review source. Only an excerpt and a link are kept."""

    source: str
    url: HttpUrl
    date: dt.date | None = Field(description="Publication date; null if the page shows none.")
    retrieved_at: dt.date
    language: str | None = Field(default=None, description="ISO 639-1 code, e.g. 'fr'.")
    conclusion_excerpt: Excerpt | None
    aspects: dict[Criterion, AspectAssessment]
    nlp_model: str | None = Field(
        default=None, description="Hugging Face model id that produced `aspects`."
    )


class BuyerRatingSummary(StrictModel):
    """Buyer ratings pooled over all retailers (spec section 4)."""

    review_count_total: int = Field(ge=0)
    raw_mean_0_5: float | None = Field(ge=0, le=5)
    bayesian_mean_0_5: float | None = Field(ge=0, le=5)
    prior_mean_0_5: float = Field(ge=0, le=5)
    prior_strength: float = Field(ge=0)


class ScoreInput(StrictModel):
    """One input of a score and its share of the final value (the provenance of a score)."""

    input: str = Field(description="e.g. 'specs.lug_depth_mm' or 'expert_reviews'.")
    source: str = Field(
        description="'manufacturer', 'lab_measurement', 'retailer', 'expert_reviews' or "
        "'neutral_prior' (the 5/10 that stands in for reviews not yet collected, spec §2.5)."
    )
    value: str = Field(description="The input as read, e.g. '4.5', 'Vibram Megagrip', '2 reviews'.")
    input_score_0_10: Score0To10
    weight: Fraction = Field(description="Share of the score; the weights of a score sum to 1.")


class CriterionScore(StrictModel):
    """Score of one criterion with the inputs that produced it (spec section 2)."""

    score_0_10: Score0To10 | None
    spec_score_0_10: Score0To10 | None
    expert_score_0_10: Score0To10 | None
    spec_input_coverage: Fraction = Field(
        description="Share of the spec input weight whose value was known."
    )
    expert_review_count: int = Field(ge=0)
    inputs_used: list[str]
    inputs_missing: list[str]
    provenance: list[ScoreInput] = Field(
        description="Inputs that produced score_0_10, with their weight. Buyer ratings are "
        "never an input of a criterion (spec section 2.6)."
    )


class CriteriaScores(StrictModel):
    """The eight criterion scores."""

    cushioning: CriterionScore
    protection: CriterionScore
    grip: CriterionScore
    stability: CriterionScore
    responsiveness: CriterionScore
    lightness: CriterionScore
    durability: CriterionScore
    fit_width: CriterionScore


class TerrainScore(StrictModel):
    """Suitability for one terrain type (spec section 3)."""

    score_0_10: Score0To10 | None
    inputs_used: list[str]
    inputs_missing: list[str]
    provenance: list[ScoreInput]


class TerrainScores(StrictModel):
    """The five terrain scores."""

    road_to_trail: TerrainScore
    groomed_mixed: TerrainScore
    technical_rocky: TerrainScore
    muddy_soft: TerrainScore
    wet_roots: TerrainScore


class Confidence(StrictModel):
    """How much the data behind this shoe can be trusted (spec section 8)."""

    spec_completeness_0_1: Fraction
    expert_review_count: int = Field(ge=0)
    buyer_review_count: int = Field(ge=0)
    price_age_days: int | None = Field(ge=0, description="Age of the freshest price at build time.")
    level: ConfidenceLevel
    reasons: list[str] = Field(description="Why the level is not higher, in plain English.")


class Shoe(StrictModel):
    """The final record of one shoe model, as read by the web app."""

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$", examples=["brand-model-6"])
    brand: str
    model: str
    version: str | None
    category: str = Field(pattern="^(trail|gravel)$")
    newer_version_id: str | None = Field(
        description="Id of a newer version of the same model in the catalogue, if any."
    )
    gender_variants: list[Gender] = Field(min_length=1)
    release_year: SourcedInt
    retail: list[RetailOffer] = Field(
        min_length=1, description="A shoe is in the catalogue only if a retailer sells it."
    )
    specs: Specs
    expert_reviews: list[ExpertReview]
    buyer_rating: BuyerRatingSummary
    criteria_scores: CriteriaScores
    terrain_scores: TerrainScores
    confidence: Confidence


class Catalog(StrictModel):
    """The whole `data/processed/shoes.json` file."""

    schema_version: str
    generated_at: dt.datetime
    scoring_config_version: str = Field(description="`version` field of scoring.yaml used.")
    shoes: list[Shoe]


class BuildMeta(StrictModel):
    """The whole `data/processed/meta.json` file, shown by the web app ("data as of...")."""

    build_date: dt.date
    generated_at: dt.datetime
    pipeline_version: str = Field(description="`version` of pyproject.toml.")
    scoring_config_version: str
    aspects_config_version: str
    shoe_count: int = Field(ge=0)
    brand_count: int = Field(ge=0)
    offer_count: int = Field(ge=0)
    expert_review_count: int = Field(ge=0)
    models_dropped: dict[str, str] = Field(description="Model id -> why it is not in shoes.json.")
    confidence_counts: dict[ConfidenceLevel, int]
    price_date_min: dt.date
    price_date_max: dt.date
    retailers: list[Retailer]
    review_sources: list[str]


# ---------------------------------------------------------------------------
# Phase 1: raw retailer listings (data/interim/retailer_listings.json)
# ---------------------------------------------------------------------------


class RetailerListing(StrictModel):
    """One product page at one retailer, as collected in phase 1 (before any matching).

    Nullable fields that are null must have an entry in `missing_reasons`, so that
    "not found" is always explained rather than silent.
    """

    retailer: Retailer
    product_url: HttpUrl
    retailer_product_id: str | None
    brand: str | None
    raw_title: str = Field(min_length=1)
    model_name: str | None = Field(
        description="Model name without colour, when the retailer provides one separately."
    )
    gender_raw: str | None = Field(description="Gender label exactly as shown by the retailer.")
    gender: Gender | None = Field(description="`gender_raw` mapped to our vocabulary, if possible.")
    price_eur: float | None = Field(gt=0)
    original_price_eur: float | None = Field(gt=0, description="Price before discount.")
    in_stock: bool | None
    rating: float | None = Field(ge=0, le=5, description="Average buyer rating on a 0-5 scale.")
    review_count: int | None = Field(ge=0)
    category_breadcrumb: list[str]
    image_url: HttpUrl | None
    attributes: dict[str, str] = Field(
        default_factory=dict, description="Short key/value facts shown by the retailer."
    )
    retrieved_at: dt.date
    missing_reasons: dict[str, str] = Field(default_factory=dict)

    @model_validator(mode="after")
    def _every_null_field_has_a_reason(self) -> Self:
        explained = (
            "retailer_product_id",
            "brand",
            "model_name",
            "gender_raw",
            "price_eur",
            "original_price_eur",
            "in_stock",
            "rating",
            "review_count",
            "image_url",
        )
        unexplained = [
            name
            for name in explained
            if getattr(self, name) is None and name not in self.missing_reasons
        ]
        if unexplained:
            raise ValueError(f"null fields without a missing_reasons entry: {unexplained}")
        return self


# ---------------------------------------------------------------------------
# Phase 2: canonical models (data/interim/catalog.json)
# ---------------------------------------------------------------------------


class VariantFlags(StrictModel):
    """Variants of one model line that we detect from titles (same model, other version)."""

    waterproof: bool = False
    gore_tex: bool = False
    wide: bool = False
    extra_wide: bool = False
    mid: bool = False
    boa: bool = False
    leather: bool = False
    insulated: bool = False
    refurbished: bool = False


class ModelOffer(StrictModel):
    """One retailer listing attached to a canonical model."""

    retailer: Retailer
    url: HttpUrl
    retailer_product_id: str | None
    raw_title: str
    title_key: str = Field(description="Key parsed from this title, before any fuzzy merge.")
    gender: Gender | None
    variant: VariantFlags
    price_eur: float | None = Field(gt=0)
    in_stock: bool | None
    rating: float | None = Field(ge=0, le=5)
    review_count: int | None = Field(ge=0)
    retrieved_at: dt.date


class CanonicalModel(StrictModel):
    """One model (brand + model + version), merged across listings and retailers."""

    id: str = Field(pattern=r"^[a-z0-9]+(-[a-z0-9]+)*$")
    key: str = Field(description="brand|model|version, e.g. 'hoka|speedgoat|6'.")
    brand: str
    model: str
    version: str | None
    category: str = Field(description="'trail' or 'gravel' (from the title).")
    gender_variants: list[Gender]
    variants: VariantFlags = Field(description="A flag is true if at least one offer has it.")
    match_confidence: str = Field(pattern="^(exact|fuzzy)$")
    is_latest_version: bool | None = Field(
        description="null when the version is unknown or the line has a single version."
    )
    is_discounted_old_version: bool
    newer_version_id: str | None
    retailers: list[Retailer]
    offers: list[ModelOffer] = Field(min_length=1)
    buyer_rating: BuyerRatingSummary
    review_flags: list[str] = Field(description="Why this model is listed in needs_review.csv.")


class InterimCatalog(StrictModel):
    """The whole data/interim/catalog.json file."""

    generated_at: dt.datetime
    listings_in: int
    models: list[CanonicalModel]


# ---------------------------------------------------------------------------
# Phase 3: manufacturer specs (data/interim/specs.json)
# ---------------------------------------------------------------------------


class LabFallback(StrictModel):
    """Separate slot for lab measurements published by a review source.

    Filled in phase 4/6 and never mixed with manufacturer data; phase 3 leaves it null.
    """

    stack_heel_mm: SourcedFloat
    stack_forefoot_mm: SourcedFloat
    lug_depth_mm: SourcedFloat


class RetailerTags(StrictModel):
    """Retailers' own classifications (shop filters), kept apart from measured specs.

    These are opinions of the shop ("Pied large", "Sentiers accidentés"), not measurements;
    phase 6 may use them only as light hints.
    """

    fit_width: SourcedStr
    terrain: SourcedStr
    cushioning_level: SourcedStr
    runner_build: SourcedStr
    distance: SourcedStr
    pronation: SourcedStr


class RetailerFallback(StrictModel):
    """SEPARATE fallback: specs shown on retailer product pages (phase 3b).

    Never mixed with manufacturer data; phase 6 uses manufacturer first, then lab
    measurements, then this, and lowers confidence when it does. Numbers are exact values
    only; the shops' filter buckets ("5-8 mm") go to the *_range fields.
    """

    weight_g: SourcedFloat = Field(description="Men's/unisex, standard version (no GTX/mid/wide).")
    weight_women_g: SourcedFloat
    drop_mm: SourcedFloat
    lug_depth_mm: SourcedFloat
    sole_height_unlabelled_mm: SourcedFloat = Field(
        description="'Hauteur de la semelle': heel or forefoot is not stated, so not a stack."
    )
    waterproof: SourcedBool = Field(description="Standard version of the model.")
    plate: SourcedPlate
    outsole_rubber: SourcedStr
    midsole_foam: SourcedStr
    drop_range: SourcedStr = Field(description="Filter bucket, e.g. '5-8 mm' (not a number).")
    weight_range: SourcedStr = Field(description="Filter bucket, e.g. 'De 251 g à 300 g'.")
    tags: RetailerTags


class ModelSpecs(StrictModel):
    """Manufacturer specs of one canonical model. Every known value quotes the page."""

    model_id: str
    brand: str
    model: str
    version: str | None
    manufacturer_url: HttpUrl | None
    manufacturer_url_missing_reason: str | None
    url_extra_words: list[str] = Field(
        default_factory=list,
        description="Words of the URL slug beyond the model name, to spot loose matches.",
    )
    retrieved_at: dt.date | None
    weight_g: SourcedFloat = Field(description="Men's (or unisex) reference size; see note.")
    weight_women_g: SourcedFloat
    stack_heel_mm: SourcedFloat
    stack_forefoot_mm: SourcedFloat
    drop_mm: SourcedFloat
    lug_depth_mm: SourcedFloat
    midsole_foam: SourcedStr
    midsole_foam_family: SourcedFoamFamily
    plate: SourcedPlate
    outsole_rubber: SourcedStr
    waterproof: SourcedBool
    upper_notes: SourcedStr
    width_options: SourcedWidthList
    release_year: SourcedInt
    lab_fallback: LabFallback
    retailer_fallback: RetailerFallback | None = Field(
        default=None, description="Specs from retailer pages; null until phase 3b has run."
    )

    @model_validator(mode="after")
    def _known_values_quote_the_page(self) -> Self:
        if (self.manufacturer_url is None) == (self.manufacturer_url_missing_reason is None):
            raise ValueError("give either manufacturer_url or manufacturer_url_missing_reason")
        values = [(name, getattr(self, name)) for name in type(self).model_fields]
        if self.retailer_fallback is not None:
            fallback = self.retailer_fallback
            values += [
                (f"retailer_fallback.{n}", getattr(fallback, n))
                for n in type(fallback).model_fields
            ]
            values += [
                (f"retailer_fallback.tags.{n}", getattr(fallback.tags, n))
                for n in type(fallback.tags).model_fields
            ]
        for name, field_value in values:
            known = isinstance(field_value, SourcedValue) and field_value.value is not None
            if known and not field_value.raw_snippet:
                raise ValueError(f"{name}: a known value needs its raw_snippet")
        return self


class InterimSpecs(StrictModel):
    """The whole data/interim/specs.json file, keyed by model id."""

    generated_at: dt.datetime
    models: dict[str, ModelSpecs]


# ---------------------------------------------------------------------------
# Phase 4: specialist reviews (data/interim/expert_reviews.json)
# ---------------------------------------------------------------------------


class MatchConfidence(StrEnum):
    """How sure we are that a review is about this exact model and version."""

    EXACT = "exact"  # URL and title name the model and its version
    VARIANT = "variant"  # same model and version, but a variant (GTX, BOA, wide...)
    MANUAL = "manual"  # ambiguous, accepted by a human in reviews_needs_review.csv


class SourceRating(StrictModel):
    """A score given by the review source, on the source's own scale."""

    label: str = Field(description="e.g. 'Our verdict', 'Gravel', 'Design'.")
    value: str = Field(description="As written: '88', 'A'.")
    scale: str = Field(description="e.g. '0-100', 'A-F'.")
    raw_snippet: Excerpt


class CollectedReview(StrictModel):
    """One specialist review attached to one catalogue model (phase 4)."""

    source: str
    url: HttpUrl
    title: str
    language: str
    date: dt.date | None = Field(description="Publication date; null if the page gives none.")
    retrieved_at: dt.date
    review_match_confidence: MatchConfidence
    match_note: str | None
    ratings: list[SourceRating]
    lab_values: dict[str, SourcedFloat] = Field(
        description="Measurements made BY THE SOURCE (not the manufacturer), e.g. stack."
    )
    conclusion_excerpt: Excerpt | None = Field(
        description="Our selection of at most 30 words from the conclusion; full text is "
        "kept only in the local cache (data/raw/reviews/)."
    )
    conclusion_heading: str | None


class InterimReviews(StrictModel):
    """The whole data/interim/expert_reviews.json file: reviews per model id."""

    generated_at: dt.datetime
    sources: list[str]
    models: dict[str, list[CollectedReview]]


# ---------------------------------------------------------------------------
# Phase 5: aspects found in review conclusions (data/interim/expert_aspects.json)
# ---------------------------------------------------------------------------


class AspectResult(StrictModel):
    """What the reviews say about one criterion, as read by the NLP step."""

    score_0_10: Score0To10 = Field(description="0 = very low, 5 = neutral, 10 = very high.")
    evidence_excerpt: Excerpt = Field(description="The sentence that most clearly mentions it.")
    source: str = Field(description="Source of the evidence sentence.")
    review_url: HttpUrl
    n_sentences: int = Field(ge=1, description="Sentences that mention the criterion.")
    n_reviews: int = Field(ge=1)


class ReviewAspects(StrictModel):
    """Aspects of one review."""

    source: str
    review_url: HttpUrl
    n_sentences_read: int
    aspects: dict[Criterion, AspectResult]


class ModelAspects(StrictModel):
    """Aspects of one model: all 8 criteria (null = no review talks about it)."""

    criteria: dict[Criterion, AspectResult | None]
    reviews: list[ReviewAspects]


class InterimAspects(StrictModel):
    """The whole data/interim/expert_aspects.json file."""

    generated_at: dt.datetime
    nlp_model: str
    nlp_model_revision: str | None
    aspects_config_version: str
    # Stage 3 (since aspects.yaml 0.3.0): "nli" with its model, or "embedding" (no model).
    direction_method: str = "embedding"
    direction_model: str | None = None
    direction_model_revision: str | None = None
    models: dict[str, ModelAspects]
