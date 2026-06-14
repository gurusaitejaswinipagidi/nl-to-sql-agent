"""
Generates a sample SQLite database with customers, products, and orders tables.
Run once: python data/create_sample_db.py
"""
import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "sample.db")


def create_database():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # ---------- Schema ----------
    cur.execute("""
        CREATE TABLE customers (
            customer_id INTEGER PRIMARY KEY,
            name TEXT NOT NULL,
            city TEXT NOT NULL,
            signup_date TEXT NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE products (
            product_id INTEGER PRIMARY KEY,
            product_name TEXT NOT NULL,
            category TEXT NOT NULL,
            price REAL NOT NULL
        )
    """)

    cur.execute("""
        CREATE TABLE orders (
            order_id INTEGER PRIMARY KEY,
            customer_id INTEGER NOT NULL,
            product_id INTEGER NOT NULL,
            quantity INTEGER NOT NULL,
            order_date TEXT NOT NULL,
            FOREIGN KEY (customer_id) REFERENCES customers(customer_id),
            FOREIGN KEY (product_id) REFERENCES products(product_id)
        )
    """)

    # ---------- Sample Data ----------
    customers = [
        (1, "Aarav Sharma", "Mumbai", "2024-01-15"),
        (2, "Priya Nair", "Bengaluru", "2024-02-10"),
        (3, "Rohan Mehta", "Delhi", "2024-02-20"),
        (4, "Sneha Iyer", "Chennai", "2024-03-05"),
        (5, "Karan Verma", "Pune", "2024-03-18"),
        (6, "Anita Desai", "Hyderabad", "2024-04-01"),
        (7, "Vikram Singh", "Jaipur", "2024-04-12"),
        (8, "Meera Joshi", "Ahmedabad", "2024-05-02"),
        (9, "Arjun Reddy", "Kolkata", "2024-05-20"),
        (10, "Divya Pillai", "Kochi", "2024-06-01"),
    ]

    products = [
        (1, "Wireless Mouse", "Electronics", 599.0),
        (2, "Mechanical Keyboard", "Electronics", 2499.0),
        (3, "USB-C Hub", "Electronics", 1299.0),
        (4, "Office Chair", "Furniture", 7999.0),
        (5, "Standing Desk", "Furniture", 14999.0),
        (6, "Notebook Set", "Stationery", 199.0),
        (7, "Pen Drive 64GB", "Electronics", 699.0),
        (8, "Desk Lamp", "Furniture", 899.0),
        (9, "Whiteboard", "Stationery", 1499.0),
        (10, "Bluetooth Speaker", "Electronics", 1999.0),
    ]

    orders = [
        (1, 1, 1, 2, "2024-06-01"),
        (2, 1, 4, 1, "2024-06-03"),
        (3, 2, 2, 1, "2024-06-05"),
        (4, 3, 5, 1, "2024-06-07"),
        (5, 4, 6, 5, "2024-06-08"),
        (6, 5, 3, 2, "2024-06-10"),
        (7, 2, 10, 1, "2024-06-11"),
        (8, 6, 7, 3, "2024-06-12"),
        (9, 7, 8, 2, "2024-06-13"),
        (10, 8, 9, 1, "2024-06-14"),
        (11, 1, 10, 1, "2024-06-15"),
        (12, 9, 2, 1, "2024-06-16"),
        (13, 10, 1, 4, "2024-06-17"),
        (14, 3, 7, 2, "2024-06-18"),
        (15, 4, 4, 1, "2024-06-19"),
        (16, 5, 5, 1, "2024-06-20"),
        (17, 6, 1, 1, "2024-06-21"),
        (18, 2, 6, 10, "2024-06-22"),
        (19, 7, 3, 1, "2024-06-23"),
        (20, 9, 10, 2, "2024-06-24"),
    ]

    cur.executemany("INSERT INTO customers VALUES (?, ?, ?, ?)", customers)
    cur.executemany("INSERT INTO products VALUES (?, ?, ?, ?)", products)
    cur.executemany("INSERT INTO orders VALUES (?, ?, ?, ?, ?)", orders)

    conn.commit()
    conn.close()
    print(f"Sample database created at {DB_PATH}")


if __name__ == "__main__":
    create_database()
