from forex_lab.discovery.score import evaluate, auto_duplicates

BASE = {"id": "T", "nom": "t", "famille": "f", "sources": [], "regles": "", "resultats_publies": "", "limites": "",
        "scores": {k: 3 for k in "SHCRIFP"}, "compatibilite": {"horizon": "", "paires": "", "donnees": ""},
        "doublon_de": None, "mots_cles": [["tokyo", "fix"]]}


def test_score_and_penalties():
    f = dict(BASE, penalites={"effet_en_declin": True, "hors_paires": True})
    r = evaluate(f, {})
    assert (r["brut"], r["score"], r["niveau"], r["exclue"]) == (21, 16, "solide", False)


def test_auto_duplicate_needs_all_words_and_fait_nouveau_overrides():
    texts = {"ECHECS.md": "vente apres le fix de tokyo"}
    assert auto_duplicates(BASE, texts)
    assert evaluate(BASE, texts)["exclue"]
    assert not evaluate(dict(BASE, fait_nouveau="x"), texts)["exclue"]
    assert not auto_duplicates(dict(BASE, mots_cles=[["tokyo", "londres"]]), texts)


def test_manual_duplicate_and_invalid_score():
    assert evaluate(dict(BASE, doublon_de="V3-H1"), {})["exclue"]
    import pytest
    with pytest.raises(ValueError):
        evaluate(dict(BASE, scores={**BASE["scores"], "S": 4}), {})
