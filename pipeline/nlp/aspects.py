"""Stages 2 and 3: which criteria a sentence talks about, and in which direction.

Stage 2 (aspect matching): cosine similarity between the sentence vector and each
criterion's descriptor vectors (pipeline/config/aspects.yaml). A criterion is mentioned
if its best similarity passes `mention_min_similarity`, is close to the sentence's best
criterion (`mention_max_gap_to_best`) and clearly beats the "background" descriptors
(price, colour, test period...) by `background_margin`.

Stage 3 (direction), method "nli" (default): a zero-shot NLI model reads the sentence as
a premise and two hypotheses per criterion ("The shoe is light." / "The shoe is heavy.").
d = ((P(entail high) - P(contradict high)) - (P(entail low) - P(contradict low))) / 2,
score = 5 + 5 * d. Method "embedding" (the 0.2.0 baseline): d = best similarity to a HIGH
descriptor - best to a LOW one, score = 5 + 5 * clip(d / polarity_scale, -1, 1).

Embeddings are similar for "lacks cushioning" and "very cushioned" (same topic), which is
why the direction moved to NLI, a model trained to tell implication from contradiction.

Both models are hidden behind small protocols (`Embedder`, `EntailmentModel`), so tests
can use fake ones.
"""

from dataclasses import dataclass
from functools import cache
from pathlib import Path
from typing import Protocol

import numpy as np
import yaml

from pipeline.models import Criterion

ASPECTS_PATH = Path(__file__).resolve().parents[1] / "config" / "aspects.yaml"


class Embedder(Protocol):
    """Anything that turns texts into L2-normalised vectors (one row per text)."""

    def encode(self, texts: list[str]) -> np.ndarray:
        """Vectors of `texts`, shape (len(texts), dim), each of length 1."""
        ...


