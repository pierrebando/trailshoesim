"""Phase 5: sentence splitting, aspect matching rules (fake models) and the real models
on the hand-written EN/FR check set (skipped when the models are not downloaded)."""

from dataclasses import replace
from pathlib import Path

import numpy as np
import pytest
import yaml

from pipeline.nlp.aspects import AspectMatcher, aggregate, load_config, score_class
from pipeline.nlp.evaluate import metrics, ranks, spearman
from pipeline.nlp.sentences import review_sentences, split_sentences

CHECK_SET = yaml.safe_load(
    (Path(__file__).parent / "fixtures" / "nlp" / "sentences.yaml").read_text(encoding="utf-8")
)

# --- stage 1 -------------------------------------------------------------------


def test_split_english_and_french() -> None:
    text = (
        "SAM : The Peregrine 16 weighs 9.5 oz. It is stable vs. the 15! "
        "Elle accroche bien. Le drop est de 4 mm, env. 2 mm de moins."
    )
    assert split_sentences(text) == [
        "The Peregrine 16 weighs 9.5 oz.",
        "It is stable vs. the 15!",
        "Elle accroche bien.",
        "Le drop est de 4 mm, env. 2 mm de moins.",
    ]


def test_pros_and_cons_are_sentences_even_when_short() -> None:
    sentences = review_sentences("The shoe grips well on rock.", ["Stable ride"], ["Heavy"])
    assert sentences == ["The shoe grips well on rock.", "Stable ride", "Heavy"]


# --- stages 2-3 with a fake model ---------------------------------------------------


class KeywordEmbedder:
    """Fake model: one dimension per keyword, so similarities are predictable."""

    WORDS = ("soft", "firm", "grip", "slip", "light", "heavy", "price", "zzz")

    def encode(self, texts: list[str]) -> np.ndarray:
        rows = []
        for text in texts:
            vector = np.array([1.0 if w in text.lower() else 0.0 for w in self.WORDS] + [0.0])
            if not vector.any():
                vector[-1] = 1.0  # text with no keyword: its own direction, close to nothing
            rows.append(vector / np.linalg.norm(vector))
        return np.array(rows)


def fake_config():
    config = load_config()
    empty = {"high": ["zzz"], "low": ["zzz"]}
    descriptors = {c: empty for c in config.descriptors}
    descriptors["cushioning"] = {"high": ["soft"], "low": ["firm"]}
    descriptors["grip"] = {"high": ["grip"], "low": ["slip"]}
    descriptors["lightness"] = {"high": ["light"], "low": ["heavy"]}
    thresholds = {**config.thresholds, "mention_min_similarity": 0.55, "background_margin": 0.05}
    return replace(
        config,
        descriptors=descriptors,
        background=["price"],
        thresholds=thresholds,
        direction_method="embedding",
    )


class FakeNLI:
    """Fake NLI: entails a hypothesis that shares a word with the sentence."""

    def probabilities(self, pairs: list[tuple[str, str]]) -> np.ndarray:
        rows = []
        for premise, hypothesis in pairs:
            shared = set(premise.lower().split()) & set(hypothesis.lower().rstrip(".").split())
            rows.append([0.9, 0.1, 0.0] if shared - {"the", "shoe", "is"} else [0.0, 0.1, 0.9])
        return np.array(rows)


def test_mentions_direction_and_background() -> None:
    matcher = AspectMatcher(KeywordEmbedder(), fake_config())
    found = {(m.sentence, m.criterion): m for m in matcher.match(
        ["very soft shoe", "it is heavy", "great grip", "the price is fair", "nothing here"]
    )}  # fmt: skip
    assert found[("very soft shoe", "cushioning")].score == 10.0
    assert found[("it is heavy", "lightness")].score == 0.0
    assert found[("great grip", "grip")].score == 10.0
    assert not any(sentence == "the price is fair" for sentence, _ in found)  # background
    assert not any(sentence == "nothing here" for sentence, _ in found)


def test_aggregate_weights_clear_sentences_more_and_keeps_best_evidence() -> None:
    config = fake_config()
    matcher = AspectMatcher(KeywordEmbedder(), config)
    result = aggregate(matcher.match(["very soft", "soft but firm"]), config)["cushioning"]
    assert result["n_sentences"] == 2
    assert result["evidence"] == "very soft"
    assert 5.0 < result["score_0_10"] <= 10.0


