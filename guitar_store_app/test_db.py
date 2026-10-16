import psycopg2

conn = psycopg2.connect("postgresql://postgres:123@localhost:5432/guitar_store")
cur = conn.cursor()

cur.execute("""
    SELECT table_name FROM information_schema.tables
    WHERE table_schema = 'public'
    ORDER BY table_name;
""")
tables = [r[0] for r in cur.fetchall()]
print("Таблицы:", tables, "\n")

for t in tables:
    cur.execute("""
        SELECT column_name, data_type, is_nullable, column_default
        FROM information_schema.columns
        WHERE table_name = %s
        ORDER BY ordinal_position;
    """, (t,))
    print(f"=== {t} ===")
    for col, dtype, nullable, default in cur.fetchall():
        print(f"  {col:<25} {dtype:<20} null={nullable} default={default}")

    cur.execute("SELECT COUNT(*) FROM " + t)
    print(f"  строк: {cur.fetchone()[0]}\n")

conn.close()