class EntailmentModel(Protocol):
    """Anything that gives NLI probabilities for (premise, hypothesis) pairs."""

    def probabilities(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        """Shape (len(pairs), 3): P(entailment), P(neutral), P(contradiction) per pair."""
        ...


class SentenceTransformerEmbedder:
    """The real model (Hugging Face, runs on CPU)."""

    def __init__(self, name: str, revision: str | None = None) -> None:
        """Load the model (downloaded once to the Hugging Face cache, then offline)."""
        from sentence_transformers import SentenceTransformer  # heavy import, only here

        self.model = SentenceTransformer(name, revision=revision, device="cpu")

    def encode(self, texts: list[str]) -> np.ndarray:
        """Normalised embeddings."""
        return self.model.encode(texts, normalize_embeddings=True, show_progress_bar=False)


class TransformersNLI:
    """The real NLI model (Hugging Face transformers, CPU)."""

    BATCH = 32

    def __init__(self, name: str, revision: str | None = None) -> None:
        """Load the model (downloaded once to the Hugging Face cache, then offline)."""
        import torch  # heavy imports, only here
        from transformers import AutoModelForSequenceClassification, AutoTokenizer

        self.torch = torch
        self.tokenizer = AutoTokenizer.from_pretrained(name, revision=revision)
        self.model = AutoModelForSequenceClassification.from_pretrained(name, revision=revision)
        self.model.eval()
        # Column order of the model's output, read from its config rather than assumed.
        labels = {label.lower(): index for index, label in self.model.config.id2label.items()}
        self.columns = [labels["entailment"], labels["neutral"], labels["contradiction"]]

    def probabilities(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        """NLI probabilities, in batches."""
        rows = []
        for start in range(0, len(pairs), self.BATCH):
            batch = pairs[start : start + self.BATCH]
            encoded = self.tokenizer(
                [premise for premise, _ in batch],
                [hypothesis for _, hypothesis in batch],
                truncation=True,
                padding=True,
                return_tensors="pt",
            )
            with self.torch.no_grad():
                logits = self.model(**encoded).logits
            rows.append(self.torch.softmax(logits, dim=-1).numpy()[:, self.columns])
        return np.concatenate(rows) if rows else np.zeros((0, 3))


@dataclass(frozen=True)
class AspectConfig:
    """The contents of aspects.yaml."""

    version: str
    model_name: str
    model_revision: str | None
    thresholds: dict[str, float]
    min_sentence_weight: float
    use_pros_cons: bool
    background: list[str]
    descriptors: dict[str, dict[str, list[str]]]
    direction_method: str = "embedding"  # "nli" or "embedding"
    nli_model_name: str | None = None
    nli_model_revision: str | None = None
    hypotheses: dict[str, dict[str, str]] | None = None


@cache
def load_config(path: Path = ASPECTS_PATH) -> AspectConfig:
    """Read aspects.yaml once."""
    raw = yaml.safe_load(path.read_text(encoding="utf-8"))
    direction = raw.get("direction", {"method": "embedding"})
    return AspectConfig(
        version=raw["version"],
        model_name=raw["model"]["name"],
        model_revision=raw["model"].get("revision"),
        thresholds=raw["thresholds"],
        min_sentence_weight=raw["aggregation"]["min_sentence_weight"],
        use_pros_cons=raw["use_pros_cons"],
        background=raw.get("background", []),
        descriptors=raw["descriptors"],
        direction_method=direction["method"],
        nli_model_name=direction.get("nli_model", {}).get("name"),
        nli_model_revision=direction.get("nli_model", {}).get("revision"),
        hypotheses=direction.get("hypotheses"),
    )


@dataclass(frozen=True)
class SentenceAspect:
    """One (sentence, criterion) pair that the model considers a mention."""

    sentence: str
    criterion: str
    relevance: float  # best similarity to any descriptor of the criterion
    direction: float  # d, between -1 (clearly low) and 1 (clearly high)
    score: float  # 0-10


class AspectMatcher:
    """Scores sentences against the descriptors; descriptor vectors are computed once."""

    def __init__(
        self, embedder: Embedder, config: AspectConfig, nli: EntailmentModel | None = None
    ) -> None:
        """Embed every descriptor of every criterion and pole."""
        if config.direction_method == "nli" and nli is None:
            raise ValueError('direction.method is "nli" but no NLI model was given')
        self.embedder = embedder
        self.config = config
        self.nli = nli
        self.vectors: dict[tuple[str, str], np.ndarray] = {}
        for criterion in Criterion:
            for pole in ("high", "low"):
                phrases = config.descriptors[criterion.value][pole]
                self.vectors[(criterion.value, pole)] = embedder.encode(phrases)
        self.background = embedder.encode(config.background) if config.background else None

    def score_direction(self, direction: float) -> float:
        """Map an embedding d to 0-10 (5 = neutral)."""
        thresholds = self.config.thresholds
        if abs(direction) < thresholds["neutral_band"]:
            return 5.0
        scaled = max(-1.0, min(1.0, direction / thresholds["polarity_scale"]))
        return round(5 + 5 * scaled, 2)

    def match(self, sentences: list[str]) -> list[SentenceAspect]:
        """Every criterion mention in the sentences."""
        if not sentences:
            return []
        thresholds = self.config.thresholds
        vectors = self.embedder.encode(sentences)
        best = {
            key: (vectors @ descriptor.T).max(axis=1) for key, descriptor in self.vectors.items()
        }
        criteria = [c.value for c in Criterion]
        relevance = np.stack(
            [np.maximum(best[(c, "high")], best[(c, "low")]) for c in criteria], axis=1
        )
        if self.background is not None:
            background = (vectors @ self.background.T).max(axis=1)
        else:
            background = np.full(len(sentences), -1.0)
        found: list[tuple[str, str, float, float]] = []  # sentence, criterion, relevance, d
        for row, sentence in enumerate(sentences):
            top = relevance[row].max()
            for column, criterion in enumerate(criteria):
                value = float(relevance[row, column])
                if value < thresholds["mention_min_similarity"]:
                    continue
                if value < top - thresholds["mention_max_gap_to_best"]:
                    continue
                if value < background[row] + thresholds.get("background_margin", 0.0):
                    continue  # closer to price/colour/test-period talk than to the criterion
                direction = float(best[(criterion, "high")][row] - best[(criterion, "low")][row])
                found.append((sentence, criterion, value, direction))
        if self.config.direction_method == "nli":
            return self._nli_directions(found)
        return [
            SentenceAspect(sentence, criterion, value, d, self.score_direction(d))
            for sentence, criterion, value, d in found
        ]

    def _nli_directions(self, found: list[tuple[str, str, float, float]]) -> list[SentenceAspect]:
        """Replace the embedding direction of each mention by the NLI one."""
        pairs = []
        for sentence, criterion, _, _ in found:
            hypotheses = self.config.hypotheses[criterion]
            pairs += [(sentence, hypotheses["high"]), (sentence, hypotheses["low"])]
        probabilities = self.nli.probabilities(pairs) if pairs else np.zeros((0, 3))
        mentions = []
        for index, (sentence, criterion, value, _) in enumerate(found):
            high, low = probabilities[2 * index], probabilities[2 * index + 1]
            d = float(((high[0] - high[2]) - (low[0] - low[2])) / 2)
            mentions.append(SentenceAspect(sentence, criterion, value, d, round(5 + 5 * d, 2)))
        return mentions


def aggregate(mentions: list[SentenceAspect], config: AspectConfig) -> dict[str, dict]:
    """Per criterion: weighted mean score, best evidence sentence, number of sentences.

    The weight of a sentence is how far its similarity is above the mention threshold, so
    sentences that clearly talk about the criterion count more.
    """
    threshold = config.thresholds["mention_min_similarity"]
    results: dict[str, dict] = {}
    for criterion in {m.criterion for m in mentions}:
        found = [m for m in mentions if m.criterion == criterion]
        weights = [max(m.relevance - threshold, config.min_sentence_weight) for m in found]
        score = sum(w * m.score for w, m in zip(weights, found, strict=True)) / sum(weights)
        evidence = max(found, key=lambda m: m.relevance)
        results[criterion] = {
            "score_0_10": round(score, 2),
            "evidence": evidence.sentence,
            "relevance": round(evidence.relevance, 3),
            "n_sentences": len(found),
        }
    return results


def score_class(score: float | None, config: AspectConfig) -> str:
    """'low' / 'medium' / 'high' / 'not mentioned', for evaluation against the labels."""
    if score is None:
        return "not mentioned"
    if score <= config.thresholds["class_low_max"]:
        return "low"
    if score >= config.thresholds["class_high_min"]:
        return "high"
    return "medium"
