import sqlite3
import os

db_path = os.path.join('data', 'database.db')
conn = sqlite3.connect(db_path)
tables = [('projects', 'featured_image'), ('project_images', 'image_path'), ('service_categories', 'hero_image'), ('services', 'image'), ('blog_posts', 'featured_image')]
for table, col in tables:
    try:
        conn.execute(f"UPDATE {table} SET {col} = REPLACE({col}, '/static/uploads/', '/uploads/')")
    except Exception as e:
        print(f"Error on {table}: {e}")
conn.commit()
conn.close()
print("DB paths updated.")
