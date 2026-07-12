from app.processor.pipeline_types import MessageCluster, ProcessedMessage

KEYWORD_WEIGHTS = {
    "earnings": 4.0,
    "guidance": 4.0,
    "revenue": 2.0,
    "eps": 2.0,
    "insider": 3.0,
    "upgrade": 3.0,
    "downgrade": 3.0,
    "sec": 2.5,
    "lawsuit": 2.5,
    "regulatory": 2.5,
    "fed": 2.0,
    "inflation": 2.0,
    "cpi": 2.0,
    "rate cut": 2.0,
    "merger": 3.0,
    "acquisition": 3.0,
}


def score_message(message: ProcessedMessage) -> float:
    text = message.normalized_text.lower()
    score = 1.0
    for keyword, weight in KEYWORD_WEIGHTS.items():
        if keyword in text:
            score += weight
    score += min(len(text) / 500, 1.5)
    return score


def rank_cluster(cluster: MessageCluster) -> MessageCluster:
    ranked = sorted(cluster.messages, key=score_message, reverse=True)
    score = sum(score_message(message) for message in ranked)
    return cluster.model_copy(update={"messages": ranked, "importance_score": score})


def rank_clusters(clusters: list[MessageCluster]) -> list[MessageCluster]:
    ranked = [rank_cluster(cluster) for cluster in clusters]
    return sorted(ranked, key=lambda cluster: cluster.importance_score, reverse=True)
