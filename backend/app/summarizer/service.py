from app.ai import LLMProvider, SummaryResult
from app.processor import MessageCluster


class SummarizerService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def summarize(self, cluster: MessageCluster) -> SummaryResult:
        return await self.provider.summarize(cluster)
