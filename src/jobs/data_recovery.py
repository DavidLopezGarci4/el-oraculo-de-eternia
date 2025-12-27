import sys
import os
from pathlib import Path
from datetime import datetime
from sqlalchemy.orm import Session

# Add project root to Python path
root_path = Path(__file__).resolve().parent.parent.parent
sys.path.append(str(root_path))

from src.infrastructure.database import SessionLocal
from src.domain.models import OfferHistoryModel, PendingMatchModel, OfferModel, ProductModel

def recover_to_purgatory(db: Session, limit=100):
    """
    Lee las últimas entradas del historial y restaura items al Purgatorio si no existen.
    """
    print(f"🕵️ Iniciando recuperación del Bastión de Datos (Límite: {limit})...")
    
    # Obtener el historial de movimientos que indican items "activos" alguna vez
    history_entries = db.query(OfferHistoryModel).order_by(OfferHistoryModel.timestamp.desc()).limit(limit).all()
    
    recovered_count = 0
    for entry in history_entries:
        # Verificar si ya existe en algun lado (Offer o Pending)
        exists_offer = db.query(OfferModel).filter(OfferModel.url == entry.offer_url).first()
        exists_pending = db.query(PendingMatchModel).filter(PendingMatchModel.url == entry.offer_url).first()
        
        if not exists_offer and not exists_pending:
            print(f"♻️ Restaurando: {entry.product_name} ({entry.shop_name})")
            new_pending = PendingMatchModel(
                scraped_name=entry.product_name,
                price=entry.price,
                currency="EUR",
                url=entry.offer_url,
                shop_name=entry.shop_name,
                details=f"RESTORED: From History ID {entry.id} ({entry.action_type})" if hasattr(PendingMatchModel, 'details') else None
            )
            db.add(new_pending)
            recovered_count += 1
            
    db.commit()
    print(f"✅ Recuperación finalizada. Items restaurados al Purgatorio: {recovered_count}")

def show_history(db: Session, limit=20):
    """
    Muestra los últimos movimientos registrados.
    """
    print(f"\n📰 Últimos 20 movimientos en el Bastión:\n")
    entries = db.query(OfferHistoryModel).order_by(OfferHistoryModel.timestamp.desc()).limit(limit).all()
    for e in entries:
        print(f"[{e.timestamp.strftime('%Y-%m-%d %H:%M')}] {e.action_type:15} | {e.shop_name:12} | {e.product_name[:40]:40} | {e.price}€")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Oráculo Recovery Tool (Bastión)")
    parser.add_argument("--show", action="store_true", help="Mostrar historial")
    parser.add_argument("--restore", action="store_true", help="Restaurar items perdidos al Purgatorio")
    args = parser.parse_args()
    
    db = SessionLocal()
    try:
        if args.show:
            show_history(db)
        if args.restore:
            recover_to_purgatory(db)
        if not args.show and not args.restore:
            parser.print_help()
    finally:
        db.close()
