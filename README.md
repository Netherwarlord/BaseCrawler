# BaseCrawler – A Modern Desktop Database Management Tool
### "A powerful, lightweight GUI that lets you explore, edit, and query relational and document databases — all from a single window."

License GitHub Tag GitHub Language Count

## Table of Contents
### Section
<ol>
    <li>Overview</li>
    <li>Features</li>
    <li>Prerequisites & Installation</li>
    <li>Getting Started</li>
    <li>Interface Guide</li>
    <li>Connection Management</li>
    <li>Architecture</li>
    <li>Contributing</li>
    <li>Roadmap</li>
    <li>License</li>
</ol>

## 1. Overview
BaseCrawler is a desktop GUI database management tool built with Python and CustomTkinter. It lets you:
<ul>
    <li>Connect to and manage multiple PostgreSQL, MySQL, MariaDB, and MongoDB databases simultaneously.</li>
    <li>Browse, create, edit, and delete tables and collections — all without writing SQL by hand.</li>
    <li>View, add, edit, and delete rows from an inline table viewer with persistent column sizing and primary key indicators.</li>
    <li>Run ad-hoc SQL queries against any connected database from a dedicated query window.</li>
    <li>Save connection profiles with optional password storage, and instantly switch between them without losing your place.</li>
</ul>

BaseCrawler is written in Python 3.10+ and uses CustomTkinter for a native-feeling dark/light mode UI on macOS, Windows, and Linux.

## 2. Features

<center>
    <table width="100%">
        <tr>
            <td>Category</td><td>Feature</td>
        </tr>
        <tr>
            <td>Connections</td>
            <td>
                <ul>
                    <li>Saved connection profiles stored in <code>connections.json</code></li>
                    <li>Supports PostgreSQL, MySQL, MariaDB, and MongoDB</li>
                    <li>Background status polling — live Online / Offline indicator per connection</li>
                    <li>Optional password saving per connection with "Save password" toggle</li>
                    <li>Per-connection workspace state — switch connections and return to exactly where you left off</li>
                    <li>One-click Disconnect from the ribbon toolbar</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Schema Browser</td>
            <td>
                <ul>
                    <li>Table / collection list with single-click select and double-click open</li>
                    <li>Add Table wizard with per-column PK, Auto, Rand, Length, and Unique options</li>
                    <li>Edit Table dialog — modify types, add/drop columns, change constraints</li>
                    <li>Delete Table with confirmation dialog</li>
                    <li>MongoDB: collections shown in list; DDL operations automatically hidden</li>
                    <li>5-second auto-refresh keeps the schema list current</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Inline Table Viewer</td>
            <td>
                <ul>
                    <li>Full-width inline data view — no separate popup windows</li>
                    <li>🔑 icon on primary key column headers</li>
                    <li>Alternating row colors with a toggleable grid-line overlay</li>
                    <li>Resizable columns — widths persist across refreshes per session</li>
                    <li>Double-click a column separator to auto-fit to content</li>
                    <li>Double-click any cell for inline editing</li>
                    <li>Add Row with auto-fill for identity and default columns</li>
                    <li>Edit Row and Delete Row with confirmation</li>
                    <li>Add Column and Delete Column while table is open</li>
                    <li>5-second auto-refresh keeps data current</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Query Wizard</td>
            <td>
                <ul>
                    <li>Non-modal query window — stays open while you browse the schema</li>
                    <li>SQL editor with Execute and Clear actions</li>
                    <li>Formatted results (column headers + rows) displayed inline</li>
                    <li>Auto-refreshes the schema list after any DDL statement (CREATE, ALTER, DROP, etc.)</li>
                    <li>Accessible from both the schema view and the table view via the ribbon</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>Ribbon Toolbar</td>
            <td>
                <ul>
                    <li>MS Office-style ribbon with labeled icon groups</li>
                    <li>Schema view groups: View · Tables · Query · Connection</li>
                    <li>Table view groups: Navigate · Rows · Columns · Query</li>
                    <li>Edit Mode toggle (✏) — dims structural editing buttons when off</li>
                    <li>Grid Lines toggle (⊞) — show/hide alternating row colors</li>
                </ul>
            </td>
        </tr>
        <tr>
            <td>UI & Workspace</td>
            <td>
                <ul>
                    <li>Dark and Light mode via CustomTkinter</li>
                    <li>Collapsible connection sidebar (◀ Hide Panel / ▶ Show Panel)</li>
                    <li>Per-connection open-table state restored on reconnect</li>
                    <li>All database calls run on background threads — UI stays responsive</li>
                </ul>
            </td>
        </tr>
    </table>
</center>

## 3. Prerequisites & Installation

**Required:**
- Python 3.10+
- A `base-crawler` conda environment (recommended) **or** a plain virtual environment

### Using conda (recommended)

```bash
git clone https://github.com/Netherwarlord/BaseCrawler.git
cd BaseCrawler
conda create -n base-crawler python=3.11
conda activate base-crawler
pip install -r requirements.txt
```

