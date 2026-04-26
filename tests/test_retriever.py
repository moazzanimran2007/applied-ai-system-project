from pawpal_system import _LocalRetriever


def test_retriever_finds_known_terms(tmp_path, monkeypatch):
    # Create a temporary assets dir with a sample file
    assets = tmp_path / "assets"
    assets.mkdir()
    file = assets / "tips.txt"
    file.write_text("Feed your pet at consistent times.\nShort walks are great for dogs.\n")

    # Point the retriever to the temp assets dir
    retriever = _LocalRetriever(assets_dir=str(assets))

    snippets = retriever.find_relevant_snippets(["feed", "walk"], top_k=2)

    assert any("Feed your pet" in s for s in snippets)
    assert any("Short walks" in s for s in snippets)


def test_retriever_returns_empty_for_no_match(tmp_path):
    assets = tmp_path / "assets"
    assets.mkdir()
    file = assets / "tips.txt"
    file.write_text("Cats like vertical spaces.\nGrooming is occasional.\n")

    retriever = _LocalRetriever(assets_dir=str(assets))

    snippets = retriever.find_relevant_snippets(["medication"], top_k=2)

    assert snippets == []
