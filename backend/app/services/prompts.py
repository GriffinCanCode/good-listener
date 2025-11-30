
def get_monitor_prompt(transcript: str, screen_ctx: str) -> str:
    return (
        f'User conversation:\nTranscript: "{transcript}"\n'
        f'Screen Context: "{screen_ctx}"\n\n'
        'If this is a question/lookup about the screen, answer it.\n'
        'If the screen is empty but asked about, describe visuals.\n'
        'If just chatter, reply "NO_RESPONSE".'
    )

def get_analysis_prompt(ocr_ctx: str, memory_ctx: str, query: str) -> str:
    ocr_text = ocr_ctx[:5000] if ocr_ctx else "No text detected via OCR."
    user_q = query or "Analyze this screen."
    return (
        f"Context from screen (OCR) with bounding boxes [x1, y1, x2, y2]:\n{ocr_text}\n\n"
        f"{memory_ctx}\n\nUser Query: {user_q}\n\n"
        "Please provide a concise, helpful response. Use the spatial coordinates to understand the layout."
    )

