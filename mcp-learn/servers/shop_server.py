


from mcp.server.fastmcp import FastMCP

from typing import Any



mcp = FastMCP(name="shop")


class ProductService:
    def __init__(self,products):
        self.products = products

    def get_product(self, id: int) -> dict[str, Any]:
        return next((product for product in self.products if product["id"] == id), None)

    def list_products(self) -> list[dict[str, Any]]:
        return self.products

    def create_product(self, product: dict[str, Any]) -> dict[str, Any]:
        self.products.append(product)