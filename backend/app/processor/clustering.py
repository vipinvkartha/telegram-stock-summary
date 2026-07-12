from collections import defaultdict
from datetime import date

from app.processor.pipeline_types import MessageCluster, ProcessedMessage


def cluster_by_stock_and_date(messages: list[ProcessedMessage]) -> list[MessageCluster]:
    buckets: dict[tuple[str, date], list[ProcessedMessage]] = defaultdict(list)
    for message in messages:
        for mention in message.mentions:
            buckets[(mention.ticker, message.timestamp.date())].append(message)

    clusters = [
        MessageCluster(ticker=ticker, cluster_date=cluster_date, messages=items)
        for (ticker, cluster_date), items in buckets.items()
    ]
    return sorted(clusters, key=lambda cluster: (-len(cluster.messages), cluster.ticker))
