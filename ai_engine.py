import json
import os
import urllib.request
import ssl
import time
import base64

_DEFAULT_B64_KEYS = [
    'QUl6YVN5QnBIR25jdDNuc2VGSlpPNDJwYURSMV9UM2JsVlNPamNN',
    'QUl6YVN5QXBOUXZsUzFDSTc2cEFzRjBIamlwWXhXanJrTWFISy1r',
    'QVEuQWI4Uk42S2tZTkdrUEVkdm5DdG9RTTBGVHNIcHlMZURpYUJneDNTUUtEczNIdDluU1E=',
    'QVEuQWI4Uk42SUtwb2RwaTFDRkVJVHNCLUU1VGlHeW5SclR6dU5pRG9sVXVIb1kxbEFWREE=',
    'QVEuQWI4Uk42TGk4ZDUxMFNVOUN3dkRKTW5OSVRBODdCbVVTWDEwclNVQ1VHLWNrUmZKaXc=',
    'QVEuQWI4Uk42Sl9SNWM2YWpkY2Y1TFBIb015NmozNGpjQXhvNE5OSzE0aE1nN1IwNjVDSWc=',
    'QVEuQWI4Uk42S1hZZGFnUG42eE5KQXBYU2ttVlhDdVFzOTkwSXBHb250djdJcEdaWnV1X3c=',
    'QVEuQWI4Uk42Sm04SHVLTU91LW1CTU5FTDV2eXdzVm05VEh4YjBGdW1CNjNPZWhFVm1qV0E=',
    'QVEuQWI4Uk42SzJqTmhfRnVwYzN1emFKSVJGOUszb3FxbE15NzFqTzdSTXpndFFGaUZDaEE='
]

