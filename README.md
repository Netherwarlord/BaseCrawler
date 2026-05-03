# BaseCrawler – A Modern, Feature‑Rich Database Management Tool
### “A powerful, lightweight crawler that extracts structured data from relational & document stores, gives you instant visibility into schema evolution, and lets you script your own workflows.”

License GitHub Tag GitHub Language Count

## Table of Contents
### Section
<ol>
    <li>Overview</li>
    <li>Features</li>
    <li>Prerequisites & Installation</li>
    <li>Getting Started</li>
    <li>Usage Examples</li>
    <li>Configuration</li>
    <li>Advanced Options</li>
    <li>Scripts & API</li>
    <li>Contributing</li>
    <li>Roadmap</li>
    <li>License</li>
</ol>

## 1. Overview
BaseCrawler is a command‑line / GUI tool that lets you:
<ul>
    <li>Catalog, explore and export schemas from virtually any relational or document database (MySQL, PostgreSQL, SQLite, MongoDB, Cassandra, DynamoDB, etc.).</li>
    <li>Run ad‑hoc queries against the discovered schema.
Export results to CSV/JSON files for downstream analysis.
Automate repetitive maintenance tasks (e.g., rename columns, purge old tables, generate documentation).</li>
    <li>It’s written in Python 3.9+ and uses a lightweight dependency tree (pandas, sqlalchemy, requests, pydantic, etc.) making it fast to start and easy to run on any OS.</li>
</ul>




## 2. Features
<center>
    <table>
        <tr>
            <td>Category</td><td>Feature</td>
        </tr>
        <tr>
            <td>Core</td>
            <td>
                <ul>
                    <li>Discover & enumerate tables/fields/columns</li>
                    <li>Resolve Primary/Foreign Keys</li>
                    <li>Detect data types (int, float, string, enum).</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Data Export</td>
            <td>
                <ul>
                    <li>One-click CSV eport per table</li>
                    <li>Bulk JSON export of entire schema</li>
                    <li>Filter by column name or type</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Query Engine</td>
            <td>
                <ul>
                    <li>Built-in SQL editor with syntax highlighting & auto-completion</li>
                    <li>Execute arbitrary queries and view results inline</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Automation</td>
            <td>
                <ul>
                    <li>Scriptable API for programatic discovery (REST)</li>
                    <li>Export scripts to generate migrations, ETL jobs, etc.</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Visualization</td>
            <td>
                <ul>
                    <li>Interactive GUI mode that shows a tree of tables.</li>
                    <li>Quick preview of first 10 rows per table.</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Extensibility</td>
            <td>
                <ul>
                    <li>Custom plugins via plugins/ folder (e.g., add new DB driver).</li>
                </ul>
            </td>
        </tr>
        <tr><td></td><td></td></tr>
    </table>
</center>

## 3. Prerequisites & Installation
### Using pip (recommended)
```bash
pip install -U git+https://github.com/Netherwarlord/BaseCrawler.git
```

### Or, clone the repo and install from source
```bash
git clone https://github.com/Netherwarlord/BaseCrawler.git
cd BaseCrawler
```
```bash
python -m venv .venv   # create a virtual env (Linux/macOS)
source .venv/bin/activate  # activate it on macOS/Linux
pip install -r requirements.txt
```

### macOS specific flag
```bash
 brew link --force --overwrite python
```

### Verify installation
```bash
basecrawler --version   # should print the version number
```
###### Note – If you prefer Docker, a minimal image is also available:

```bash
docker run -it netherwarlord/basecrawler:latest /bin/sh -c "basecrawler"
```

## 4. Getting Started

### Connect to your database

```bash
basecrawler connect \
  --host localhost \
  --port 5432 \
  --user postgres \
  --password mySecretPass \
  --dbtype postgresql
Supported --dbtype values: postgresql, mysql, sqlite, mongodb, cassandra, dynamodb.
```

### Discover the schema

```bash
basecrawler discover
```

Export a CSV file for one table

```bash
basecrawler export --table users --format csv > users.csv
Run an ad‑hoc query
```

```bash
basecrawler exec \
  "SELECT * FROM inventory WHERE quantity < 5"
```

## 5. Usage Examples

### Example 1 – One‑liner Discovery & Export

```bash
basecrawler discover --output json > schema.json && \
basecrawler export --table orders --format csv -o orders.csv
```

### Example 2 – Execute a Query and Save to JSON

```bash
basecrawler exec \
  "SELECT * FROM products WHERE price < 100" \
  --output json > low_price_products.json

```

### Example 3 – Run a Custom Script (Python)

#### Create scripts/example.py:

```
scripts/example.py
```

```python
from basecrawler import cli, config

if __name__ == "__main__":
    # Load the discovered schema and filter for numeric columns only
    schema = config.get_schema()
    num_cols = [c for c in schema if c.type in ["int", "float"]]
    print("Numeric columns:", num_cols)
```