### Using a plain virtual environment

```bash
git clone https://github.com/Netherwarlord/BaseCrawler.git
cd BaseCrawler
python -m venv .venv
source .venv/bin/activate   # macOS / Linux
.venv\Scripts\activate      # Windows
pip install -r requirements.txt
```

### macOS – if pip complains about the system Python

```bash
brew link --force --overwrite python
```

### Key dependencies

<center>
    <table width="100%">
        <tr>
            <td>Package</td><td>Purpose</td>
        </tr>
        <tr>
            <td>customtkinter</td><td>Modern themed GUI framework</td>
        </tr>
        <tr>
            <td>CTkMessagebox</td><td>Styled dialog boxes</td>
        </tr>
        <tr>
            <td>psycopg2</td><td>PostgreSQL driver</td>
        </tr>
        <tr>
            <td>mysql-connector-python</td><td>MySQL / MariaDB driver</td>
        </tr>
        <tr>
            <td>pymongo</td><td>MongoDB driver</td>
        </tr>
    </table>
</center>

## 4. Getting Started

### Launch the application

Always activate the conda environment first, then run `app.py` directly:

```bash
conda activate base-crawler
python app.py
```

To syntax-check without launching the GUI:

```bash
python -m py_compile app.py
```

### Add your first connection

1. Click **Manage Connections** at the bottom of the left sidebar.
2. Click **Add Connection** and fill in the connection name, database type, host, port, username, password, and database name.
3. Click **Save Connection**. The connection now appears in the sidebar.

### Connect and explore

1. Click a connection name in the sidebar to select it — the right panel shows connection details and a live status indicator.
2. Enter your username and password in the credentials panel (check **Save password** if you want it stored).
3. Click **Connect**. The ribbon toolbar and table list appear automatically.
4. Double-click any table in the list to open it inline, or single-click and press **▶ Open** in the ribbon.

## 5. Interface Guide

### Top Bar

The narrow bar above the workspace contains three persistent controls:

<center>
    <table width="100%">
        <tr>
            <td>Control</td><td>Function</td>
        </tr>
        <tr>
            <td>◀ Hide Panel / ▶ Show Panel</td><td>Collapse or expand the left connection sidebar</td>
        </tr>
        <tr>
            <td>⊞ (checkbox)</td><td>Toggle alternating row grid lines in the table viewer</td>
        </tr>
        <tr>
            <td>✏ (checkbox)</td><td>Toggle Edit Mode — when off, structural editing buttons are dimmed</td>
        </tr>
    </table>
</center>

### Schema View Ribbon

Visible when browsing the table list. Groups and their icon buttons:

<center>
    <table width="100%">
        <tr>
            <td>Group</td><td>Buttons</td>
        </tr>
        <tr>
            <td>View</td><td>▶ Open — open the selected table inline</td>
        </tr>
        <tr>
            <td>Tables</td><td>✎ Edit · ⊕ Add · ⊗ Delete</td>
        </tr>
        <tr>
            <td>Query</td><td>≡ SQL — open the Query Wizard window</td>
        </tr>
        <tr>
            <td>Connection</td><td>⏻ Disconnect — disconnect and return to the connection info panel</td>
        </tr>
    </table>
</center>

### Table View Ribbon

Visible when a table is open inline. Groups and their icon buttons:

<center>
    <table width="100%">
        <tr>
            <td>Group</td><td>Buttons</td>
        </tr>
        <tr>
            <td>Navigate</td><td>◀ Back — return to the table list</td>
        </tr>
        <tr>
            <td>Rows</td><td>⊕ Add · ✎ Edit · ⊗ Delete</td>
        </tr>
        <tr>
            <td>Columns</td><td>⊕ Add · ⊗ Delete</td>
        </tr>
        <tr>
            <td>Query</td><td>≡ SQL — open the Query Wizard window</td>
        </tr>
    </table>
</center>

### Column Resizing

- **Drag** a column separator in the header to resize. Width is remembered for the rest of the session.
- **Double-click** a column separator to auto-fit the column to its widest content.

## 6. Connection Management

### Connection Info Screen

When you select a saved connection (but are not yet connected), the right panel shows:

- **Connection name** — large, top-left
- **Info card** — Type, Host, Port, DB, live Status (Online / Offline / Checking…), and Size
- **Credentials panel** — editable Username and Password fields, pre-filled from saved values
- **Save password** checkbox — controls whether the password is persisted to `connections.json`
- **Connect** button — or press Enter in either credential field

### Saved Connections File

Connections are stored in `connections.json` in the project root. This file is created automatically the first time you save a connection. **Do not commit this file if it contains sensitive credentials.**

### Switching Connections

Click any connection in the sidebar while already connected. BaseCrawler will:
1. Save your current workspace state (which table is open, the cached schema).
2. Silently reconnect to the new connection.
3. Restore your previous workspace for that connection if one exists.

## 7. Architecture

BaseCrawler is three Python files with no web server or external process:

