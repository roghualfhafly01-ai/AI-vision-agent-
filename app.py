import streamlit as st
from PIL import Image
import requests
import io
import os

import prompt

# Set page configuration
st.set_page_config(
    page_title="AI Multimodal Chatbot",
    page_icon="🤖",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Helper function to get secret safely
def get_secret(key_name: str, default: str = "") -> str:
    """Helper to safely fetch secret values without leaking or raising errors."""
    try:
        return st.secrets.get(key_name, default)
    except Exception:
        return default


# Initialize Session State
if "user_info" not in st.session_state:
    st.session_state.user_info = {"name": "", "phone": "", "submitted": False}

if "messages" not in st.session_state:
    st.session_state.messages = []

if "uploaded_image" not in st.session_state:
    st.session_state.uploaded_image = None

if "telegram_chat_id" not in st.session_state:
    st.session_state.telegram_chat_id = get_secret("TELEGRAM_CHAT_ID", "")


def get_gemini_api_key() -> str:
    """Fetches and validates the Gemini API key from secrets."""
    key = get_secret("GEMINI_API_KEY", "")
    if not key or key == "YOUR_GEMINI_API_KEY":
        return ""
    return key


def build_conversation_context(messages: list, max_turns: int = 10) -> str:
    """
    Phase 1 Feature: Conversation Memory
    Constructs a clean text context from recent conversation turns.
    Limits context to recent turns to keep memory relevant and prevent window inflation.
    """
    if not messages:
        return ""

    recent_messages = messages[-max_turns:]
    history_lines = []
    for msg in recent_messages:
        role_label = "User" if msg["role"] == "user" else "Assistant"
        content = msg.get("content", "").strip()
        if content:
            history_lines.append(f"{role_label}: {content}")

    if history_lines:
        return "Previous Conversation History:\n" + "\n".join(history_lines) + "\n\nCurrent Request:"
    return ""


def call_gemini_api(prompt_text: str, image: Image.Image = None, conversation_context: str = "", chosen_model: str = None) -> tuple[bool, str]:
    """
    Calls the Google Gemini API with multimodal input (text + optional image) and conversation context.
    Prioritizes user selected model with fallback list to ensure high performance and reliability.
    """
    api_key = get_gemini_api_key()
    if not api_key:
        return False, "⚠️ **Gemini API Key missing or unconfigured.** Please set `GEMINI_API_KEY` in `.streamlit/secrets.toml`."

    candidate_models = ["gemini-3.8-flash", "gemini-3.6-flash", "gemini-flash-latest"]
    if chosen_model and chosen_model in candidate_models:
        candidate_models.remove(chosen_model)
        candidate_models.insert(0, chosen_model)

    # Combine conversation context if present
    full_prompt_text = prompt_text
    if conversation_context.strip():
        full_prompt_text = f"{conversation_context.strip()}\n\n{prompt_text}"

    # Try modern google-genai SDK first
    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        contents = []
        if image:
            contents.append(image)
        contents.append(full_prompt_text)

        config = types.GenerateContentConfig(
            system_instruction=prompt.SYSTEM_PROMPT
        )

        last_error = None
        for model_name in candidate_models:
            try:
                # 1. Try client.interactions.create if no image present
                if not image and hasattr(client, "interactions"):
                    try:
                        interaction = client.interactions.create(
                            model=model_name,
                            input=full_prompt_text
                        )
                        if interaction and hasattr(interaction, "output_text") and interaction.output_text:
                            return True, interaction.output_text
                    except Exception:
                        pass

                # 2. Try client.models.generate_content for multimodal / text requests
                response = client.models.generate_content(
                    model=model_name,
                    contents=contents,
                    config=config
                )
                if response and hasattr(response, "text") and response.text:
                    return True, response.text
            except Exception as ex:
                last_error = ex
                continue

        if last_error:
            raise last_error

    except ImportError:
        # Fallback to google-generativeai SDK
        try:
            import google.generativeai as genai

            genai.configure(api_key=api_key)
            system_instruction = prompt.SYSTEM_PROMPT

            content_parts = []
            if image:
                content_parts.append(image)
            content_parts.append(full_prompt_text)

            last_error = None
            for model_name in candidate_models:
                try:
                    model = genai.GenerativeModel(
                        model_name=model_name,
                        system_instruction=system_instruction
                    )
                    response = model.generate_content(content_parts)
                    if response and hasattr(response, "text") and response.text:
                        return True, response.text
                except Exception as ex:
                    last_error = ex
                    continue

            if last_error:
                raise last_error

        except Exception as e:
            err_msg = str(e)
            if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg:
                return False, "⚠️ **Invalid Gemini API Key.** Please verify your key in `.streamlit/secrets.toml`."
            elif "ResourceExhausted" in err_msg or "429" in err_msg:
                return False, "⚠️ **Quota Limit Exceeded.** You have hit the Gemini API rate limit. Please wait a moment and try again."
            else:
                return False, f"⚠️ **Gemini API Error:** {err_msg}"
    except Exception as e:
        err_msg = str(e)
        if "API_KEY_INVALID" in err_msg or "API key not valid" in err_msg or "INVALID_ARGUMENT" in err_msg:
            return False, "⚠️ **Invalid Gemini API Key.** Please verify your key in `.streamlit/secrets.toml`."
        elif "ResourceExhausted" in err_msg or "429" in err_msg:
            return False, "⚠️ **Quota Limit Exceeded.** You have hit the Gemini API rate limit. Please wait a moment and try again."
        else:
            return False, f"⚠️ **Gemini API Error:** {err_msg}"


def send_to_whatsapp(message: str, phone_number: str) -> tuple[bool, str]:
    """
    Sends a WhatsApp message using Twilio's ContentSid-based Content Template API.
    """
    account_sid = get_secret("TWILIO_ACCOUNT_SID", "")
    auth_token = get_secret("TWILIO_AUTH_TOKEN", "")
    from_number = get_secret("TWILIO_WHATSAPP_FROM", "")
    content_sid = get_secret("TWILIO_CONTENT_SID", "")

    if not account_sid or account_sid == "YOUR_TWILIO_ACCOUNT_SID":
        return False, "Twilio Account SID is not configured in `.streamlit/secrets.toml`."
    if not auth_token or auth_token == "YOUR_TWILIO_AUTH_TOKEN":
        return False, "Twilio Auth Token is not configured in `.streamlit/secrets.toml`."
    if not from_number or from_number == "YOUR_TWILIO_WHATSAPP_NUMBER":
        return False, "Twilio WhatsApp Sender Number is not configured in `.streamlit/secrets.toml`."
    if not content_sid or content_sid == "YOUR_TWILIO_CONTENT_SID":
        return False, "Twilio WhatsApp Content Template is not configured."

    if not phone_number.strip():
        return False, "User mobile number is empty."

    try:
        from twilio.rest import Client
        import json

        # Format recipient phone number (E.164 with whatsapp: prefix)
        clean_phone = phone_number.strip()
        if not clean_phone.startswith("whatsapp:"):
            if not clean_phone.startswith("+"):
                clean_phone = "+" + clean_phone
            clean_phone = f"whatsapp:{clean_phone}"

        # Format sender phone number (E.164 with whatsapp: prefix)
        clean_from = from_number.strip()
        if not clean_from.startswith("whatsapp:"):
            if not clean_from.startswith("+"):
                clean_from = "+" + clean_from
            clean_from = f"whatsapp:{clean_from}"

        client = Client(account_sid, auth_token)

        # Dispatch using ContentSid and content_variables
        sent_msg = client.messages.create(
            to=clean_phone,
            from_=clean_from,
            content_sid=content_sid.strip(),
            content_variables=json.dumps({"1": message})
        )
        return True, f"WhatsApp message sent successfully via Content Template! Message SID: `{sent_msg.sid}`"

    except Exception as e:
        return False, f"Twilio WhatsApp Error: {str(e)}"


def send_to_telegram(message: str, chat_id: str) -> tuple[bool, str]:
    """
    Sends a message to Telegram using the official Telegram Bot API.
    """
    bot_token = get_secret("TELEGRAM_BOT_TOKEN", "")

    if not bot_token or bot_token == "YOUR_TELEGRAM_BOT_TOKEN":
        return False, "Telegram Bot Token is not configured in `.streamlit/secrets.toml`."
    if not chat_id or not chat_id.strip():
        return False, "Telegram Chat ID is missing. Please enter your Telegram Chat ID in settings or secrets.toml."

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        payload = {
            "chat_id": chat_id.strip(),
            "text": message
        }

        response = requests.post(url, json=payload, timeout=10)
        res_data = response.json()

        if response.status_code == 200 and res_data.get("ok"):
            return True, "Telegram message sent successfully!"
        else:
            err_desc = res_data.get("description", response.text)
            return False, f"Telegram API Error: {err_desc}"
    except Exception as e:
        return False, f"Telegram Connection Error: {str(e)}"


# ==============================================================================
# UI STEP 1: INITIAL REGISTRATION FORM
# ==============================================================================
if not st.session_state.user_info["submitted"]:
    st.title("👤 User Registration")
    st.markdown("Please provide your basic details to start using the Multimodal AI Chatbot.")

    with st.form("user_registration_form"):
        name_input = st.text_input("Full Name", placeholder="e.g. John Doe")
        phone_input = st.text_input("Mobile Number (with country code)", placeholder="e.g. +14155552671")
        submitted = st.form_submit_button("🚀 Start Chatting")

        if submitted:
            if not name_input.strip():
                st.error("Please enter your name.")
            elif not phone_input.strip():
                st.error("Please enter your mobile number.")
            else:
                st.session_state.user_info = {
                    "name": name_input.strip(),
                    "phone": phone_input.strip(),
                    "submitted": True
                }
                st.success("Registration complete! Loading chatbot...")
                st.rerun()

else:
    # ==============================================================================
    # UI STEP 2: MAIN CHAT APPLICATION
    # ==============================================================================
    user_name = st.session_state.user_info["name"]
    user_phone = st.session_state.user_info["phone"]

    # SIDEBAR
    with st.sidebar:
        st.title("⚙️ Control Panel")
        st.subheader(f"👤 Welcome, {user_name}")
        st.caption(f"📞 Mobile: {user_phone}")

        if st.button("✏️ Edit User Info", key="edit_user_info"):
            st.session_state.user_info["submitted"] = False
            st.rerun()

        st.markdown("---")
        st.subheader("✈️ Telegram Settings")
        telegram_id_input = st.text_input(
            "Telegram Chat ID",
            value=st.session_state.telegram_chat_id,
            placeholder="e.g. 123456789",
            help="Enter your Telegram chat ID to receive messages directly."
        )
        st.session_state.telegram_chat_id = telegram_id_input

        st.markdown("---")
        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.session_state.uploaded_image = None
            st.rerun()

    # MAIN CONTENT AREA
    st.title("🤖 AI Multimodal Assistant")

    # Display welcome message if conversation is empty
    if len(st.session_state.messages) == 0:
        st.info(prompt.WELCOME_PROMPT)

    # API Key warning if missing
    if not get_gemini_api_key():
        st.warning("⚠️ **Gemini API Key missing.** Configure your API key in `.streamlit/secrets.toml` to start using the chatbot.")

    # Render Chat History
    for idx, msg in enumerate(st.session_state.messages):
        role = msg["role"]
        content = msg["content"]

        with st.chat_message(role):
            # Render user attached image inside user message thread
            if role == "user" and msg.get("image_preview") is not None:
                st.image(msg["image_preview"], caption="Attached Image", width=250)
            
            if msg.get("category") and role == "assistant":
                st.caption(f"🏷️ *Category: {msg['category']}*")
                
            st.markdown(content)

            # Direct WhatsApp & Telegram buttons under EACH AI assistant response!
            if role == "assistant":
                st.markdown("---")
                col_wa, col_tg = st.columns([1, 1])

                with col_wa:
                    if st.button("📱 Send to WhatsApp", key=f"wa_btn_{idx}"):
                        wa_formatted = prompt.format_whatsapp_message(
                            content,
                            user_name=user_name,
                            has_image=msg.get("has_image", False)
                        )
                        with st.spinner("Sending response to WhatsApp..."):
                            success, status_msg = send_to_whatsapp(wa_formatted, user_phone)
                        if success:
                            st.toast(status_msg, icon="✅")
                            st.success(status_msg)
                        else:
                            st.toast(status_msg, icon="❌")
                            st.error(status_msg)

                with col_tg:
                    if st.button("✈️ Send to Telegram", key=f"tg_btn_{idx}"):
                        tg_formatted = prompt.format_telegram_message(
                            content,
                            user_name=user_name,
                            has_image=msg.get("has_image", False)
                        )
                        chat_id_to_use = st.session_state.telegram_chat_id or get_secret("TELEGRAM_CHAT_ID", "")
                        with st.spinner("Sending response to Telegram..."):
                            success, status_msg = send_to_telegram(tg_formatted, chat_id_to_use)
                        if success:
                            st.toast(status_msg, icon="✅")
                            st.success(status_msg)
                        else:
                            st.toast(status_msg, icon="❌")
                            st.error(status_msg)

    # ==============================================================================
    # ANTIGRAVITY-STYLE CARD CHAT COMPOSER CONTAINER
    # Outer dark box containing:
    # Top: Attached Image preview (if uploaded) + Text prompt input
    # Bottom Row: Left (+ attach popover, Model dropdown) | Right (🎤 Voice, ➔ Send button)
    # ==============================================================================
    st.markdown("---")

    voice_transcription = None

    # Custom CSS for seamless Antigravity-style composer card (removes internal widget borders)
    st.markdown("""
    <style>
        /* Remove internal borders from text input */
        div[data-testid="stTextInput"] input {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
            font-size: 15px !important;
            padding-left: 0px !important;
        }
        div[data-testid="stTextInput"] input:focus {
            border: none !important;
            box-shadow: none !important;
        }

        /* Seamless Model Selectbox without box borders */
        div[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
            font-size: 13px !important;
        }

        /* Seamless Popover (+) button */
        div[data-testid="stPopover"] > button {
            border: none !important;
            background-color: transparent !important;
            box-shadow: none !important;
            font-size: 16px !important;
        }
    </style>
    """, unsafe_allow_html=True)

    with st.container(border=True):
        # Image Thumbnail Preview inside composer box (if attached)
        if st.session_state.uploaded_image is not None:
            prev_col1, prev_col2 = st.columns([0.1, 0.9])
            with prev_col1:
                st.image(st.session_state.uploaded_image, width=60)
            with prev_col2:
                if st.button("❌ Remove Attachment", key="composer_remove_img"):
                    st.session_state.uploaded_image = None
                    st.rerun()

        # Top: Message Text Input Field
        typed_input = st.text_input(
            "Message Composer",
            placeholder="Ask anything, @ to mention, / for actions...",
            label_visibility="collapsed",
            key="composer_typed_input"
        )

        # Bottom Toolbar Row: Left (+ attach popover, Model dropdown) | Right (🎤 Voice, ➔ Send button)
        c_left, c_right = st.columns([6, 6])

        with c_left:
            b_plus, b_model = st.columns([0.8, 4.0])
            with b_plus:
                with st.popover("➕", help="Attach Image"):
                    composer_file = st.file_uploader(
                        "Upload Image for AI Analysis",
                        type=["png", "jpg", "jpeg", "webp"],
                        key="composer_file_input"
                    )
                    if composer_file is not None:
                        try:
                            st.session_state.uploaded_image = Image.open(composer_file)
                            st.success("Image Attached!")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Image error: {str(e)}")

            with b_model:
                chosen_model = st.selectbox(
                    "Model",
                    options=["gemini-3.8-flash", "gemini-3.6-flash", "gemini-flash-latest"],
                    index=0,
                    label_visibility="collapsed",
                    key="composer_model_select"
                )

        with c_right:
            b_space, b_voice, b_send = st.columns([3.2, 1.2, 1.6])
            with b_voice:
                try:
                    from streamlit_mic_recorder import speech_to_text
                    spoken = speech_to_text(
                        language='en',
                        start_prompt="🎤",
                        stop_prompt="⏹️",
                        just_once=True,
                        key="composer_voice_rec"
                    )
                    if spoken:
                        voice_transcription = spoken.strip()
                except Exception:
                    pass

            with b_send:
                send_clicked = st.button("➔", key="composer_send_btn", type="primary", use_container_width=True)

    if voice_transcription:
        st.toast(f"🎙️ Transcribed: \"{voice_transcription}\"", icon="🎙️")

    # Determine user input from voice, text input, or send click
    text_prompt = ""
    attached_pil_image = None
    has_img = False

    if voice_transcription:
        text_prompt = voice_transcription
    elif send_clicked or typed_input:
        text_prompt = typed_input.strip()

    if text_prompt or st.session_state.uploaded_image is not None:
        if send_clicked or voice_transcription:
            attached_pil_image = st.session_state.uploaded_image
            has_img = attached_pil_image is not None

            # Phase 1: Smart Prompt Routing
            category, formatted_prompt = prompt.route_prompt(text_prompt, image_present=has_img)

            # Phase 1: Conversation Memory Context
            conversation_context = build_conversation_context(st.session_state.messages, max_turns=10)

            st.session_state.messages.append({
                "role": "user",
                "content": text_prompt if text_prompt else "Analyze this attached image.",
                "has_image": has_img,
                "image_preview": attached_pil_image
            })

            with st.spinner(f"AI is processing ({category})..."):
                success, response_text = call_gemini_api(
                    formatted_prompt,
                    image=attached_pil_image,
                    conversation_context=conversation_context,
                    chosen_model=chosen_model
                )

            st.session_state.messages.append({
                "role": "assistant",
                "content": response_text,
                "has_image": has_img,
                "category": category
            })
            st.rerun()
