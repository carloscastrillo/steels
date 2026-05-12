import sqlite3
conn = sqlite3.connect('db/steel_mvp.db')
conn.execute("DROP TABLE IF EXISTS quotes")
conn.commit()
print("Tabla 'quotes' eliminada.")