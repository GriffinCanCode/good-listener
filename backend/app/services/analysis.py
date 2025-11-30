class AnalysisService:
    def analyze_text(self, text: str) -> str:
        """
        Analyzes the extracted text to provide insights.
        Placeholder for LLM integration.
        """
        if not text:
            return ""
            
        # Simple keyword matching for now
        keywords = ["error", "fail", "deadline", "urgent", "meeting"]
        found = [k for k in keywords if k in text.lower()]
        
        if found:
            return f"Detected urgent keywords: {', '.join(found)}. You might want to check this."
        
        return ""

