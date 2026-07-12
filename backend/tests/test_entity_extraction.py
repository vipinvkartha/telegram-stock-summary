from app.processor.entity_extraction import extract_stock_mentions
from app.processor.pipeline import ProcessingPipeline


def test_extracts_tickers_and_company_names() -> None:
    mentions = extract_stock_mentions("NVIDIA is running again, but $TSLA looks mixed.")
    tickers = {mention.ticker for mention in mentions}

    assert tickers == {"NVDA", "TSLA"}
    assert next(mention for mention in mentions if mention.ticker == "NVDA").company_name


def test_ignores_common_market_uppercase_words() -> None:
    mentions = extract_stock_mentions("CPI and FOMC are moving AI stocks, but $PLTR is the trade.")

    assert {mention.ticker for mention in mentions} == {"PLTR"}


def test_pipeline_deduplicates_and_clusters(raw_message_factory) -> None:
    messages = [
        raw_message_factory(1, "NVDA earnings beat expectations"),
        raw_message_factory(2, "NVDA earnings beat expectations"),
        raw_message_factory(3, "Tesla downgrade risk is all over chat"),
    ]

    clusters = ProcessingPipeline().process(messages)

    assert [cluster.ticker for cluster in clusters] == ["NVDA", "TSLA"]
    assert len(clusters[0].messages) == 1
