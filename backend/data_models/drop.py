import psycopg2
from psycopg2 import sql


def drop_all_tables():
    # Database connection details
    conn = psycopg2.connect(
        dbname="db",
        user="ardsnijders",
        password="",
        host="localhost",  # or the host of your database
        port="5432"  # or the port of your PostgreSQL server
    )
    
    try:
        # Create a cursor object to interact with the database
        cursor = conn.cursor()
        
        # Retrieve a list of all table names in the public schema
        cursor.execute("""
            SELECT table_name
            FROM information_schema.tables
            WHERE table_schema = 'public';
        """)
        
        # Fetch all the table names
        tables = cursor.fetchall()
        
        # Drop each table in the list
        for table in tables:
            table_name = table[0]
            print(f"Dropping table {table_name}")
            cursor.execute(sql.SQL("DROP TABLE IF EXISTS {} CASCADE;").format(sql.Identifier(table_name)))
        
        # Commit the changes
        conn.commit()
        print("All tables dropped successfully.")
        
    except Exception as e:
        print(f"Error dropping tables: {e}")
        conn.rollback()  # Rollback in case of an error
    
    finally:
        # Close the cursor and connection
        cursor.close()
        conn.close()

# Call the function to drop all tables
drop_all_tables()