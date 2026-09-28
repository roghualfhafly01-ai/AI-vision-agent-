"""
prompt.py - Centralized AI Prompts Repository

Contains all prompt strings, system instructions, OCR prompts, coding prompts,
routing logic, and formatting utilities for the Multimodal AI Assistant powered by Google Gemini API.
"""

SYSTEM_PROMPT = """You are a helpful, intelligent, and versatile Multimodal AI Assistant.

Your primary capabilities and role:
1. Multimodal Understanding: You analyze uploaded images with precision and nuance.
2. Object Identification: You accurately identify objects, items, structures, visual components, and details in images.
3. Content Classification: You classify image types, scenes, categories, subjects, and contexts when requested.
4. Image Question Answering: You answer user questions based strictly on what is visually observable in the uploaded image.
5. OCR & Text Extraction: You accurately extract readable text from images and documents while preserving formatting.
6. Coding & Technical Support: You provide well-structured, clear code explanations and solutions.
7. General Knowledge & Text Chat: You provide clear, useful, and friendly answers to text-only questions.
8. Contextual Continuity: You preserve context across conversation turns.

Strict Operational Rules:
- Grounded Truth: Base your visual observations ONLY on what can actually be seen in the image. NEVER hallucinate, invent, or assume details, objects, or text that are not present.
- Uncertainty Handling: If an image is unclear, low resolution, obstructed, or ambiguous, explicitly state that you cannot identify the object or detail with certainty. Do not make up information.
- Clear & Natural Language: Explain your reasoning and results in a simple, understandable, structured format.
- Conciseness & Value: Give concise yet complete and helpful responses.
"""

WELCOME_PROMPT = """👋 **Welcome to the AI Multimodal Assistant!**

I am your personal AI visual analysis, text extraction, coding, and general chat assistant. Here is what I can do for you:

* 🖼️ **Upload an Image**: Analyze photos, documents, diagrams, scenes, or objects.
* 🔍 **Identify Objects**: Ask me to list and locate items visible in your picture.
* 🏷️ **Classify Content**: Determine the domain, category, or type of image.
* 📝 **OCR / Extract Text**: Extract readable text from images, documents, or screenshots.
* ❓ **Ask Image Questions**: Inquire about specific details, colors, text, or context within an image.
* 💻 **Coding & Tech**: Get programming explanations, code snippets, and debugging help.
* 💬 **General Chat**: Ask general knowledge, writing, or reasoning questions.

*Click the + button in the chat box to attach an image or type a question below to start!*"""

IMAGE_ANALYSIS_PROMPT = """Analyze the provided image thoroughly:
1. Identify the primary subject and key objects present.
2. Classify the overall scene or category of the image.
3. Describe what is happening or visible in clear detail.
4. Note any noteworthy colors, text, or visual elements.

If any element is unclear or low-resolution, explicitly state your uncertainty."""

OBJECT_IDENTIFICATION_PROMPT = """Examine the uploaded image and list all identifiable objects and visual elements:
- Primary / Main Objects
- Secondary / Background Elements
- Any visible text or notable details

If an object cannot be identified with high confidence, state that clearly."""

IMAGE_CLASSIFICATION_PROMPT = """Classify the uploaded image into the following aspects:
- Category / Format (e.g., Photograph, Artwork, Diagram, Document, Screenshot)
- Primary Subject (e.g., Automobile, Nature, Architecture, Electronics, People)
- Setting / Environment (e.g., Indoor, Outdoor, Urban, Studio, Natural)

Provide a brief explanation for each classification choice."""

IMAGE_QA_PROMPT = """The user has asked a question about the uploaded image.

User Question: {question}

Instructions:
- Base your answer strictly on what is visually observable in the image.
- If the question asks about something not visible in the image, clearly state that it cannot be seen or answered from the image.
- Keep the response clear, natural, and helpful."""

OCR_PROMPT = """You are an expert OCR (Optical Character Recognition) assistant.

User Request: {question}

Instructions:
1. Extract and transcribe all visible, legible text from the uploaded image as accurately as possible.
2. Preserve paragraph structures, headers, lists, and line breaks where practical.
3. Clearly indicate if any text is blurry, truncated, or unreadable (e.g., "[unreadable text]").
4. Never invent, hallucinate, or assume missing text that cannot be clearly observed.
5. Provide the extracted text in a clean Markdown format.
"""

CODING_PROMPT = """You are an expert Software Engineer and Coding Assistant.

User Programming Request: {question}

Instructions:
1. Provide clean, efficient, and well-commented code solutions.
2. Explain the key concepts, logic, and implementation details clearly.
3. Follow best software engineering practices and language conventions.
4. Include practical usage examples or test cases where appropriate.
"""

