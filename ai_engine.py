import json
import os
import urllib.request
import ssl
import time

class AIEngine:
    def __init__(self, knowledge_base_path="knowledge_base.json"):
        self.knowledge_base_path = knowledge_base_path
        self.knowledge_base = self._load_knowledge_base()
        
        # Load API keys from environment variable GEMINI_API_KEYS (comma-separated)
        # Fallback to single GEMINI_API_KEY if set
        keys_env = os.getenv("GEMINI_API_KEYS", "")
        if keys_env:
            self.gemini_keys = [k.strip() for k in keys_env.split(",") if k.strip()]
        else:
            single_key = os.getenv("GEMINI_API_KEY", "")
            self.gemini_keys = [single_key] if single_key else []
            
        self.models = ["gemini-3.6-flash", "gemini-flash-latest"]
        self.current_key_idx = 0
        
        # Per-user conversation memory
        self.conversations = {}
        
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
        info = self.knowledge_base.get("business_info", {})
        services = self.knowledge_base.get("services", [])
        faqs = self.knowledge_base.get("faqs", [])
        
        instruction = f"""شما یک انسان واقعی، صمیمی، بسیار هوشمند، باانرژی و رفیقانه در تلگرام هستید که به نمایندگی از {info.get('name', 'پارسا')} به پیام‌های تلگرام پاسخ می‌دهید.

قوانین رفتار و لحن (CRITICAL RULES):
1. دقیقاً مانند یک انسان واقعی و رفیق فاب صحبت کنید. هرگز و تحت هیچ شرایطی متن‌های رباتیک، گزینه‌ای، یا دارای علائمی مانند (سلام داداش/آجی) یا برچسب‌های انگلیسی مانند (Possible responses) ننویسید.
2. همیشه جملات خود را کاملاً روان، کامل و بدون نصفه رها کردن پایان دهید.
3. با شوخ‌طبعی و صمیمیت جواب بدهید.
4. اگر درباره خدمات یا قیمت پروژه‌ها سوال شد، بر اساس اطلاعات زیر راهنمایی کنید.
5. پاسخ‌ها کوتاه، چابک و کامل (بین ۲ تا ۴ جمله) باشد.

اطلاعات خدمات:
"""
        for s in services:
            instruction += f"- {s['name']}: {s['description']} (قیمت: {s.get('pricing', 'استعلام قیمت')})\n"
            
        instruction += "\nسوالات متداول:\n"
        for f in faqs:
            instruction += f"سوال: {f['question']}\nپاسخ: {f['answer']}\n"
            
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
            reply_text = "سلام داداش! چطوری؟ بگو ببینم چه خبر؟ ✨"
            
        history.append({"role": "assistant", "content": reply_text})
        
        return {
            "reply": reply_text,
            "needs_escalation": needs_escalation,
            "reason": reason
        }

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
                            "temperature": 0.8,
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
                    
                    answer = res_json["candidates"][0]["content"]["parts"][0]["text"].strip()
                    
                    self.current_key_idx = (key_idx + 1) % num_keys
                    return answer
                    
                except Exception as e:
                    print(f"Gemini API Exception (Key #{key_idx+1}, Model {model_name}): {e}")
                    time.sleep(0.5)
                    
        return None
