from fastmcp import FastMCP
from src.infrastructure.database import SessionLocal
from src.infrastructure.repositories.product import ProductRepository
from src.domain.models import ProductModel
from typing import List, Optional

# Initialize FastMCP server
mcp = FastMCP("El Oráculo de Eternia")

@mcp.tool()
def search_product(query: str) -> List[str]:
    """
    Busca productos en la base de datos de Eternia por nombre.
    Retorna una lista de nombres encontrados.
    """
    db = SessionLocal()
    try:
        repo = ProductRepository(db)
        products = repo.get_all() # Optimization: Filter in DB
        # Simple client-side filter
        results = [p.name for p in products if query.lower() in p.name.lower()]
        return results[:10] # Top 10
    finally:
        db.close()

@mcp.tool()
def get_product_details(name: str) -> str:
    """
    Obtiene los detalles completos de un producto dado su nombre exacto.
    """
    db = SessionLocal()
    try:
        repo = ProductRepository(db)
        product = repo.get_by_name(name)
        if not product:
            return f"No se encontró el producto: {name}"
        
        info = f"Product: {product.name}\nCategory: {product.category}\nImage: {product.image_url}\n"
        if product.offers:
            info += f"Offers: {len(product.offers)} found.\n"
        
        return info
    finally:
        db.close()

if __name__ == "__main__":
    mcp.run()
