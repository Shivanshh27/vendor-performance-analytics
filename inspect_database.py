import sqlite3

DB_PATH = "vendor.db"

connection = sqlite3.connect(DB_PATH)
cursor = connection.cursor()

# Step 1: List all tables
cursor.execute("""
    SELECT name
    FROM sqlite_master
    WHERE type = 'table'
    ORDER BY name;
""")

tables = cursor.fetchall()

print("\nDATABASE TABLES")
print("=" * 50)

for table in tables:
    table_name = table[0]

    print(f"\nTable: {table_name}")

    # Step 2: Inspect the schema
    cursor.execute(f'PRAGMA table_info("{table_name}")')
    columns = cursor.fetchall()

    print("\nColumns:")

    for column in columns:
        print(f"  {column[1]} : {column[2]}")

    # Step 3: Count records
    cursor.execute(f'SELECT COUNT(*) FROM "{table_name}"')
    row_count = cursor.fetchone()[0]

    print(f"\nTotal rows: {row_count:,}")

    # Step 4: Display sample records
    cursor.execute(f'SELECT * FROM "{table_name}" LIMIT 3')
    records = cursor.fetchall()

    print("\nSample records:")

    for record in records:
        print(record)

    print("-" * 50)

connection.close()