def test_nli_direction_overrides_the_embedding_one() -> None:
    hypotheses = {
        c: {"high": "The shoe is zzz.", "low": "The shoe is zzz."}
        for c in fake_config().descriptors
    }
    hypotheses["lightness"] = {"high": "The shoe is light.", "low": "The shoe is heavy."}
    config = replace(fake_config(), direction_method="nli", hypotheses=hypotheses)
    with pytest.raises(ValueError):
        AspectMatcher(KeywordEmbedder(), config)  # NLI method without an NLI model
    (mention,) = AspectMatcher(KeywordEmbedder(), config, FakeNLI()).match(["light"])
    # high entailed (0.9 - 0), low contradicted (0 - 0.9): d = (0.9 + 0.9) / 2 = 0.9
    assert mention.criterion == "lightness"
    assert mention.direction == pytest.approx(0.9)
    assert mention.score == 9.5


def test_score_classes() -> None:
    config = load_config()
    assert [score_class(s, config) for s in (None, 2.0, 5.0, 8.0)] == [
        "not mentioned",
        "low",
        "medium",
        "high",
    ]


# --- evaluation helpers ---------------------------------------------------------------


def test_spearman_with_ties_and_metrics() -> None:
    assert ranks([3.0, 1.0, 3.0]) == [2.5, 1.0, 2.5]
    assert spearman([1.0, 2.0, 3.0], [0, 1, 2]) == pytest.approx(1.0)
    assert spearman([3.0, 2.0, 1.0], [0, 1, 2]) == pytest.approx(-1.0)
    assert spearman([1.0, 1.0, 1.0], [0, 1, 2]) is None  # no variation: undefined
    pairs = [
        {"label": "high", "score": 8.0, "predicted": "high"},
        {"label": "low", "score": 6.5, "predicted": "high"},
        {"label": "not mentioned", "score": 5.0, "predicted": "medium"},
        {"label": "medium", "score": None, "predicted": "not mentioned"},
    ]
    result = metrics(pairs)
    assert (result["n_mentioned"], result["n_found"], result["n_false"]) == (3, 2, 1)
    assert result["accuracy"] == 0.5
    assert result["confusion"]["medium"]["not mentioned"] == 1


# --- the real models on the hand-written check set (slow, needs the models) ---------


def _real_matcher():
    pytest.importorskip("sentence_transformers")
    from huggingface_hub import try_to_load_from_cache

    config = load_config()
    models = [(config.model_name, config.model_revision)]
    models.append((config.nli_model_name, config.nli_model_revision))
    for name, revision in models:
        if not isinstance(try_to_load_from_cache(name, "config.json", revision=revision), str):
            pytest.skip(f"{name} not downloaded (run python -m pipeline.nlp once)")
    from pipeline.nlp.aspects import SentenceTransformerEmbedder, TransformersNLI

    return AspectMatcher(
        SentenceTransformerEmbedder(config.model_name, config.model_revision),
        config,
        TransformersNLI(config.nli_model_name, config.nli_model_revision),
    )


def test_real_model_on_check_set() -> None:
    matcher = _real_matcher()
    mentions = matcher.match([item["text"] for item in CHECK_SET])
    by_sentence: dict[str, dict] = {}
    for mention in mentions:
        by_sentence.setdefault(mention.sentence, {})[mention.criterion] = mention
    on_topic = [i for i in CHECK_SET if i["criterion"]]
    found = [i for i in on_topic if i["criterion"] in by_sentence.get(i["text"], {})]
    right_direction = [
        i for i in found
        if (by_sentence[i["text"]][i["criterion"]].score > 5) == (i["pole"] == "high")
    ]  # fmt: skip
    off_topic = [i for i in CHECK_SET if not i["criterion"] and i["text"] in by_sentence]
    assert len(found) >= 27, f"found {len(found)}/32 mentions"
    assert len(right_direction) >= len(found) - 1
    assert len(off_topic) <= 1, [i["text"] for i in off_topic]