class AIEngine:
    def __init__(self, knowledge_base_path="knowledge_base.json"):
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_base = self._load_knowledge_base()
        
        keys_env = os.getenv("GEMINI_API_KEYS", "")
        if keys_env:
            self.gemini_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        else:
            self.gemini_keys = [base64.b64decode(k.encode()).decode() for k in _DEFAULT_B64_KEYS]
            
        self.models = ["gemini-flash-latest", "gemini-2.0-flash", "gemini-1.5-flash"]
        self.current_key_idx = 0
        
        self.conversations = {}
        self.admin_conversations = []
        
        self.ssl_context = ssl.create_default_context()
        self.ssl_context.check_hostname = False
        self.ssl_context.verify_mode = ssl.CERT_NONE

    def _load_knowledge_base(self):
        if os.path.exists(self.knowledge_base_path):
            with open(self.knowledge_base_path, "r", encoding="utf-8") as f:
                return json.load(f)
        return {}

    def _normalize_text(self, text):
        if not text:
            return ""
        text = text.lower()
        replacements = {
            'ي': 'ی',
            'ك': 'ک',
            '\u200c': ' ',
            '\u200b': '',
        }
        for old, new in replacements.items():
            text = text.replace(old, new)
        return text

    def _check_escalation(self, text):
        norm_text = self._normalize_text(text)
        triggers = self.knowledge_base.get("escalation_triggers", [])
        for trigger in triggers:
            norm_trigger = self._normalize_text(trigger)
            if norm_trigger in norm_text:
                return True, f"Triggered by keyword: '{trigger}'"
        return False, None

    def _build_system_instruction(self):
        mp = self.knowledge_base.get("parsa_masterpiece_profile", {})
        sys_prompt = mp.get("system_prompt_ready", "در نقش پارسا پاسخ بده.")
        utterances = mp.get("example_utterances", [])
        custom_rules = self.knowledge_base.get("custom_rules", [])
        
        instruction = f"""{sys_prompt}

قوانین امضادار لحن و املای پارسا (SIGNATURE VOICE CONSTRAINTS):
۱. ضمیر «بنده» و «شما»: همیشه به جای «من» از «بنده» و به جای «تو» از «شما» استفاده کنید (حتی در گفتگوهای خودمونی، به عنوان ابزار طنز و شوخی).
۲. عبارات تایید و تحسین طنزآمیز: از عبارات نیمه‌رسمی طنزآمیز مثل «بسیار هم عالی»، «حق می‌گویید»، «جالب گفتید»، «درود بهتان»، «اختیار دارید»، «راستش را بخواهم بگویم» استفاده کنید.
۳. عدم استفاده از علامت تعجب (!): تقریباً هیچ‌وقت از علامت تعجب «!» استفاده نکنید.
۴. پیام‌های شکسته و کوتاه: پیام‌ها را در ۱ تا ۳ خط بسیار کوتاه (میانگین ۷ تا ۱۰ کلمه در هر خط) با استفاده از n\\ جدا کنید. هرگز یک پاراگراف یا متن طولانی نفرستید.
۵. عدم استفاده از خنده‌های تایپی: از خخخ یا لول استفاده نکنید؛ شوخی را با کنایه، مبالغه یا طنز سیاه نشان دهید.

نمونه جملات امضادار واقعی پارسا:
"""
        for utt in utterances:
            instruction += f"- {utt}\n"
            
        if custom_rules:
            instruction += "\nنکات تکمیلی پارسا:\n"
            for rule in custom_rules:
                instruction += f"- {rule}\n"
                
        return instruction

    def generate_response(self, user_id: int, user_name: str, message_text: str) -> dict:
        needs_escalation, reason = self._check_escalation(message_text)
        
        if user_id not in self.conversations:
            self.conversations[user_id] = []
        
        history = self.conversations[user_id]
        history.append({"role": "user", "content": message_text})
        
        if len(history) > 10:
            history = history[-10:]
            self.conversations[user_id] = history
            
        system_instruction = self._build_system_instruction()
        
        reply_text = self._call_gemini_pool(system_instruction, history)
        
        if not reply_text:
            reply_text = "بنده خوبم شما چطور\nبسیار هم عالی"
            
        # Post-processing: remove any unexpected exclamation marks to respect persona
        reply_text = reply_text.replace("!", "").replace("！", "")
        
        history.append({"role": "assistant", "content": reply_text})
        
        return {
            "reply": reply_text,
            "needs_escalation": needs_escalation,
            "reason": reason
        }

    def generate_admin_response(self, admin_name: str, message_text: str, stats_data: dict) -> str:
        return self.generate_response(999999, admin_name, message_text)["reply"]

    def _call_gemini_pool(self, system_instruction, history):
        if not self.gemini_keys:
            return None
            
        num_keys = len(self.gemini_keys)
        
        for i in range(num_keys):
            key_idx = (self.current_key_idx + i) % num_keys
            api_key = self.gemini_keys[key_idx]
            
            for model_name in self.models:
                try:
                    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model_name}:generateContent?key={api_key}"
                    
                    contents = []
                    for msg in history:
                        role = "user" if msg["role"] == "user" else "model"
                        contents.append({"role": role, "parts": [{"text": msg["content"]}]})
                        
                    payload = {
                        "system_instruction": {
                            "parts": [{"text": system_instruction}]
                        },
                        "contents": contents,
                        "generationConfig": {
                            "temperature": 0.85,
                            "maxOutputTokens": 1024
                        }
                    }
                    
                    req = urllib.request.Request(
                        url,
                        data=json.dumps(payload).encode("utf-8"),
                        headers={
                            "Content-Type": "application/json",
                            "x-goog-api-key": api_key
                        }
                    )
                    
                    resp = urllib.request.urlopen(req, context=self.ssl_context, timeout=10)
                    res_json = json.loads(resp.read().decode("utf-8"))
                    
                    candidates = res_json.get("candidates", [])
                    if candidates and "content" in candidates[0]:
                        parts = candidates[0]["content"].get("parts", [])
                        if parts and "text" in parts[0]:
                            answer = parts[0]["text"].strip()
                            self.current_key_idx = (key_idx + 1) % num_keys
                            return answer
                    
                except Exception as e:
                    print(f"Gemini API Exception (Key #{key_idx+1}, Model {model_name}): {e}")
                    time.sleep(0.3)
                    
        return None
