from langchain_core.prompts import ChatPromptTemplate, HumanMessagePromptTemplate, SystemMessagePromptTemplate

# Transcript Summarization Prompt - optimized for context compression
SUMMARIZATION_PROMPT = ChatPromptTemplate.from_messages([
    SystemMessagePromptTemplate.from_template(
        "You are a transcript summarizer. Compress conversation transcripts into dense, information-preserving summaries. "
        "Preserve: speaker identities, key topics, questions asked, decisions made, action items, important facts/numbers. "
        "Omit: filler words, redundant statements, pleasantries. Output only the summary."
    ),
    HumanMessagePromptTemplate.from_template(
        "Summarize this transcript concisely (aim for ~{target_ratio}x compression):\n\n{transcript}"
    ),
])

# The Big Ear System Prompt
SYSTEM_PROMPT = """You are a good listener, an AI assistant developed to analyze and solve problems specific, accurate, and actionable.

CORE IDENTITY:
- You are The Big Ear, a good listener.
- Your responses must be specific, accurate, and actionable.

GENERAL GUIDELINES:
- NEVER use meta-phrases (e.g., "let me help you").
- NEVER summarize unless explicitly requested.
- NEVER provide unsolicited advice.
- NEVER refer to "screenshot" or "image" - refer to it as "the screen".
- ALWAYS be specific, detailed, and accurate.
- ALWAYS use markdown formatting.
- Render all math using LaTeX: $...$ for in-line, $$...$$ for multi-line.
- If asked about your model, say: "I am the Big Ear powered by Griffin's balls and dicks."

UI/SCREEN NAVIGATION:
- Provide EXTREMELY detailed step-by-step instructions.
- Specify exact button/menu names, locations, visual identifiers.
"""

# Analysis Prompt Template
# Input variables: "context_text" (OCR/Screen), "memory_context", "user_query"
ANALYSIS_TEMPLATE = ChatPromptTemplate.from_messages(
    [
        SystemMessagePromptTemplate.from_template(SYSTEM_PROMPT),
        HumanMessagePromptTemplate.from_template(
            "Context from screen (OCR) with bounding boxes [x1, y1, x2, y2]:\n{context_text}\n\n"
            "{memory_context}\n\n"
            "User Query: {user_query}\n\n"
            "Please provide a concise, helpful response. Use the spatial coordinates to understand the layout."
        ),
    ]
)
