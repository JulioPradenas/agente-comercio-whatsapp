"""Genera un catálogo sintético de una tienda de electro y hogar.

Salida: data/raw/products.csv
Uso:    uv run python data/generate_catalog.py
"""

import json
from pathlib import Path

import numpy as np
import pandas as pd

SEED = 42
N_PRODUCTS = 300
OUTPUT_PATH = Path(__file__).parent / "raw" / "products.csv"

# Cada tipo de producto define reglas de negocio: rango de precio (CLP),
# marcas plausibles y atributos con valores válidos. Sin esto, un generador
# aleatorio produce cosas como "Refrigerador Lenovo de $9.990".
PRODUCT_TYPES: dict[str, dict] = {
    "Refrigerador": {
        "category": "Línea blanca",
        "price_range": (249_990, 1_499_990),
        "brands": ["Samsung", "LG", "Mabe", "Fensa", "Midea"],
        "attributes": {"tecnologia": ["No Frost", "Frío directo"], "capacidad_l": [250, 300, 350, 420, 500]},
    },
    "Lavadora": {
        "category": "Línea blanca",
        "price_range": (199_990, 899_990),
        "brands": ["Samsung", "LG", "Mabe", "Fensa", "Midea"],
        "attributes": {"carga": ["Frontal", "Superior"], "capacidad_kg": [8, 10, 13, 16, 19]},
    },
    "Smart TV": {
        "category": "Televisión",
        "price_range": (179_990, 2_499_990),
        "brands": ["Samsung", "LG", "Sony", "TCL", "Hisense"],
        "attributes": {"pulgadas": [32, 43, 50, 55, 65, 75], "resolucion": ["HD", "4K UHD", "QLED 4K", "OLED 4K"]},
    },
    "Notebook": {
        "category": "Computación",
        "price_range": (299_990, 1_999_990),
        "brands": ["Lenovo", "HP", "Asus", "Acer", "Dell"],
        "attributes": {"ram_gb": [8, 16, 32], "almacenamiento_gb": [256, 512, 1024], "pantalla_pulgadas": [14, 15.6, 16]},
    },
    "Smartphone": {
        "category": "Telefonía",
        "price_range": (99_990, 1_399_990),
        "brands": ["Samsung", "Xiaomi", "Motorola", "Apple", "Honor"],
        "attributes": {"almacenamiento_gb": [128, 256, 512], "color": ["Negro", "Azul", "Blanco", "Verde"]},
    },
    "Audífonos": {
        "category": "Audio",
        "price_range": (14_990, 399_990),
        "brands": ["Sony", "JBL", "Xiaomi", "Samsung", "Apple"],
        "attributes": {"tipo": ["In-ear", "Over-ear"], "cancelacion_ruido": ["Sí", "No"]},
    },
    "Microondas": {
        "category": "Electrodomésticos",
        "price_range": (59_990, 249_990),
        "brands": ["Samsung", "LG", "Mabe", "Thomas", "Oster"],
        "attributes": {"capacidad_l": [20, 25, 28, 32], "grill": ["Sí", "No"]},
    },
    "Aspiradora": {
        "category": "Electrodomésticos",
        "price_range": (49_990, 699_990),
        "brands": ["Electrolux", "Thomas", "Xiaomi", "Philips", "Samsung"],
        "attributes": {"tipo": ["Escoba", "Robot", "Arrastre"], "inalambrica": ["Sí", "No"]},
    },
}


def to_retail_price(raw_price: float) -> int:
    """Redondea al estilo retail chileno: 349.990 en vez de 347.218."""
    return int(np.ceil(raw_price / 10_000) * 10_000 - 10)


def build_name(product_type: str, brand: str, attrs: dict) -> str:
    """Arma un nombre comercial legible a partir de los atributos más relevantes."""
    # lambdas: cada texto se evalúa solo para su tipo (un dict de f-strings
    # evaluaría todas y fallaría con atributos que ese tipo no tiene).
    highlights = {
        "Refrigerador": lambda a: f"{a['tecnologia']} {a['capacidad_l']} L",
        "Lavadora": lambda a: f"Carga {a['carga']} {a['capacidad_kg']} kg",
        "Smart TV": lambda a: f'{a["pulgadas"]}" {a["resolucion"]}',
        "Notebook": lambda a: f"{a['ram_gb']}GB RAM {a['almacenamiento_gb']}GB SSD",
        "Smartphone": lambda a: f"{a['almacenamiento_gb']}GB {a['color']}",
        "Audífonos": lambda a: a["tipo"] + (" con cancelación de ruido" if a["cancelacion_ruido"] == "Sí" else ""),
        "Microondas": lambda a: f"{a['capacidad_l']} L" + (" con grill" if a["grill"] == "Sí" else ""),
        "Aspiradora": lambda a: a["tipo"] + (" inalámbrica" if a["inalambrica"] == "Sí" else ""),
    }
    return f"{product_type} {brand} {highlights[product_type](attrs)}"


def build_description(name: str, category: str, attrs: dict) -> str:
    """Texto que más adelante se convertirá en embedding para la búsqueda semántica."""
    attr_text = ", ".join(f"{key.replace('_', ' ')}: {value}" for key, value in attrs.items())
    return f"{name}. Categoría {category}. Características: {attr_text}."


def generate_catalog(n_products: int, rng: np.random.Generator) -> pd.DataFrame:
    type_names = list(PRODUCT_TYPES)
    rows = []

    for i in range(n_products):
        product_type = str(rng.choice(type_names))
        spec = PRODUCT_TYPES[product_type]
        brand = str(rng.choice(spec["brands"]))
        attrs = {key: rng.choice(values).item() for key, values in spec["attributes"].items()}

        # Log-uniforme: hay muchos más productos baratos que caros dentro de cada rango.
        low, high = spec["price_range"]
        list_price = to_retail_price(np.exp(rng.uniform(np.log(low), np.log(high))))

        # ~30% de los productos tienen descuento entre 10% y 40%.
        has_discount = rng.random() < 0.30
        sale_price = to_retail_price(list_price * (1 - rng.uniform(0.10, 0.40))) if has_discount else list_price

        # ~12% sin stock: el agente debe saber decir "no hay" y ofrecer alternativas.
        stock = 0 if rng.random() < 0.12 else int(rng.integers(1, 80))

        # Código de modelo como en un catálogo real: evita nombres idénticos con distinto SKU,
        # que confundirían al agente ("¿cuál de los dos refrigeradores?").
        model_code = f"{brand[:2].upper()}{rng.integers(100, 1000)}"
        name = f"{build_name(product_type, brand, attrs)} ({model_code})"
        rows.append(
            {
                "sku": f"SKU-{100_000 + i}",
                "name": name,
                "product_type": product_type,
                "category": spec["category"],
                "brand": brand,
                "list_price": list_price,
                "sale_price": sale_price,
                "stock": stock,
                "attributes": attrs,
                "description": build_description(name, spec["category"], attrs),
            }
        )

    return pd.DataFrame(rows)


if __name__ == "__main__":
    rng = np.random.default_rng(SEED)
    products = generate_catalog(N_PRODUCTS, rng)

    # attributes es un dict; se guarda como JSON para que el CSV sea plano.
    products["attributes"] = products["attributes"].apply(lambda attrs: json.dumps(attrs, ensure_ascii=False))

    OUTPUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    products.to_csv(OUTPUT_PATH, index=False)
    print(f"Guardado: {OUTPUT_PATH} ({len(products)} filas)")