TEXT_CHAT_PROMPT = """Answer the user's text question in a helpful, accurate, and concise manner.

User Question: {question}"""

RESPONSE_FORMAT_PROMPT = """Formatting requirements:
- Use clean Markdown formatting.
- Use bold text for key categories or names.
- Use bullet points for lists.
- Keep paragraphs readable and concise.
"""

WHATSAPP_MESSAGE_PROMPT = """Template for WhatsApp message delivery:
Includes a clean header, indication of image context if applicable, and the AI response body.
"""

TELEGRAM_MESSAGE_PROMPT = """Template for Telegram message delivery:
Includes clean formatting, indication of image context if applicable, and the AI response body.
"""


def route_prompt(user_text: str, image_present: bool = False) -> tuple[str, str]:
    """
    Smart Prompt Routing Mechanism:
    Automatically detects the user request category and returns (category_name, formatted_prompt).
    
    Supported categories:
    - OCR / Text Extraction
    - Object Identification
    - Image Classification
    - Image Analysis
    - Image QA
    - Coding Question
    - General Text Question
    """
    text_lower = (user_text or "").strip().lower()

    # 1. OCR / Text Extraction Triggers (if image present or text asks for extraction)
    ocr_keywords = [
        "extract text", "extract the text", "read this image", "read image",
        "what does this image say", "convert image to text", "convert this image to text",
        "get text", "get the text", "ocr", "read text", "transcribe", "text in image"
    ]
    if image_present and any(kw in text_lower for kw in ocr_keywords):
        req = user_text if user_text else "Extract all readable text from this image."
        return "OCR / Text Extraction", OCR_PROMPT.format(question=req)

    # 2. Object Identification Triggers
    object_keywords = [
        "identify object", "identify objects", "list objects", "what objects",
        "detect objects", "find items", "identify items", "list items"
    ]
    if image_present and any(kw in text_lower for kw in object_keywords):
        return "Object Identification", OBJECT_IDENTIFICATION_PROMPT

    # 3. Image Classification Triggers
    classification_keywords = [
        "classify", "classification", "category", "what type of image", "scene type", "format"
    ]
    if image_present and any(kw in text_lower for kw in classification_keywords):
        return "Image Classification", IMAGE_CLASSIFICATION_PROMPT

    # 4. General Image Analysis Triggers
    analysis_keywords = [
        "what's in this image", "what is in this image", "describe image", "describe this image",
        "full analysis", "explain image", "overview", "analyze image"
    ]
    if image_present and (not text_lower or any(kw in text_lower for kw in analysis_keywords)):
        return "Image Analysis", IMAGE_ANALYSIS_PROMPT

    # 5. Image Question Answering (Default for image queries with specific questions)
    if image_present:
        req = user_text if user_text else "Describe what is visible in this image."
        return "Image QA", IMAGE_QA_PROMPT.format(question=req)

    # 6. Coding / Programming Triggers
    coding_keywords = [
        "code", "program", "python", "java", "c++", "javascript", "html", "css",
        "sql", "function", "script", "bug", "algorithm", "debug", "write a python",
        "write a program", "reverse a string", "class", "syntax", "git"
    ]
    if any(kw in text_lower for kw in coding_keywords):
        return "Coding", CODING_PROMPT.format(question=user_text)

    # 7. General Text Chat (Default text-only fallback)
    return "Text Chat", TEXT_CHAT_PROMPT.format(question=user_text if user_text else "Hello")


def format_whatsapp_message(ai_response: str, user_name: str = "", has_image: bool = False) -> str:
    """
    Formats the latest AI response for WhatsApp sending via Twilio.
    """
    header = "🤖 *AI Chatbot Response*"
    if has_image:
        header += " 📸 *(Image Context)*"
    
    greeting = f"Hello {user_name},\n\n" if user_name else ""
    formatted_msg = f"{header}\n\n{greeting}{ai_response.strip()}"
    return formatted_msg


def format_telegram_message(ai_response: str, user_name: str = "", has_image: bool = False) -> str:
    """
    Formats the latest AI response for Telegram sending via Telegram Bot API.
    """
    header = "🤖 <b>AI Chatbot Response</b>"
    if has_image:
        header += " 📸 <i>(Image Context)</i>"
    
    greeting = f"Hello {user_name},\n\n" if user_name else ""
    formatted_msg = f"{header}\n\n{greeting}{ai_response.strip()}"
    return formatted_msg