<center>
    <table width="100%">
        <tr>
            <td>File</td><td>Responsibility</td>
        </tr>
        <tr>
            <td><code>connection_manager.py</code></td>
            <td>Pure data layer. Reads/writes <code>connections.json</code>. No UI dependency. Key methods: <code>add_connection</code>, <code>remove_connection</code>, <code>update_connection</code>, <code>reorder_connection</code>.</td>
        </tr>
        <tr>
            <td><code>db_connector.py</code></td>
            <td>
                One <code>DBConnector</code> base class, three concrete implementations:
                <code>PostgreSQLConnector</code> (psycopg2),
                <code>MongoDBConnector</code> (pymongo),
                <code>MySQLMariaDBConnector</code> (mysql-connector-python).
                <code>get_connector(connection_details)</code> is the factory.
                All connectors share a common interface: <code>connect</code>, <code>disconnect</code>, <code>fetch_schema</code>, <code>fetch_data</code>, <code>execute_query</code>, <code>insert_data</code>, <code>update_data</code>, <code>delete_data</code>, <code>fetch_column_defaults</code>, <code>fetch_primary_keys</code>, <code>evaluate_expression</code>.
            </td>
        </tr>
        <tr>
            <td><code>app.py</code></td>
            <td>
                All UI. Key classes:
                <code>DBManagerApp</code> (main window),
                <code>ManageConnectionsWindow</code>,
                <code>NewConnectionWindow</code>,
                <code>AddEditDataWindow</code> (row-level add/edit form),
                <code>AddTableDialog</code>,
                <code>EditTableDialog</code>,
                <code>AddColumnDialog</code>,
                <code>DeleteColumnDialog</code>,
                <code>QueryWindow</code>.
                All DB calls that run in the background use <code>queue.Queue</code> + <code>after()</code> polling — never updating CTk widgets directly from a background thread.
            </td>
        </tr>
    </table>
</center>

### Threading Model

All database calls that run in the background communicate results back to the main thread via `queue.Queue` + `after()` polling — UI widgets are never updated from a background thread.

The status poller (`_start_status_poller`) is a long-lived daemon thread per selected connection, sleeping 30 s between checks. The auto-refresh timer (`_start_auto_refresh`) fires every 5 seconds via `after()` on the main thread, refreshing either the schema list or the open table depending on the current view.

## 8. Contributing

We welcome contributions! Whether you have a bug report, a feature request, or just want to improve documentation — open an issue first so we can discuss it before diving into code.

### Development Setup

```bash
git clone https://github.com/Netherwarlord/BaseCrawler.git
cd BaseCrawler
conda create -n base-crawler python=3.11
conda activate base-crawler
pip install -r requirements.txt
```

### Style & Linting
PEP 8 compliance — run `flake8` locally.

Black formatter — apply with `black .`

## 10. Roadmap

<center>
    <table width="100%">
        <tr>
            <td>Version</td><td>Description</td><td>Release Date</td>
        </tr>
        <tr>
            <td>v1.0.0</td>
            <td>
                Initial Release
                <ul>
                    <li>Full database support for: PostgreSQL, Oracle DB, MySQL, MariaDB, MongoDB and MSDB</li>
                    <li>Full-Feature toolbar for manipulating databases.</li>
                    <li>Support for custom modules and databse connecotrs.</li>
                    <li>Modern UI and design language.</li>
                    <li>Improved performance and reliability.</li>
                    <li>Native support for secrets management, parameterized query enforcement, and identity-bound auditing to satisfy SOC 2 and PCI DSS requirements out of the box.</li>
                </ul>
            </td>
            <td>Coming Soon</td>
        </tr>
        <tr>
            <td>v0.8.3-alpha</td>
            <td>
                Major Overhaul
                <ul>
                    <li>Separated main app.py file into smaller modules.</li>
                    <li>Made performance improvements on load times.</li>
                    <li>Added persistent state saving across restarts.</li>
                    <li>Added double-click to edit cuntionality in active tables.</li>
                    <li>Modularized Wizard design for later implementation.</li>
                </ul>
            </td>
            <td>2026-05-03</td>
        </tr>
        <tr>
            <td>v0.7.51-alpha</td>
            <td>
                Initial Pre-Release Alpha
                <ul>
                    <li>First alpha version fit for public testing stages.</li>
                    <li>Stabilized Thread Leak issue.</li>
                    <li>Created single window functionality.</li>
                    <li>Added toolbar to table viewer/editor.</li>
                    <li>Moved Query editor into its own window/wizard.</li>
                    <li>Finalized PostgreSQL connector.</li>
                    <li>Finalized MongoDB connecotr.</li>
                    <li>Finalized MariaDB connector.</li>
                    <li>Finalized MySQL connector.</li>
                </ul>
            </td>
            <td>2026-05-03</td>
        </tr>
    </table>
</center>

## 11. License
This project is licensed under the GNU Public License V3 (GPL3). See the LICENSE file for details.

## Enjoy CRAWLING your data! 🚀
