from app.ai import AnalysisResult, LLMProvider, SummaryResult


class AnalyzerService:
    def __init__(self, provider: LLMProvider) -> None:
        self.provider = provider

    async def analyze(self, summary: SummaryResult) -> AnalysisResult:
        return await self.provider.analyze(summary)
