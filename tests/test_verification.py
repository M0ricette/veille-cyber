from veille.verification import verifier


def une(paragraphes, sources=("S1",)):
    return {"titre": "Fuite massive", "chapo": "Un opérateur touché.", "paragraphes": list(paragraphes), "sources": list(sources)}


def breve(texte, source="S3", rubrique="Géopolitique et régulation"):
    return {"rubrique": rubrique, "titre": "Sanctions", "texte": texte, "source": source}


def test_journal_correct_accepte(catalogue):
    lus = {"S1": "Fuite de 3 000 000 fiches. CVE-2026-11111."}
    data = {"accroche": "Une fuite majeure", "une": une(["3 000 000 fiches ont fuité [S1].", "La faille CVE-2026-11111 est en cause [S1]."]),
            "breves": [breve("L'UE vise six individus.")], "notion": {"titre": "Le credential stuffing", "explication": "Réutiliser des identifiants volés.", "source": "S1"}}
    journal, problemes = verifier(data, {a.id: a for a in catalogue}, lus)
    assert problemes == []
    assert journal.une and len(journal.breves) == 1 and journal.notion


def test_une_sans_lecture_complete_refusee(catalogue):
    data = {"une": une(["Un pirate revendique la fuite [S1]."]), "breves": []}
    journal, problemes = verifier(data, {a.id: a for a in catalogue}, lus={})
    assert journal.une is None
    assert any("lu en entier" in p for p in problemes)


def test_paragraphe_sans_source_refuse(catalogue):
    data = {"une": une(["Phrase sourcée [S1].", "Phrase sans source."]), "breves": []}
    _, problemes = verifier(data, {a.id: a for a in catalogue}, {"S1": "texte"})
    assert any("paragraphe 2" in p for p in problemes)


def test_nombre_invente_refuse_et_format_different_accepte(catalogue):
    cat = {a.id: a for a in catalogue}
    # La source écrit 3,000,000 à l'anglaise : 3 000 000 à la française passe.
    ok, _ = verifier({"breves": [breve("3 000 000 fiches.", "S1", "Fuites et attaques")]}, cat, {})
    assert len(ok.breves) == 1
    ko, problemes = verifier({"breves": [breve("4 500 000 fiches.", "S1", "Fuites et attaques")]}, cat, {})
    assert ko.breves == [] and "4 500 000" in problemes[0]


def test_annee_non_signalee_comme_nombre(catalogue):
    journal, problemes = verifier({"breves": [breve("Décision prise en 2026.")]}, {a.id: a for a in catalogue}, {})
    assert problemes == []


def test_cve_inventee_refusee(catalogue):
    _, problemes = verifier({"breves": [breve("Lié à CVE-2026-99999.")]}, {a.id: a for a in catalogue}, {})
    assert "CVE-2026-99999" in problemes[0]


def test_source_inconnue_refusee(catalogue):
    journal, problemes = verifier({"breves": [breve("Texte.", "S42")]}, {a.id: a for a in catalogue}, {})
    assert journal.breves == [] and "S42" in problemes[0]


def test_rubrique_inventee_remplacee_par_celle_de_la_source(catalogue):
    journal, _ = verifier({"breves": [breve("L'UE vise six individus.", rubrique="Divers")]}, {a.id: a for a in catalogue}, {})
    assert journal.breves[0].rubrique == "Géopolitique et régulation"
