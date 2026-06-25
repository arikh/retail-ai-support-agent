"""
Database setup and seeding script.
Creates SQLite database with realistic retail pricing data.
Run once to initialize: python data/setup_db.py
"""

import sqlite3
import os
import sys

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

DATABASE_PATH = "data/pricing.db"


def create_tables(conn: sqlite3.Connection) -> None:
    """Create all database tables."""
    cursor = conn.cursor()

    # Pricing Plans table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pricing_plans (
            plan_id         TEXT PRIMARY KEY,
            plan_name       TEXT NOT NULL,
            region          TEXT NOT NULL,
            market          TEXT NOT NULL,
            channel         TEXT NOT NULL,
            season          TEXT NOT NULL,
            status          TEXT NOT NULL,
            created_at      TEXT NOT NULL,
            total_materials INTEGER NOT NULL,
            priced_materials INTEGER NOT NULL
        )
    """)

    # Materials table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS materials (
            material_id     TEXT PRIMARY KEY,
            material_name   TEXT NOT NULL,
            category        TEXT NOT NULL,
            expiry_months   INTEGER,
            active          INTEGER NOT NULL DEFAULT 1
        )
    """)

    # Plan Materials — which materials are in which plan
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS plan_materials (
            id                  INTEGER PRIMARY KEY AUTOINCREMENT,
            plan_id             TEXT NOT NULL,
            material_id         TEXT NOT NULL,
            season              TEXT NOT NULL,
            price_status        TEXT NOT NULL,
            downstream_status   TEXT,
            rejection_reason    TEXT,
            price_value         REAL,
            FOREIGN KEY (plan_id) REFERENCES pricing_plans(plan_id),
            FOREIGN KEY (material_id) REFERENCES materials(material_id)
        )
    """)

    # Pricing Rules table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS pricing_rules (
            rule_id         INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_name       TEXT NOT NULL,
            description     TEXT NOT NULL,
            active          INTEGER NOT NULL DEFAULT 1
        )
    """)

    conn.commit()
    print("✓ Tables created successfully")


def seed_materials(conn: sqlite3.Connection) -> None:
    """Seed materials master data."""
    cursor = conn.cursor()

    materials = [
        ("M-1001", "Winter Jacket XL", "Outerwear", 6, 1),
        ("M-1002", "Summer Dress S", "Apparel", 3, 1),
        ("M-1003", "Running Shoes Size 10", "Footwear", 12, 1),
        ("M-1004", "Leather Belt", "Accessories", 24, 1),
        ("M-1005", "Wool Scarf", "Accessories", 6, 1),
        ("M-1006", "Denim Jeans 32", "Apparel", 12, 1),
        ("M-1007", "Polo Shirt M", "Apparel", 3, 1),
        ("M-1008", "Canvas Tote Bag", "Accessories", 18, 1),
        ("M-1009", "Silk Blouse L", "Apparel", 2, 1),
        ("M-1010", "Formal Trousers 34", "Apparel", 12, 1),
        ("M-1011", "Expired Product A", "Apparel", 1, 1),
        ("M-1012", "Discontinued Item B", "Footwear", None, 0),
        ("M-2001", "Garden Hose 50ft", "Hardware", 24, 1),
        ("M-2002", "Power Drill Set", "Tools", 36, 1),
        ("M-2003", "Paint Brush Set", "Hardware", 12, 1),
        ("M-3001", "Pool Chlorine Tablets", "Pool", 3, 1),
        ("M-3002", "Pool Vacuum Head", "Pool", 24, 1),
        ("M-3003", "Swim Goggles", "Pool", 6, 1),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO materials
        (material_id, material_name, category, expiry_months, active)
        VALUES (?, ?, ?, ?, ?)
    """,
        materials,
    )

    conn.commit()
    print(f"✓ Seeded {len(materials)} materials")


def seed_pricing_rules(conn: sqlite3.Connection) -> None:
    """Seed pricing rules master data."""
    cursor = conn.cursor()

    rules = [
        (
            "EXPIRY_HORIZON_RULE",
            "Material expiry months must be >= plan pricing horizon months. "
            "Example: 6-month plan requires material expiry >= 6 months.",
        ),
        (
            "ACTIVE_MATERIAL_RULE",
            "Only active materials can be included in a pricing plan. "
            "Inactive or discontinued materials are automatically excluded.",
        ),
        (
            "MARKET_MAPPING_RULE",
            "Material must be mapped to the plan region, market, and channel "
            "combination in master data. Missing mapping causes silent exclusion.",
        ),
        (
            "CATEGORY_CHANNEL_RULE",
            "Certain product categories are restricted to specific channels. "
            "Example: Pool products cannot be priced for EU Wholesale channel.",
        ),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO pricing_rules (rule_name, description)
        VALUES (?, ?)
    """,
        rules,
    )

    conn.commit()
    print(f"✓ Seeded {len(rules)} pricing rules")


