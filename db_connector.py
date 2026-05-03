import psycopg2
from pymongo import MongoClient
from bson.objectid import ObjectId # Added for MongoDB
import mysql.connector
import datetime

class DBConnector:
    def __init__(self, connection_details):
        self.connection_details = connection_details
        self.connection = None
        self.cursor = None # For SQL databases

    def connect(self, silent=False):
        raise NotImplementedError

    def disconnect(self, silent=False):
        if self.connection:
            if self.cursor:
                self.cursor.close()
            self.connection.close()
            self.connection = None
            self.cursor = None
            if not silent:
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

    def fetch_primary_keys(self, table_name):
        return [], None

    def fetch_unique_columns(self, table_name):
        return {}

    def fetch_column_defaults(self, table_name):
        return {}

    def evaluate_expression(self, expr: str) -> str:
        return ""

class PostgreSQLConnector(DBConnector):
    def connect(self, silent=False):
        try:
            self.connection = psycopg2.connect(
                host=self.connection_details.get("host"),
                port=self.connection_details.get("port"),
                user=self.connection_details.get("user"),
                password=self.connection_details.get("password"),
                database=self.connection_details.get("database")
            )
            self.cursor = self.connection.cursor()
            if not silent:
                print(f"Connected to PostgreSQL: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            if not silent:
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
                self.cursor.execute(
                    "SELECT column_name, data_type FROM information_schema.columns "
                    "WHERE table_name = %s AND table_schema = 'public' "
                    "ORDER BY ordinal_position;",
                    (table,)
                )
                columns = [{"name": col[0], "type": col[1]} for col in self.cursor.fetchall()]
                schema["tables"][table] = {"columns": columns}
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
            self.cursor.execute(f'SELECT * FROM "{table_name}";')
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            return True, {"columns": columns, "rows": rows}
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def insert_data(self, table_name, data):
        if not self.connection:
            return False, "Not connected."
        try:
            columns = ', '.join(f'"{k}"' for k in data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f'INSERT INTO "{table_name}" ({columns}) VALUES ({placeholders});'
            self.cursor.execute(query, list(data.values()))
            self.connection.commit()
            print(f"Table '{table_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Inserted 1 row into {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def update_data(self, table_name, data, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            set_clauses = [f'"{col}" = %s' for col in data.keys()]
            set_clause_str = ', '.join(set_clauses)

            where_clauses = [f'"{col}" = %s' for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f'UPDATE "{table_name}" SET {set_clause_str} WHERE {where_clause_str};'
            params = list(data.values()) + list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            print(f"Table '{table_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Updated {self.cursor.rowcount} rows in {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def delete_data(self, table_name, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            where_clauses = [f'"{col}" = %s' for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f'DELETE FROM "{table_name}" WHERE {where_clause_str};'
            params = list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            print(f"Table '{table_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Deleted {self.cursor.rowcount} rows from {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def fetch_primary_keys(self, table_name):
        if not self.connection:
            return [], None
        try:
            self.cursor.execute("""
                SELECT kcu.column_name, tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = %s
                  AND tc.constraint_type = 'PRIMARY KEY'
                  AND tc.table_schema = 'public'
                ORDER BY kcu.ordinal_position;
            """, (table_name,))
            rows = self.cursor.fetchall()
            cols = [r[0] for r in rows]
            constraint_name = rows[0][1] if rows else None
            return cols, constraint_name
        except Exception as e:
            self.connection.rollback()
            return [], None

    def fetch_unique_columns(self, table_name):
        if not self.connection:
            return {}
        try:
            self.cursor.execute("""
                SELECT kcu.column_name, tc.constraint_name
                FROM information_schema.table_constraints tc
                JOIN information_schema.key_column_usage kcu
                  ON tc.constraint_name = kcu.constraint_name
                  AND tc.table_schema = kcu.table_schema
                WHERE tc.table_name = %s
                  AND tc.constraint_type = 'UNIQUE'
                  AND tc.table_schema = 'public';
            """, (table_name,))
            return {r[0]: r[1] for r in self.cursor.fetchall()}
        except Exception as e:
            self.connection.rollback()
            return {}

    def fetch_column_defaults(self, table_name):
        """Returns {col_name: {"default": str|None, "is_identity": bool}} for each column."""
        if not self.connection:
            return {}
        try:
            self.cursor.execute("""
                SELECT column_name, column_default, is_identity
                FROM information_schema.columns
                WHERE table_name = %s AND table_schema = 'public'
                ORDER BY ordinal_position;
            """, (table_name,))
            result = {}
            for col_name, col_default, is_identity in self.cursor.fetchall():
                result[col_name] = {
                    "default": col_default,
                    "is_identity": (is_identity == "YES"),
                }
            return result
        except Exception as e:
            self.connection.rollback()
            return {}

    def evaluate_expression(self, expr: str) -> str:
        """Run SELECT (expr) and return the result as a string — used to generate sample values."""
        if not self.connection or not expr:
            return ""
        try:
            self.cursor.execute(f"SELECT ({expr})")
            row = self.cursor.fetchone()
            return str(row[0]) if row and row[0] is not None else ""
        except Exception:
            self.connection.rollback()
            return ""


class MongoDBConnector(DBConnector):
    def connect(self, silent=False):
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

            self.connection = MongoClient(uri, serverSelectionTimeoutMS=5000)
            self.db = self.connection[database] # Select the database
            # The ping command is cheap and does not require auth.
            self.connection.admin.command('ping') 
            if not silent:
                print(f"Connected to MongoDB: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            if not silent:
                print(f"MongoDB connection error: {e}")
            return False

    def disconnect(self, silent=False):
        if self.connection:
            self.connection.close()
            self.connection = None
            self.db = None
            if not silent:
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
            print(f"Collection '{collection_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Inserted document with ID: {result.inserted_id}"
        except Exception as e:
            return False, str(e)

    def update_data(self, collection_name, query_filter, update_data):
        if not self.db:
            return False, "Not connected."
        try:
            result = self.db[collection_name].update_many(query_filter, {"$set": update_data})
            print(f"Collection '{collection_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Matched {result.matched_count} documents, modified {result.modified_count}."
        except Exception as e:
            return False, str(e)

    def delete_data(self, collection_name, query_filter):
        if not self.db:
            return False, "Not connected."
        try:
            result = self.db[collection_name].delete_many(query_filter)
            print(f"Collection '{collection_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Deleted {result.deleted_count} documents."
        except Exception as e:
            return False, str(e)


class MySQLMariaDBConnector(DBConnector):
    def connect(self, silent=False):
        try:
            self.connection = mysql.connector.connect(
                host=self.connection_details.get("host"),
                port=self.connection_details.get("port"),
                user=self.connection_details.get("user"),
                password=self.connection_details.get("password"),
                database=self.connection_details.get("database")
            )
            self.cursor = self.connection.cursor()
            if not silent:
                print(f"Connected to MySQL/MariaDB: {self.connection_details.get('name')}")
            return True
        except Exception as e:
            if not silent:
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
            self.cursor.execute(f"SELECT * FROM `{table_name}`;")
            columns = [desc[0] for desc in self.cursor.description]
            rows = self.cursor.fetchall()
            return True, {"columns": columns, "rows": rows}
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def insert_data(self, table_name, data):
        if not self.connection:
            return False, "Not connected."
        try:
            columns = ', '.join(f'`{k}`' for k in data.keys())
            placeholders = ', '.join(['%s'] * len(data))
            query = f"INSERT INTO `{table_name}` ({columns}) VALUES ({placeholders});"
            self.cursor.execute(query, list(data.values()))
            self.connection.commit()
            print(f"Table '{table_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Inserted 1 row into {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def update_data(self, table_name, data, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            set_clauses = [f'`{col}` = %s' for col in data.keys()]
            set_clause_str = ', '.join(set_clauses)

            where_clauses = [f'`{col}` = %s' for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"UPDATE `{table_name}` SET {set_clause_str} WHERE {where_clause_str};"
            params = list(data.values()) + list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            print(f"Table '{table_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Updated {self.cursor.rowcount} rows in {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def delete_data(self, table_name, condition):
        if not self.connection:
            return False, "Not connected."
        try:
            where_clauses = [f'`{col}` = %s' for col in condition.keys()]
            where_clause_str = ' AND '.join(where_clauses)

            query = f"DELETE FROM `{table_name}` WHERE {where_clause_str};"
            params = list(condition.values())
            self.cursor.execute(query, params)
            self.connection.commit()
            print(f"Table '{table_name}' in '{self.connection_details.get('name')}' edited at {datetime.datetime.now()}")
            return True, f"Deleted {self.cursor.rowcount} rows from {table_name}."
        except Exception as e:
            self.connection.rollback()
            return False, str(e)

    def fetch_primary_keys(self, table_name):
        if not self.connection:
            return [], None
        try:
            self.cursor.execute("""
                SELECT COLUMN_NAME FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_NAME = %s AND CONSTRAINT_NAME = 'PRIMARY'
                  AND TABLE_SCHEMA = DATABASE()
                ORDER BY ORDINAL_POSITION;
            """, (table_name,))
            cols = [r[0] for r in self.cursor.fetchall()]
            return cols, 'PRIMARY' if cols else None
        except Exception as e:
            self.connection.rollback()
            return [], None

    def fetch_unique_columns(self, table_name):
        if not self.connection:
            return {}
        try:
            self.cursor.execute("""
                SELECT COLUMN_NAME, CONSTRAINT_NAME
                FROM information_schema.KEY_COLUMN_USAGE
                WHERE TABLE_NAME = %s
                  AND TABLE_SCHEMA = DATABASE()
                  AND CONSTRAINT_NAME != 'PRIMARY';
            """, (table_name,))
            return {r[0]: r[1] for r in self.cursor.fetchall()}
        except Exception as e:
            self.connection.rollback()
            return {}


def get_connector(connection_details):
    db_type = connection_details.get("db_type")
    if db_type == "PostgreSQL":
        return PostgreSQLConnector(connection_details)
    elif db_type == "MongoDB":
        return MongoDBConnector(connection_details)
    elif db_type == "MariaDB" or db_type == "MySQL": # MariaDB uses MySQL connector
        return MySQLMariaDBConnector(connection_details)
    else:
        raise ValueError(f"Unsupported database type: {db_type}")