import psycopg2
from pymongo import MongoClient
from bson.objectid import ObjectId # Added for MongoDB
import mysql.connector
import sqlite3

class DBConnector:
    def __init__(self, connection_details):
        self.connection_details = connection_details
        self.connection = None
        self.cursor = None # For SQL databases

    def connect(self):
        raise NotImplementedError

    def disconnect(self):
        if self.connection:
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            self.connection = None
            self.cursor = None
            print(f"Disconnected from {self.connection_details.get('name')}")

    def execute_query(self, query):
        raise NotImplementedError

    def fetch_schema(self):
        raise NotImplementedError

    def fetch_data(self, table_name):
        raise NotImplementedError

    def insert_data(self, table_name, data):
        raise NotImplementedError

    def update_data(self, table_name, data, condition):
        raise NotImplementedError

    def delete_data(self, table_name, condition):
        raise NotImplementedError

class PostgreSQLConnector(DBConnector):
    def connect(self):
        try:
            self.connection = psycopg2.connect(
                host=self.connection_details.get("host"),
                port=self.connection_details.get("port"),
                user=self.connection_details.get("user"),
                password=self.connection_details.get("password"),
                database=self.connection_details.get("database")
            )
            self.cursor = self.connection.cursor()
            print(f"Connected to PostgreSQL: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            print(f"PostgreSQL connection error: {e}")
            return False

    def fetch_schema(self):
        if not self.connection:
            return None
        try:
            self.cursor.execute("""
                SELECT table_name FROM information_schema.tables
                WHERE table_schema = 'public' AND table_type = 'BASE TABLE';
            """)
            tables = [row[0] for row in self.cursor.fetchall()]
            schema = {"tables": {}}
            for table in tables:
                self.cursor.execute(f"SELECT column_name, data_type FROM information_schema.columns WHERE table_name = '{table}';")
                columns = [{"name": col[0], "type": col[1]} for col in self.cursor.fetchall()]
                schema["tables"][table] = {"columns": columns}
            print(f"PostgreSQL fetch_schema returning: {schema}") # Debug print
            return schema
        except Exception as e:
            print(f"Error fetching PostgreSQL schema: {e}")
            return None

    def execute_query(self, query):
        if not self.connection:
            return False, "Not connected to database."
        try:
            self.cursor.execute(query)
            if self.cursor.description: # It's a SELECT query
                columns = [desc[0] for desc in self.cursor.description]
                results = self.cursor.fetchall()
                return True, {"columns": columns, "rows": results}
            else: # It's an INSERT, UPDATE, DELETE, or DDL query
                self.connection.commit()
                return True, {"message": f"Query executed successfully. Rows affected: {self.cursor.rowcount}"}
        except Exception as e:
            self.connection.rollback() # Rollback on error for transactional databases
            return False, str(e)

    def fetch_data(self, table_name):
        if not self.connection:
            return False, "Not connected."
        try:
            self.cursor.execute(f"SELECT * FROM {table_name};")
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            return True, {"columns": columns, "rows": rows}
        except Exception as e:
            return False, str(e)

    def insert_data(self, table_name, data):
        if not self.connection:
            return False, "Not connected."
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
            self.cursor.execute(query, list(data.values()))
            self.connection.commit()
            return True, f"Inserted 1 row into {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def update_data(self, table_name, data, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            set_clauses = [f"{col} = %s" for col in data.keys()]
            set_clause_str = ', '.join(set_clauses)
            
            # Assuming condition is a dictionary like {"id": 1}
            where_clauses = [f"{col} = %s" for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"UPDATE {table_name} SET {set_clause_str} WHERE {where_clause_str};"
            params = list(data.values()) + list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            return True, f"Updated {self.cursor.rowcount} rows in {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def delete_data(self, table_name, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            # Assuming condition is a dictionary like {"id": 1}
            where_clauses = [f"{col} = %s" for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"DELETE FROM {table_name} WHERE {where_clause_str};"
            params = list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            return True, f"Deleted {self.cursor.rowcount} rows from {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)


class MongoDBConnector(DBConnector):
    def connect(self):
        try:
            # MongoDB connection string can be complex, simplifying for now
            # For production, consider more robust URI construction and authentication
            user = self.connection_details.get('user')
            password = self.connection_details.get('password')
            host = self.connection_details.get('host')
            port = self.connection_details.get('port')
            database = self.connection_details.get('database')

            if user and password:
                uri = f"mongodb://{user}:{password}@{host}:{port}/"
            else:
                uri = f"mongodb://{host}:{port}/"

            self.connection = MongoClient(uri)
            self.db = self.connection[database] # Select the database
            # The ping command is cheap and does not require auth.
            self.connection.admin.command('ping') 
            print(f"Connected to MongoDB: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            print(f"MongoDB connection error: {e}")
            return False

    def disconnect(self):
        if self.connection:
            self.connection.close()
            self.connection = None
            self.db = None
            print(f"Disconnected from {self.connection_details.get('name')}")

    def fetch_schema(self):
        if not self.db:
            return None
        try:
            collections = self.db.list_collection_names()
            schema = {"collections": {}}
            for col_name in collections:
                # For MongoDB, schema is dynamic. We can sample documents.
                # For simplicity, we'll just list collection names for now.
                # A more advanced implementation would sample documents to infer schema.
                schema["collections"][col_name] = {"fields": "dynamic (sample to infer)"}
            print(f"MongoDB fetch_schema returning: {schema}") # Debug print
            return schema
        except Exception as e:
            print(f"Error fetching MongoDB schema: {e}")
            return None

    def execute_query(self, query):
        if not self.db:
            return False, "Not connected to database."
        try:
            # For MongoDB, a "query" can be a Python dictionary representing a find operation,
            # or a command to be executed. This is a simplified approach.
            # A more robust solution would parse the query string or provide specific UI for operations.
            # For now, let's assume 'query' is a collection name for a find operation.
            # Or a simple command like db.collection.find({})
            
            # Example: query = "my_collection.find({})"
            parts = query.split('.')
            if len(parts) >= 2 and parts[1].startswith('find'):
                collection_name = parts[0]
                # This is a very basic parsing. Needs improvement for real-world use.
                # For now, assume find({}) means all documents.
                results = list(self.db[collection_name].find({}))
                if results:
                    # Extract keys from the first document to use as columns
                    all_keys = set()
                    for doc in results:
                        all_keys.update(doc.keys())
                    columns = sorted(list(all_keys), key=lambda x: (x != '_id', x)) # _id first

                    # Convert ObjectId to string for display
                    rows = []
                    for doc in results:
                        row = []
                        for col in columns:
                            val = doc.get(col)
                            if isinstance(val, ObjectId):
                                row.append(str(val))
                            else:
                                row.append(val)
                        rows.append(row)
                    return True, {"columns": columns, "rows": rows}
                else:
                    return True, {"message": "No documents found.", "columns": [], "rows": []}
            else:
                return False, "Unsupported MongoDB query format. Try 'collection_name.find({})'."
        except Exception as e:
            return False, str(e)

    def fetch_data(self, collection_name):
        if not self.db:
            return False, "Not connected."
        try:
            results = list(self.db[collection_name].find({}))
            if results:
                # Extract all unique keys from all documents to form columns
                all_keys = set()
                for doc in results:
                    all_keys.update(doc.keys())
                columns = sorted(list(all_keys), key=lambda x: (x != '_id', x)) # _id first

                rows = []
                for doc in results:
                    row = []
                    for col in columns:
                        val = doc.get(col)
                        if isinstance(val, ObjectId):
                            row.append(str(val))
                        else:
                            row.append(val)
                    rows.append(row)
                return True, {"columns": columns, "rows": rows}
            else:
                return True, {"columns": [], "rows": []}
        except Exception as e:
            return False, str(e)

    def insert_data(self, collection_name, data):
        if not self.db:
            return False, "Not connected."
        try:
            result = self.db[collection_name].insert_one(data)
            return True, f"Inserted document with ID: {result.inserted_id}"
        except Exception as e:
            return False, str(e)

    def update_data(self, collection_name, query_filter, update_data):
        if not self.db:
            return False, "Not connected."
        try:
            result = self.db[collection_name].update_many(query_filter, {"$set": update_data})
            return True, f"Matched {result.matched_count} documents, modified {result.modified_count}."
        except Exception as e:
            return False, str(e)

    def delete_data(self, collection_name, query_filter):
        if not self.db:
            return False, "Not connected."
        try:
            result = self.db[collection_name].delete_many(query_filter)
            return True, f"Deleted {result.deleted_count} documents."
        except Exception as e:
            return False, str(e)


class MySQLMariaDBConnector(DBConnector):
    def connect(self):
        try:
            self.connection = mysql.connector.connect(
                host=self.connection_details.get("host"),
                port=self.connection_details.get("port"),
                user=self.connection_details.get("user"),
                password=self.connection_details.get("password"),
                database=self.connection_details.get("database")
            )
            self.cursor = self.connection.cursor()
            print(f"Connected to MySQL/MariaDB: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            print(f"MySQL/MariaDB connection error: {e}")
            return False

    def fetch_schema(self):
        if not self.connection:
            return None
        try:
            self.cursor.execute("SHOW TABLES;")
            tables = [row[0] for row in self.cursor.fetchall()]
            schema = {"tables": {}}
            for table in tables:
                self.cursor.execute(f"DESCRIBE {table};")
                columns = [{"name": col[0], "type": col[1]} for col in self.cursor.fetchall()]
                schema["tables"][table] = {"columns": columns}
            print(f"MySQL/MariaDB fetch_schema returning: {schema}") # Debug print
            return schema
        except Exception as e:
            print(f"Error fetching MySQL/MariaDB schema: {e}")
            return None

    def execute_query(self, query):
        if not self.connection:
            return False, "Not connected to database."
        try:
            self.cursor.execute(query)
            if self.cursor.description: # It's a SELECT query
                columns = [desc[0] for desc in self.cursor.description]
                results = self.cursor.fetchall()
                return True, {"columns": columns, "rows": results}
            else: # It's an INSERT, UPDATE, DELETE, or DDL query
                self.connection.commit()
                return True, {"message": f"Query executed successfully. Rows affected: {self.cursor.rowcount}"}
        except Exception as e:
            self.connection.rollback() # Rollback on error for transactional databases
            return False, str(e)

    def fetch_data(self, table_name):
        if not self.connection:
            return False, "Not connected."
        try:
            self.cursor.execute(f"SELECT * FROM {table_name};")
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            return True, {"columns": columns, "rows": rows}
        except Exception as e:
            return False, str(e)

    def insert_data(self, table_name, data):
        if not self.connection:
            return False, "Not connected."
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
            self.cursor.execute(query, list(data.values()))
            self.connection.commit()
            return True, f"Inserted 1 row into {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def update_data(self, table_name, data, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            set_clauses = [f"{col} = %s" for col in data.keys()]
            set_clause_str = ', '.join(set_clauses)
            
            where_clauses = [f"{col} = %s" for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"UPDATE {table_name} SET {set_clause_str} WHERE {where_clause_str};"
            params = list(data.values()) + list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            return True, f"Updated {self.cursor.rowcount} rows in {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def delete_data(self, table_name, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            where_clauses = [f"{col} = %s" for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"DELETE FROM {table_name} WHERE {where_clause_str};"
            params = list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            return True, f"Deleted {self.cursor.rowcount} rows from {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)


class SQLiteConnector(DBConnector):
    def connect(self):
        try:
            # For SQLite, host is the path to the database file, or just the database name
            db_path = self.connection_details.get("database")
            if not db_path:
                raise ValueError("SQLite database path cannot be empty.")
            self.connection = sqlite3.connect(db_path)
            self.cursor = self.connection.cursor()
            print(f"Connected to SQLite: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            print(f"SQLite connection error: {e}")
            return False

    def fetch_schema(self):
        if not self.connection:
            return None
        try:
            self.cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
            tables = [row[0] for row in self.cursor.fetchall()]
            schema = {"tables": {}}
            for table in tables:
                self.cursor.execute(f"PRAGMA table_info({table});")
                columns = [{"name": col[1], "type": col[2]} for col in self.cursor.fetchall()]
                schema["tables"][table] = {"columns": columns}
            print(f"SQLite fetch_schema returning: {schema}") # Debug print
            return schema
        except Exception as e:
            print(f"Error fetching SQLite schema: {e}")
            return None

    def execute_query(self, query):
        if not self.connection:
            return False, "Not connected to database."
        try:
            self.cursor.execute(query)
            if self.cursor.description: # It's a SELECT query
                columns = [desc[0] for desc in self.cursor.description]
                results = self.cursor.fetchall()
                return True, {"columns": columns, "rows": results}
            else: # It's an INSERT, UPDATE, DELETE, or DDL query
                self.connection.commit()
                return True, {"message": f"Query executed successfully. Rows affected: {self.cursor.rowcount}"}
        except Exception as e:
            self.connection.rollback() # Rollback on error for transactional databases
            return False, str(e)

    def fetch_data(self, table_name):
        if not self.connection:
            return False, "Not connected."
        try:
            self.cursor.execute(f"SELECT * FROM {table_name};")
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            return True, {"columns": columns, "rows": rows}
        except Exception as e:
            return False, str(e)

    def insert_data(self, table_name, data):
        if not self.connection:
            return False, "Not connected."
        try:
            columns = ', '.join(data.keys())
            placeholders = ', '.join(['?'] * len(data))
            query = f"INSERT INTO {table_name} ({columns}) VALUES ({placeholders});"
            self.cursor.execute(query, list(data.values()))
            self.connection.commit()
            return True, f"Inserted 1 row into {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def update_data(self, table_name, data, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            set_clauses = [f"{col} = ?" for col in data.keys()]
            set_clause_str = ', '.join(set_clauses)
            
            where_clauses = [f"{col} = ?" for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"UPDATE {table_name} SET {set_clause_str} WHERE {where_clause_str};"
            params = list(data.values()) + list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            return True, f"Updated {self.cursor.rowcount} rows in {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def delete_data(self, table_name, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            where_clauses = [f"{col} = ?" for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"DELETE FROM {table_name} WHERE {where_clause_str};"
            params = list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            return True, f"Deleted {self.cursor.rowcount} rows from {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)


def get_connector(connection_details):
    db_type = connection_details.get("db_type")
    if db_type == "PostgreSQL":
        return PostgreSQLConnector(connection_details)
    elif db_type == "MongoDB":
        return MongoDBConnector(connection_details)
    elif db_type == "MariaDB" or db_type == "MySQL": # MariaDB uses MySQL connector
        return MySQLMariaDBConnector(connection_details)
    elif db_type == "SQLite":
        return SQLiteConnector(connection_details)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")