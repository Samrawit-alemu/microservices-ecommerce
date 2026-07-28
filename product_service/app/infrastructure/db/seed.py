# product_service/app/infrastructure/db/seed.py
import os
from decimal import Decimal

from sqlalchemy import text
from sqlalchemy.future import select

from app.infrastructure.db.config import async_session
from app.infrastructure.db.models import ProductDB


def _image(photo_id: str) -> str:
    return f"https://images.unsplash.com/photo-{photo_id}?w=600&q=80&auto=format&fit=crop"


CATALOG = [
    {
        "name": "Wireless Mouse",
        "description": "Contoured two-button mouse with a precision scroll wheel and silent-click switches. Pairs over a 2.4GHz USB receiver and runs up to 18 months per battery.",
        "price": Decimal("35.00"),
        "stock": 15,
        "image_url": _image("1527864550417-7fd91fc51a46"),
    },
    {
        "name": "Mechanical Keyboard",
        "description": "Compact 75% layout with hot-swappable tactile switches and doubleshot PBT keycaps. Connects over USB-C or Bluetooth to three paired devices.",
        "price": Decimal("89.00"),
        "stock": 12,
        "image_url": _image("1618384887929-16ec33fab9ef"),
    },
    {
        "name": "Slim Wireless Keyboard",
        "description": "Low-profile scissor-switch keys set in a full-size aluminium frame. Recharges over USB-C and holds roughly a month of typing per charge.",
        "price": Decimal("59.00"),
        "stock": 20,
        "image_url": _image("1587829741301-dc798b83add3"),
    },
    {
        "name": "Noise-Cancelling Headphones",
        "description": "Over-ear active noise cancellation tuned for open offices, with 30-hour battery life and a transparency mode for quick conversations.",
        "price": Decimal("199.00"),
        "stock": 10,
        "image_url": _image("1546435770-a3e426bf472b"),
    },
    {
        "name": "Studio Over-Ear Headphones",
        "description": "Closed-back reference headphones with a flat response curve for mixing. Ships with a detachable coiled cable and replaceable velour pads.",
        "price": Decimal("129.00"),
        "stock": 14,
        "image_url": _image("1505740420928-5e560c06d30e"),
    },
    {
        "name": "27-inch 4K Monitor",
        "description": "27-inch 4K IPS panel covering 99% of sRGB, with a single-cable USB-C dock that delivers 90W of charging back to your laptop.",
        "price": Decimal("429.00"),
        "stock": 6,
        "image_url": _image("1527443224154-c4a3942d3acf"),
    },
    {
        "name": "24-inch IPS Monitor",
        "description": "Sharp 1440p IPS display with slim bezels and a height-adjustable stand. A practical second screen for code and documentation.",
        "price": Decimal("189.00"),
        "stock": 9,
        "image_url": _image("1585792180666-f7347c490ee2"),
    },
    {
        "name": "LED Desk Lamp",
        "description": "Matte steel task lamp on a weighted base with stepless warm-to-cool dimming. The articulated arm holds its position without drifting.",
        "price": Decimal("45.00"),
        "stock": 25,
        "image_url": _image("1507473885765-e6ed057f782c"),
    },
    {
        "name": "Tablet with Stylus",
        "description": "Laminated 10.9-inch display paired with a low-latency stylus for sketching and handwritten notes. Doubles as a portable second monitor.",
        "price": Decimal("549.00"),
        "stock": 8,
        "image_url": _image("1544244015-0df4b3ffc6b0"),
    },
    {
        "name": "13-inch Ultrabook",
        "description": "A 1.1kg magnesium chassis with a 13-inch touchscreen and all-day battery, configured with 16GB of memory and a 512GB NVMe drive.",
        "price": Decimal("1099.00"),
        "stock": 5,
        "image_url": _image("1593642632823-8f785ba67e45"),
    },
    {
        "name": "16-inch Pro Laptop",
        "description": "Sixteen-inch mobile workstation with a discrete GPU and backlit keyboard, built for compiling and rendering away from a desk.",
        "price": Decimal("2399.00"),
        "stock": 3,
        "image_url": _image("1517336714731-489689fd1ca8"),
    },
    {
        "name": "4TB Internal Hard Drive",
        "description": "4TB 7200RPM SATA drive with a 256MB cache, rated for continuous operation in NAS enclosures and home servers.",
        "price": Decimal("95.00"),
        "stock": 30,
        "image_url": _image("1531492746076-161ca9bcad58"),
    },
]


async def ensure_schema(conn) -> None:
    """
    create_all() only creates missing tables, so it cannot add image_url to a
    products table that already exists on a deployed database.
    """
    await conn.execute(
        text("ALTER TABLE products ADD COLUMN IF NOT EXISTS image_url VARCHAR(500)")
    )


async def seed_catalog() -> None:
    """
    Populates the demo storefront. Safe to run on every boot: products are matched
    by name, and existing rows keep the price and stock that live orders depend on.
    """
    if os.getenv("SEED_CATALOG", "true").strip().lower() not in ("1", "true", "yes"):
        print("[*] Catalog seeding disabled via SEED_CATALOG")
        return

    async with async_session() as session:
        result = await session.execute(select(ProductDB))
        existing = {p.name.strip().lower(): p for p in result.scalars().all()}

        added = 0
        backfilled = 0

        for entry in CATALOG:
            product = existing.get(entry["name"].lower())

            if product is None:
                session.add(ProductDB(**entry))
                added += 1
                continue

            changed = False
            if not (product.description or "").strip():
                product.description = entry["description"]
                changed = True
            if not product.image_url:
                product.image_url = entry["image_url"]
                changed = True
            if product.name != entry["name"]:
                product.name = entry["name"]
                changed = True
            if changed:
                backfilled += 1

        await session.commit()
        print(f"[*] Catalog seed complete: {added} added, {backfilled} backfilled")
