import json
import os
import time
import uuid
import asyncio
from typing import List, Dict, Optional, Tuple, Any
from datetime import datetime
import httpx
from .models import ConsensusApiKey

KEYS_FILE = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "consensus_keys.json")

class KeyManager:
    def __init__(self, filepath: str = KEYS_FILE):
        self.filepath = filepath
        self.keys: List[ConsensusApiKey] = []
        self._current_index: int = 0
        self._lock = asyncio.Lock()
        self.activity_logs: List[Dict[str, Any]] = []
        self.load_keys()

    def load_keys(self):
        """Loads keys from JSON file or initializes default empty structure."""
        if os.path.exists(self.filepath):
            try:
                with open(self.filepath, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.keys = [ConsensusApiKey(**item) for item in data.get("keys", [])]
            except Exception as e:
                print(f"Error loading keys file: {e}")
                self.keys = []
        else:
            # Create template with 6 account placeholders ready to be filled
            self.keys = [
                ConsensusApiKey(
                    id=str(uuid.uuid4())[:8],
                    name=f"اکانت شماره {i+1}",
                    key="",
                    status="disabled"
                )
                for i in range(6)
            ]
            self.save_keys()

    def save_keys(self):
        """Saves keys to JSON file."""
        data = {
            "version": "1.0",
            "updated_at": datetime.now().isoformat(),
            "keys": [k.model_dump() for k in self.keys]
        }
        with open(self.filepath, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def log_event(self, event_type: str, message: str, key_name: Optional[str] = None, details: Optional[Dict[str, Any]] = None):
        """Records an audit log entry."""
        log_entry = {
            "id": str(uuid.uuid4())[:8],
            "timestamp": datetime.now().strftime("%H:%M:%S"),
            "event_type": event_type,  # 'info', 'success', 'warning', 'error', 'failover'
            "message": message,
            "key_name": key_name or "-",
            "details": details or {}
        }
        self.activity_logs.insert(0, log_entry)
        if len(self.activity_logs) > 100:
            self.activity_logs.pop()

    def _refresh_cooldowns(self):
        """Check if rate_limited keys have passed their cooldown and revive them."""
        now = time.time()
        for k in self.keys:
            if k.status == "rate_limited" and k.cooldown_until:
                if now >= k.cooldown_until:
                    k.status = "active"
                    k.cooldown_until = None
                    k.last_error = None
                    self.log_event("info", f"دوره انتظار کلید [{k.name}] پایان یافت و مجدداً فعال شد.", k.name)

    def get_all_keys(self, mask_keys: bool = True) -> List[Dict[str, Any]]:
        self._refresh_cooldowns()
        result = []
        for k in self.keys:
            d = k.model_dump()
            if mask_keys and d["key"]:
                if len(d["key"]) > 8:
                    d["masked_key"] = d["key"][:4] + "••••••••" + d["key"][-4:]
                else:
                    d["masked_key"] = "••••••••"
            else:
                d["masked_key"] = d["key"]
            result.append(d)
        return result

    def add_key(self, key_str: str, name: Optional[str] = None) -> ConsensusApiKey:
        key_str = key_str.strip()
        if not key_str:
            raise ValueError("کلید API نمی‌تواند خالی باشد.")
        
        # Check duplicate
        for k in self.keys:
            if k.key == key_str:
                raise ValueError("این کلید قبلاً در سیستم ثبت شده است.")

        if not name or not name.strip():
            name = f"اکانت شماره {len(self.keys) + 1}"

        new_key = ConsensusApiKey(
            id=str(uuid.uuid4())[:8],
            name=name.strip(),
            key=key_str,
            status="active"
        )
        self.keys.append(new_key)
        self.save_keys()
        self.log_event("success", f"کلید جدید با نام [{new_key.name}] افزوده شد.", new_key.name)
        return new_key

    def add_bulk_keys(self, raw_text: str) -> Tuple[int, List[str]]:
        """Add multiple keys from text lines."""
        lines = [line.strip() for line in raw_text.replace(",", "\n").split("\n") if line.strip()]
        added = 0
        errors = []
        for line in lines:
            try:
                # check if line has name:key format
                if ":" in line and not line.startswith("http"):
                    parts = line.split(":", 1)
                    name = parts[0].strip()
                    key = parts[1].strip()
                else:
                    name = None
                    key = line
                self.add_key(key, name)
                added += 1
            except Exception as e:
                errors.append(f"{line[:10]}...: {str(e)}")
        return added, errors

    def update_key(self, key_id: str, name: Optional[str] = None, status: Optional[str] = None) -> Optional[ConsensusApiKey]:
        for k in self.keys:
            if k.id == key_id:
                if name is not None:
                    k.name = name.strip()
                if status is not None:
                    k.status = status
                    if status == "active":
                        k.cooldown_until = None
                        k.last_error = None
                        k.consecutive_errors = 0
                self.save_keys()
                self.log_event("info", f"اطلاعات کلید [{k.name}] بروزرسانی شد.", k.name)
                return k
        return None

    def delete_key(self, key_id: str) -> bool:
        for i, k in enumerate(self.keys):
            if k.id == key_id:
                deleted = self.keys.pop(i)
                self.save_keys()
                self.log_event("warning", f"کلید [{deleted.name}] حذف شد.", deleted.name)
                return True
        return False

    def reset_all_stats(self):
        """Reset status and request counts on all keys (e.g. for monthly renewal)."""
        for k in self.keys:
            if k.key:
                k.status = "active"
            k.requests_count = 0
            k.consecutive_errors = 0
            k.cooldown_until = None
            k.last_error = None
        self.save_keys()
        self.log_event("success", "تمامی آمارها و وضعیت کلیدها ریست شدند و به حالت فعال برگشتند.")

    async def get_next_available_key(self, exclude_ids: Optional[List[str]] = None) -> Optional[ConsensusApiKey]:
        """
        Round-Robin load balancing selector.
        Returns the next active, non-rate-limited key with a valid key string.
        """
        async with self._lock:
            self._refresh_cooldowns()
            exclude_ids = exclude_ids or []
            
            # Find eligible keys
            eligible = [
                k for k in self.keys 
                if k.status == "active" and k.key.strip() and k.id not in exclude_ids
            ]
            
            if not eligible:
                return None
            
            # Round-robin selection
            # We pick the next one based on current index
            selected = None
            for _ in range(len(self.keys)):
                self._current_index = (self._current_index + 1) % len(self.keys)
                candidate = self.keys[self._current_index]
                if candidate in eligible:
                    selected = candidate
                    break
            
            if not selected:
                selected = eligible[0]
            
            return selected

    def record_success(self, key_id: str):
        """Marks a successful API call on this key."""
        for k in self.keys:
            if k.id == key_id:
                k.requests_count += 1
                k.consecutive_errors = 0
                k.last_used = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                self.save_keys()
                break

    def record_failure(self, key_id: str, status_code: int, error_msg: str) -> Dict[str, Any]:
        """
        Handles error status codes:
        - 429: Rate limited -> set 60s cooldown
        - 403 / 402: Quota exceeded -> mark quota_exhausted
        - 401: Invalid key -> mark invalid
        - Other: increment consecutive errors
        """
        for k in self.keys:
            if k.id == key_id:
                k.consecutive_errors += 1
                k.last_error = f"HTTP {status_code}: {error_msg}"
                
                if status_code == 429:
                    cooldown = 60  # seconds
                    k.status = "rate_limited"
                    k.cooldown_until = time.time() + cooldown
                    action = f"ریت لیمیت شد (۴۲۹). فعال شدن پس از {cooldown} ثانیه."
                    self.log_event("failover", f"⚠️ محدودیت ریت‌لیمیت برای [{k.name}]. سوییچ به کلید دیگر...", k.name)
                elif status_code in (403, 402):
                    k.status = "quota_exhausted"
                    action = "سهمیه ماهانه پایان یافت (۴۰۳/۴۰۲). از چرخه خارج شد."
                    self.log_event("failover", f"⛔ سهمیه ماهانه [{k.name}] تمام شد. سوییچ خودکار به کلید دیگر...", k.name)
                elif status_code == 401:
                    k.status = "invalid"
                    action = "کلید نامعتبر است (۴۰۱)."
                    self.log_event("error", f"❌ کلید [{k.name}] نامعتبر است (۴۰۱).", k.name)
                else:
                    action = f"خطای ارتباطی ({status_code})."
                    self.log_event("warning", f"خطا در کلید [{k.name}]: {error_msg}", k.name)
                
                self.save_keys()
                return {
                    "key_id": k.id,
                    "key_name": k.name,
                    "new_status": k.status,
                    "action": action
                }
        return {}

    async def test_key(self, api_key_str: str) -> Tuple[bool, str]:
        """Direct ping test to Consensus API."""
        api_key_str = api_key_str.strip()
        if not api_key_str:
            return False, "کلید خالی است."
        
        headers = {
            "x-api-key": api_key_str,
            "User-Agent": "ConsensusPaperCraft/1.0"
        }
        url = "https://api.consensus.app/v1/search"
        params = {"query": "artificial intelligence", "page_size": 1}

        try:
            async with httpx.AsyncClient(timeout=10.0) as client:
                res = await client.get(url, headers=headers, params=params)
                if res.status_code == 200:
                    return True, "اتصال با موفقیت برقرار شد (HTTP 200 OK)."
                elif res.status_code == 401:
                    return False, "کلید نامعتبر است (HTTP 401 Unauthorized)."
                elif res.status_code == 429:
                    return False, "محدودیت تعداد درخواست در ثانیه / ریت لیمیت (HTTP 429)."
                elif res.status_code in (403, 402):
                    return False, "اعتبار یا سهمیه این اکانت تمام شده است (HTTP 403/402)."
                else:
                    return False, f"خطای سرور: HTTP {res.status_code} - {res.text[:100]}"
        except httpx.RequestError as e:
            return False, f"خطای اتصال به شبکه: {str(e)}"
