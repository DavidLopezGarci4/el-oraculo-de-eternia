import sys
import os
from datetime import datetime, timezone, timedelta
from sqlalchemy import text

# Añadir el root al path para importar src
sys.path.append(os.getcwd())

try:
    from src.infrastructure.database import SessionLocal, engine
    from src.domain.models import ProductModel, OfferModel, PendingMatchModel, BlackcludedItemModel
except ImportError as e:
    print(f"Error de importacion: {e}")
    sys.exit(1)

def perform_audit():
    # Configurar salida segura para evitar errores de Unicode en Windows
    if sys.platform == 'win32':
        import codecs
        sys.stdout = codecs.getwriter('utf-8')(sys.stdout.detach())

    print("--- AUDITORIA DEL ORACULO (Revision de Datos) ---")
    now = datetime.now(timezone.utc)
    cutoff_24h = now - timedelta(hours=24)
    cutoff_48h = now - timedelta(hours=48)

    db = SessionLocal()
    try:
        # 1. Verificar Ofertas Vinculadas Recientemente
        print("\n[1] Ofertass vinculadas recientemente (ultimas 48h):")
        recent_offers = db.query(OfferModel).filter(OfferModel.last_seen >= cutoff_48h).all()
        if not recent_offers:
            print(" - No hay ofertas nuevas vinculadas.")
        else:
            for o in recent_offers:
                p_name = o.product.name if o.product else "DESCONOCIDO"
                print(f" - [{o.shop_name}] {p_name}: {o.price} EUR (Visto: {o.last_seen})")

        # 2. Verificar Purgatorio (Pending Matches)
        print("\n[2] Items en el Purgatorio creados recientemente:")
        pending = db.query(PendingMatchModel).filter(PendingMatchModel.found_at >= cutoff_48h).all()
        if not pending:
            print(" - No hay items nuevos en el Purgatorio.")
        else:
            for p in pending:
                print(f" - [PENDIENTE] {p.scraped_name} de {p.shop_name} ({p.price} EUR)")

        # 3. Verificar Exilio (Blacklist) - CAUSA PROBABLE DE DESAPARICION
        print("\n[3] Items EXILIADOS (Blacklist) recientemente (Causa de desaparicion):")
        blacklisted = db.query(BlackcludedItemModel).filter(BlackcludedItemModel.created_at >= cutoff_48h).all()
        if not blacklisted:
            print(" - No hay items exiliados recientemente.")
        else:
            for b in blacklisted:
                print(f" - [EXILIADO] {b.scraped_name} (Razon: {b.reason}, Fecha: {b.created_at})")

        # 4. Auditoria de conteo total
        print("\n[4] Estadisticas Globales:")
        print(f" - Total Productos: {db.query(ProductModel).count()}")
        print(f" - Total Ofertas Vinculadas: {db.query(OfferModel).count()}")
        print(f" - Total Purgatorio: {db.query(PendingMatchModel).count()}")
        print(f" - Total Blacklist: {db.query(BlackcludedItemModel).count()}")

    except Exception as e:
        print(f"ERROR DURANTE LA AUDITORIA: {str(e)}")
    finally:
        db.close()

if __name__ == "__main__":
    perform_audit()
