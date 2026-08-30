"""Multi-Channel Alert Dispatcher (Telegram, Webhook & Audible Alarms)."""

from __future__ import annotations

import os
import time
import requests
from typing import Optional
from ppe_detector.database.models import Incident


class AlertNotifier:
    """Dispatches high-priority incident alerts to external services."""

    def __init__(
        self,
        telegram_token: Optional[str] = None,
        telegram_chat_id: Optional[str] = None,
        webhook_url: Optional[str] = None,
    ):
        self.telegram_token = telegram_token or os.getenv("TELEGRAM_BOT_TOKEN")
        self.telegram_chat_id = telegram_chat_id or os.getenv("TELEGRAM_CHAT_ID")
        self.webhook_url = webhook_url or os.getenv("WEBHOOK_ALERT_URL")

    def notify(self, incident: Incident) -> bool:
        """Send incident notifications across configured channels."""
        success = True

        if self.telegram_token and self.telegram_chat_id:
            try:
                self._send_telegram(incident)
            except Exception:
                success = False

        if self.webhook_url:
            try:
                self._send_webhook(incident)
            except Exception:
                success = False

        return success

    def _send_telegram(self, incident: Incident):
        """Send formatted alert to Telegram channel."""
        text = (
            f"🚨 *INDUSTRIAL SAFETY VIOLATION DETECTED*\n\n"
            f"📍 *Zone*: {incident.zone_name}\n"
            f"📹 *Camera*: {incident.camera_id}\n"
            f"⚠️ *Violation*: {incident.violation_type}\n"
            f"👤 *Worker ID*: #{incident.worker_track_id}\n"
            f"🕒 *Timestamp*: {incident.timestamp}\n"
            f"🎯 *Confidence*: {int(incident.confidence * 100)}%"
        )
        url = f"https://api.telegram.org/bot{self.telegram_token}/sendMessage"
        payload = {
            "chat_id": self.telegram_chat_id,
            "text": text,
            "parse_mode": "Markdown",
        }
        requests.post(url, json=payload, timeout=5)

    def _send_webhook(self, incident: Incident):
        """Post incident payload to an enterprise webhook."""
        requests.post(self.webhook_url, json=incident.to_dict(), timeout=5)