### Run it:

```bash
basecrawler run scripts/example.py
```

## 6. Configuration
### All runtime options can be overridden via environment variables or an external config.yaml file.

### 6.1 Environment Variables

<center>
    <table>
        <tr>
            <td>Variable</td><td>Description</td>
        </tr>
        <tr>
            <td>BASECRAWLER_LOG_LEVEL</td><td>DEBUG, INFO, WARNING, ERROR, CRITICAL. Default: INFO.</td>
        </tr>
        <tr>
            <td>BASECRAWLER_DB_HOST</td><td>Hostname of the DB server.</td>
        </tr>
        <tr>
            <td>BASECRAWLER_DB_PORT</td><td>Port number (e.g., 5432).</td>
        </tr>
        <tr>
            <td>BASECRAWLER_USER</td><td>Username for authentication.</td>
        </tr>
        <tr>
            <td>BASECRAWLER_PASS</td><td>Password for authentication.</td>
        </tr>
        <tr>
            <td>BASECRAWLER_DB_TYPE</td><td>One of postgresql, mysql, sqlite, mongodb, cassandra, dynamodb.</td>
        </tr>
        <tr><td></td><td></td></tr>
    </table>
</center>

### 6.2 config.yaml
#### config.yaml (stored in the project root)

```yaml
database:
  host: "localhost"
  port: 5432
  username: "postgres"
  password: "secret"
  type:   postgresql
logging:
  level: DEBUG
```

#### Tip – Run ```basecrawler --help``` to see all sub‑commands and their flags.

## 7. Advanced Options
<center>
    <table>
        <tr>
            <td>Flag</td><td>Description</td>
        </tr>
        <tr>
            <td>--verbose, -v</td><td>Print detailed progress (e.g., column scan speed).</td>
        </tr>
        <tr>
            <td>--force, -f</td><td>Skip the confirmation prompt for destructive actions (drop, purge).</td>
        </tr>  
        <tr>
            <td>--no-ui</td><td>Disable the optional GUI overlay when running headless.</td>
        </tr>  
        <tr>
            <td>--Plugin [path]</td><td>Load a custom plugin from any directory (e.g., to add support for a new DB driver).</td>
        </tr>
        <tr><td></td><td></td></tr>
    </table>
</center>

#### Example – Force export of all tables without prompting

```bash
basecrawler export --format json --force > all_tables.json
```

## 8. Scripts & API

### 8.1 CLI Sub‑Commands

<center>
    <table>
        <tr>
            <td>Command</td><td>Synopsis</td>
        </tr>
        <tr>
            <td>discover</td><td>Enumerate tabels columns, primary keys and foreign constraints.</td>
        </tr>
        <tr>
            <td>export [table]</td><td>Export a table to CSV/JSON/TXT.</td>
        </tr>
        <tr>
            <td>exec [sql]</td><td>Run arbitrary SQL; outputs result set in JSON by default.</td>
        </tr>
        <tr>
            <td>run [script] [args]</td><td>Execute any python script that imports the internal helper module.</td>
        </tr>
        <tr>
            <td>list-plugins</td><td>Show all installed plugins and their version.</td>
        </tr>
        <tr>
            <td>Connect</td><td>Establish a connection before discovery (optional for. CLI mode).</td>
        </tr>
        <tr><td></td><td></td></tr>
    </table>
</center>

### 8.2 Programmatic API
```python
from basecrawler import cli, config
```

# Discover schema without UI

```python
schema = config.get_schema()
print(schema)
```

# Export to CSV using pandas

```python
import pandas as pd
pd.read_sql_table('orders', conn).to_csv('orders.csv')
```

### All classes (Schema, Connection, Executor) expose a clean API and are fully documented in the source code.

## 9. Contributing
### We welcome contributions! Whether you have a bug report, a feature request, or just want to improve documentation—open an issue first so we can discuss it before diving into code.

### 9.1 Development Setup

```bash
git clone https://github.com/Netherwarlord/BaseCrawler.git
cd BaseCrawler
python -m venv .venv && source .venv/bin/activate
pip install -r requirements-dev.txt
```

### Run the test suite:

```python
pytest tests/
```

### 9.2 Style & Linting
PEP 8 compliance – Run flake8 locally.

Black formatter – Apply with black ..

## 10. Roadmap

<center>
    <table>
        <tr>
            <td>Version</td><td>Planned Features</td><td>Release Date</td>
        </tr>
        <tr>
            <td>V1.0.0</td>
            <td>Initial Release | stabilization and documantation overhaul</td>
            <td>Coming Soon</td>
        </tr>
        <tr><td><td></td></td><td></td><tr>
    </table>
</center>

## 11. License
This project is licensed under the GNU Public License V3 (GPL3). See the LICENSE file for details.

## Enjoy CRAWLING your data! 🚀