def seed_plans(conn: sqlite3.Connection) -> None:
    """Seed pricing plans with realistic scenarios."""
    cursor = conn.cursor()

    plans = [
        # Fully completed plan
        (
            "PLAN-001",
            "SUMMER_LATAM_V2",
            "LATAM",
            "Brazil",
            "Wholesale",
            "Summer",
            "COMPLETED",
            "2024-01-15",
            10,
            8,
        ),
        # Plan with missing materials
        (
            "PLAN-002",
            "FALL_EU_2024",
            "EU",
            "Germany",
            "Retail",
            "Fall",
            "COMPLETED",
            "2024-02-10",
            6,
            5,
        ),
        # Plan in progress
        (
            "PLAN-003",
            "WINTER_NA_2024",
            "NA",
            "USA",
            "Wholesale",
            "Winter",
            "IN_PROGRESS",
            "2024-03-01",
            8,
            6,
        ),
        # Plan with downstream issues
        (
            "PLAN-004",
            "SPRING_LATAM_2024",
            "LATAM",
            "Mexico",
            "Retail",
            "Spring",
            "COMPLETED",
            "2024-03-15",
            5,
            5,
        ),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO pricing_plans
        (plan_id, plan_name, region, market, channel, season,
         status, created_at, total_materials, priced_materials)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """,
        plans,
    )

    conn.commit()
    print(f"✓ Seeded {len(plans)} pricing plans")


def seed_plan_materials(conn: sqlite3.Connection) -> None:
    """Seed plan-material relationships with realistic status data."""
    cursor = conn.cursor()

    plan_materials = [
        # PLAN-001: SUMMER_LATAM_V2 — 10 selected, 8 priced, 2 missing
        ("PLAN-001", "M-1001", "Summer", "PRICED", "DOWNSTREAMED", None, 45.99),
        ("PLAN-001", "M-1002", "Summer", "PRICED", "DOWNSTREAMED", None, 29.99),
        ("PLAN-001", "M-1003", "Summer", "PRICED", "DOWNSTREAMED", None, 89.99),
        ("PLAN-001", "M-1004", "Summer", "PRICED", "DOWNSTREAMED", None, 34.99),
        ("PLAN-001", "M-1005", "Summer", "PRICED", "DOWNSTREAMED", None, 19.99),
        ("PLAN-001", "M-1006", "Summer", "PRICED", "DOWNSTREAMED", None, 59.99),
        ("PLAN-001", "M-1007", "Summer", "PRICED", "DOWNSTREAMED", None, 24.99),
        ("PLAN-001", "M-1008", "Summer", "PRICED", "DOWNSTREAMED", None, 14.99),
        (
            "PLAN-001",
            "M-1009",
            "Summer",
            "NOT_PRICED",
            None,
            "EXPIRY_HORIZON_RULE",
            None,
        ),
        (
            "PLAN-001",
            "M-1011",
            "Summer",
            "NOT_PRICED",
            None,
            "EXPIRY_HORIZON_RULE",
            None,
        ),
        # PLAN-002: FALL_EU_2024 — 6 selected, 5 priced, 1 missing
        ("PLAN-002", "M-1001", "Fall", "PRICED", "DOWNSTREAMED", None, 52.99),
        ("PLAN-002", "M-1004", "Fall", "PRICED", "DOWNSTREAMED", None, 36.99),
        ("PLAN-002", "M-1005", "Fall", "PRICED", "DOWNSTREAMED", None, 22.99),
        ("PLAN-002", "M-1006", "Fall", "PRICED", "DOWNSTREAMED", None, 64.99),
        ("PLAN-002", "M-1010", "Fall", "PRICED", "DOWNSTREAMED", None, 74.99),
        (
            "PLAN-002",
            "M-3001",
            "Fall",
            "NOT_PRICED",
            None,
            "CATEGORY_CHANNEL_RULE",
            None,
        ),
        # PLAN-003: WINTER_NA_2024 — 8 selected, 6 priced, 2 missing
        ("PLAN-003", "M-1001", "Winter", "PRICED", "PENDING", None, 67.99),
        ("PLAN-003", "M-1003", "Winter", "PRICED", "PENDING", None, 94.99),
        ("PLAN-003", "M-1004", "Winter", "PRICED", "PENDING", None, 38.99),
        ("PLAN-003", "M-1005", "Winter", "PRICED", "PENDING", None, 27.99),
        ("PLAN-003", "M-1006", "Winter", "PRICED", "PENDING", None, 72.99),
        ("PLAN-003", "M-1010", "Winter", "PRICED", "PENDING", None, 82.99),
        (
            "PLAN-003",
            "M-1011",
            "Winter",
            "NOT_PRICED",
            None,
            "EXPIRY_HORIZON_RULE",
            None,
        ),
        (
            "PLAN-003",
            "M-1012",
            "Winter",
            "NOT_PRICED",
            None,
            "ACTIVE_MATERIAL_RULE",
            None,
        ),
        # PLAN-004: SPRING_LATAM_2024 — 5 selected, 5 priced, downstream issues
        ("PLAN-004", "M-1002", "Spring", "PRICED", "DOWNSTREAMED", None, 31.99),
        ("PLAN-004", "M-1003", "Spring", "PRICED", "DOWNSTREAMED", None, 91.99),
        ("PLAN-004", "M-1006", "Spring", "PRICED", "DOWNSTREAMED", None, 61.99),
        ("PLAN-004", "M-1007", "Spring", "PRICED", "FAILED", None, 26.99),
        ("PLAN-004", "M-1008", "Spring", "PRICED", "FAILED", None, 16.99),
    ]

    cursor.executemany(
        """
        INSERT OR IGNORE INTO plan_materials
        (plan_id, material_id, season, price_status,
         downstream_status, rejection_reason, price_value)
        VALUES (?, ?, ?, ?, ?, ?, ?)
    """,
        plan_materials,
    )

    conn.commit()
    print(f"✓ Seeded {len(plan_materials)} plan-material records")


def verify_database(conn: sqlite3.Connection) -> None:
    """Print summary of seeded data for verification."""
    cursor = conn.cursor()

    print("\n--- Database Verification ---")

    cursor.execute("SELECT COUNT(*) FROM materials")
    print(f"Materials:      {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM pricing_plans")
    print(f"Pricing Plans:  {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM plan_materials")
    print(f"Plan Materials: {cursor.fetchone()[0]}")

    cursor.execute("SELECT COUNT(*) FROM pricing_rules")
    print(f"Pricing Rules:  {cursor.fetchone()[0]}")

    print("\n--- Plans Summary ---")
    cursor.execute("""
        SELECT plan_name, region, status, total_materials, priced_materials
        FROM pricing_plans
    """)
    for row in cursor.fetchall():
        print(
            f"  {row[0]:<25} {row[1]:<6} {row[2]:<12} "
            f"{row[4]}/{row[3]} materials priced"
        )

    print("\n--- Missing Materials ---")
    cursor.execute("""
        SELECT pp.plan_name, pm.material_id, pm.rejection_reason
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        WHERE pm.price_status = 'NOT_PRICED'
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]:<25} {row[1]:<8} Reason: {row[2]}")

    print("\n--- Downstream Issues ---")
    cursor.execute("""
        SELECT pp.plan_name, pm.material_id, pm.downstream_status
        FROM plan_materials pm
        JOIN pricing_plans pp ON pm.plan_id = pp.plan_id
        WHERE pm.downstream_status IN ('FAILED', 'PENDING')
    """)
    for row in cursor.fetchall():
        print(f"  {row[0]:<25} {row[1]:<8} Status: {row[2]}")


def main() -> None:
    """Main entry point."""
    print("Setting up pricing database...")
    print(f"Database path: {DATABASE_PATH}\n")

    # Ensure data directory exists
    os.makedirs("data", exist_ok=True)

    # Ensure logs directory exists
    os.makedirs("logs", exist_ok=True)

    conn = sqlite3.connect(DATABASE_PATH)

    try:
        create_tables(conn)
        seed_materials(conn)
        seed_pricing_rules(conn)
        seed_plans(conn)
        seed_plan_materials(conn)
        verify_database(conn)
        print("\n✓ Database setup complete")
    except Exception as e:
        print(f"\n✗ Database setup failed: {e}")
        raise
    finally:
        conn.close()


if __name__ == "__main__":
    main()
