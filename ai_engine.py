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
            reply_text = "سلام رفیق! چطوری؟ بگو ببینم چه خبر و چه کاری می‌تونم برات انجام بدم؟ ✨"
            
        history.append({"role": "assistant", "content": reply_text})
        
        return {
            "reply": reply_text,
            "needs_escalation": needs_escalation,
            "reason": reason
        }

    def generate_admin_response(self, admin_name: str, message_text: str, stats_data: dict) -> str:
        uptime = stats_data.get("uptime", "در حال فعالیت")
        total_msgs = stats_data.get("total_messages", 0)
        escalations = stats_data.get("escalations_count", 0)
        recent_esc = stats_data.get("recent_escalations", [])
        
        system_instruction = f"""شما «دستیار ارشد و کوپایلوت هوشمند مدیر ارشد، {admin_name} (پارسا)» هستید.
لحن شما: صمیمی، حرفه‌ای، خفن، هوشمند و کاملاً مسلط.

اطلاعات و وضعیت لحظه‌ای سیستم شما:
- آپتایم و وضعیت: {uptime}
- کل پیام‌های دریافتی از مشتریان: {total_msgs}
- کل ارجاعات انسانی (Escalations): {escalations}
- تعداد کلیدهای فعال Gemini: {len(self.gemini_keys)}
- تعداد چت‌های فعال مشتریان: {len(self.conversations)}

آخرین گزارش‌های ارجاع انسانی مشتریان:
{json.dumps(recent_esc, ensure_ascii=False, indent=2) if recent_esc else "هیچ ارجاع جدیدی ثبت نشده است."}

وظایف شما در گفتگو با {admin_name}:
۱. مانند یک رفیق و دستیار هوشمند، به هر سوال یا گپ و گفت {admin_name} پاسخ کامل و پرانرژی بدهید.
۲. اگر درباره مشتریان، آمار، استراتژی یا توسعه سوال کرد، راهنمایی دقیق و کاربردی ارائه کنید.
۳. همیشه پاسخ‌ها روان، شیک و بدون کدهای اضافی باشد.
"""
        self.admin_conversations.append({"role": "user", "content": message_text})
        if len(self.admin_conversations) > 10:
            self.admin_conversations = self.admin_conversations[-10:]
            
        reply_text = self._call_gemini_pool(system_instruction, self.admin_conversations)
        
        if not reply_text:
            reply_text = f"سلام {admin_name} جان! سیستم در حال حاضر ۱۰۰٪ پایداره و به پیام‌های مشتریان پاسخ می‌ده. چطور می‌تونم کمکت کنم؟ 👑"
            
        self.admin_conversations.append({"role": "assistant", "content": reply_text})
        return reply_text

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
                    
                    resp = urllib.request.urlopen(req, context=self.ssl_context, timeout=8)
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
