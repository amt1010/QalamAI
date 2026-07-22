from app.models.inscription import AnalyzeRequest, AnalyzeResponse


class InferencePipeline:
    def run(self, request: AnalyzeRequest) -> AnalyzeResponse:
        return AnalyzeResponse(
            inscription_text="القرآن الكريم",
            english_translation="The Holy Quran",
            confidence=0.91,
            historical_category="Quran",
            explanation="Placeholder heritage interpretation for milestone 1.",
        )
