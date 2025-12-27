import httpx
import logging
from typing import Optional
from src.core.config import settings
from sqlalchemy.orm import Session
from datetime import datetime

logger = logging.getLogger("notifier")

class NotifierService:
    _last_sent = {} # Class-level cache to persist across instances in same process

    def __init__(self):
        self.token = settings.TELEGRAM_BOT_TOKEN
        self.chat_id = settings.TELEGRAM_CHAT_ID
        self.api_url = f"https://api.telegram.org/bot{self.token}/sendMessage" if self.token else None

    def _should_throttle(self, key: str, minutes: int = 60) -> bool:
        """
        Returns True if the message should be throttled.
        """
        now = datetime.utcnow()
        if key in self._last_sent:
            last_time = self._last_sent[key]
            if (now - last_time).total_seconds() < (minutes * 60):
                return True
        self._last_sent[key] = now
        return False

    async def send_deal_alert(self, product, offer, discount: float):
        if not self.api_url or not self.chat_id:
            return

        # Rate limit per product to avoid spamming the same deal
        if self._should_throttle(f"deal_{product.name}", minutes=120): # 2 hours
            return

        savings = offer.max_price - offer.price
        
        msg = (
            f"🔥 **ALERTA DE CAZA** 🔥\n\n"
            f"📦 **{product.name}**\n"
            f"💰 Precio: **{offer.price:.2f}€**\n"
            f"📉 Descuento: **-{discount*100:.0f}%** (Antes {offer.max_price:.2f}€)\n"
            f"💵 Ahorro: {savings:.2f}€\n"
            f"🏪 Tienda: {offer.shop_name}\n\n"
            f"[🔗 Comprar ahora]({offer.url})"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": msg,
            "parse_mode": "Markdown"
        }

        try:
            async with httpx.AsyncClient() as client:
                resp = await client.post(self.api_url, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    logger.info(f"📨 Alert sent for {product.name}")
                else:
                    logger.error(f"❌ Telegram Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")

    def send_deal_alert_sync(self, product, offer, discount: float):
        """Synchronous version for use in sync pipeline context"""
        if not self.api_url or not self.chat_id:
            return

        # Rate limit per product
        if self._should_throttle(f"deal_{product.name}", minutes=120):
            return

        savings = offer.max_price - offer.price
        
        msg = (
            f"🔥 **ALERTA DE CAZA** 🔥\n\n"
            f"📦 **{product.name}**\n"
            f"💰 Precio: **{offer.price:.2f}€**\n"
            f"📉 Descuento: **-{discount*100:.0f}%** (Antes {offer.max_price:.2f}€)\n"
            f"💵 Ahorro: {savings:.2f}€\n"
            f"🏪 Tienda: {offer.shop_name}\n\n"
            f"[🔗 Comprar ahora]({offer.url})"
        )

        payload = {
            "chat_id": self.chat_id,
            "text": msg,
            "parse_mode": "Markdown"
        }

        try:
            with httpx.Client() as client:
                resp = client.post(self.api_url, json=payload, timeout=10.0)
                if resp.status_code == 200:
                    logger.info(f"📨 Alert sent for {product.name}")
                else:
                    logger.error(f"❌ Telegram Error {resp.status_code}: {resp.text}")
        except Exception as e:
            logger.error(f"❌ Failed to send Telegram alert: {e}")

    async def send_message(self, text: str):
        """Generic message sender with anti-spam protection"""
        if not self.api_url or not self.chat_id:
            return

        # Rate limit based on message content to avoid alert loops
        import hashlib
        msg_hash = hashlib.md5(text.encode()).hexdigest()
        if self._should_throttle(f"msg_{msg_hash}", minutes=30):
            logger.warning(f"Throttling duplicate message: {text[:50]}...")
            return

        payload = {
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "Markdown"
        }
        try:
            async with httpx.AsyncClient() as client:
                await client.post(self.api_url, json=payload)
        except Exception:
            pass

    def check_price_alerts_sync(self, db: Session, product, offer):
        from src.domain.models import ProductModel, OfferModel, PriceAlertModel
        """
        Checks if a newly updated price triggers any user alerts.
        """
        alerts = db.query(PriceAlertModel).filter(
            PriceAlertModel.product_id == product.id,
            PriceAlertModel.is_active == True,
            PriceAlertModel.target_price >= offer.price
        ).all()
        
        for alert in alerts:
            # Avoid notifying too often (e.g. once per 12h per alert)
            if alert.last_notified_at:
                from datetime import timedelta
                if datetime.utcnow() - alert.last_notified_at < timedelta(hours=12):
                    continue
            
            msg = (
                f"🛡️ **EL CENTINELA HA AVISTADO UNA PRESA** 🛡️\n\n"
                f"🎯 **{product.name}** ha bajado de tu umbral ({alert.target_price:.2f}€)\n"
                f"💰 Precio Actual: **{offer.price:.2f}€**\n"
                f"🏪 Tienda: {offer.shop_name}\n\n"
                f"[🔗 Abrir en el Oráculo]({offer.url})"
            )
            
            payload = {
                "chat_id": self.chat_id, # Target chat_id
                "text": msg,
                "parse_mode": "Markdown"
            }
            
            try:
                if self.api_url:
                    with httpx.Client() as client:
                        resp = client.post(self.api_url, json=payload, timeout=10.0)
                        if resp.status_code == 200:
                            alert.last_notified_at = datetime.utcnow()
                            db.commit()
                            logger.info(f"🔔 Price alert sent to user {alert.user_id} for {product.name}")
            except Exception as e:
                logger.error(f"❌ Failed to send Sentinel alert: {e}")
