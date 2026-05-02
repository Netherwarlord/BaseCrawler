import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
import json
import datetime
from CTkMessagebox import CTkMessagebox
import threading
import queue

from connection_manager import ConnectionManager
from db_connector import get_connector

class NewConnectionWindow(ctk.CTkToplevel):
    def __init__(self, master, connection_manager, existing_connection=None):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.connection_manager = connection_manager
        self.existing_connection = existing_connection
        self._edit_mode = existing_connection is not None

        self.title("Edit Connection" if self._edit_mode else "New Connection")
        self.geometry("400x550")

        self.grid_columnconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Connection Name
        ctk.CTkLabel(self, text="Connection Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        # DB Type
        ctk.CTkLabel(self, text="Database Type:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.db_type_var = ctk.StringVar(value="PostgreSQL")
        self.db_type_optionmenu = ctk.CTkOptionMenu(self, values=["PostgreSQL", "MongoDB", "MariaDB", "MySQL"],
                                                    variable=self.db_type_var)
        self.db_type_optionmenu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        # Host
        ctk.CTkLabel(self, text="Host:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.host_entry = ctk.CTkEntry(self)
        self.host_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        # Port
        ctk.CTkLabel(self, text="Port:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.port_entry = ctk.CTkEntry(self)
        self.port_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        # User
        ctk.CTkLabel(self, text="User:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.user_entry = ctk.CTkEntry(self)
        self.user_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        # Password
        ctk.CTkLabel(self, text="Password:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        self._pw_visible = False
        self.pw_toggle_btn = ctk.CTkButton(
            self,
            text="◡",
            width=28,
            height=28,
            corner_radius=6,
            fg_color="transparent",
            hover_color=("gray75", "gray35"),
            text_color=("gray10", "gray90"),
            command=self._toggle_password_visibility
        )
        self.password_entry.bind("<Configure>", self._reposition_pw_toggle)

        # Database Name
        ctk.CTkLabel(self, text="Database Name:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.database_entry = ctk.CTkEntry(self)
        self.database_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # Pre-fill fields when editing an existing connection
        if self._edit_mode:
            self.name_entry.insert(0, existing_connection.get("name", ""))
            self.db_type_var.set(existing_connection.get("db_type", "PostgreSQL"))
            self.host_entry.insert(0, existing_connection.get("host", ""))
            self.port_entry.insert(0, existing_connection.get("port", ""))
            self.user_entry.insert(0, existing_connection.get("user", ""))
            self.password_entry.insert(0, existing_connection.get("password", ""))
            self.database_entry.insert(0, existing_connection.get("database", ""))

        button_label = "Update Connection" if self._edit_mode else "Save Connection"
        self.save_button = ctk.CTkButton(self, text=button_label, command=self._save_connection)
        self.save_button.grid(row=7, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def _save_connection(self):
        connection_details = {
            "name": self.name_entry.get(),
            "db_type": self.db_type_var.get(),
            "host": self.host_entry.get(),
            "port": self.port_entry.get(),
            "user": self.user_entry.get(),
            "password": self.password_entry.get(),
            "database": self.database_entry.get()
        }
        if self._edit_mode:
            self.connection_manager.update_connection(self.existing_connection["name"], connection_details)
            CTkMessagebox(title="Success", message="Connection updated successfully.", icon="check", option_1="Ok")
        else:
            self.connection_manager.add_connection(connection_details)
            CTkMessagebox(title="Success", message="Connection saved successfully.", icon="check", option_1="Ok")
        self.master._load_connections_list()
        self.master.master._load_connection_buttons()
        self.destroy()

    def _reposition_pw_toggle(self, event=None):
        self.update_idletasks()
        e = self.password_entry
        btn_size = 28
        x = e.winfo_x() + e.winfo_width() - btn_size - 4
        y = e.winfo_y() + (e.winfo_height() - btn_size) // 2
        self.pw_toggle_btn.place(x=x, y=y)

    def _toggle_password_visibility(self):
        self._pw_visible = not self._pw_visible
        if self._pw_visible:
            self.password_entry.configure(show="")
            self.pw_toggle_btn.configure(text="👁")
        else:
            self.password_entry.configure(show="*")
            self.pw_toggle_btn.configure(text="◡")


class ManageConnectionsWindow(ctk.CTkToplevel):
    def __init__(self, master, connection_manager):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title("Manage Connections")
        self.geometry("500x600")
        self.connection_manager = connection_manager
        self.master = master # Reference to DBManagerApp

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.connections_frame = ctk.CTkScrollableFrame(self, label_text="Saved Connections")
        self.connections_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.connections_frame.grid_columnconfigure(0, weight=1)

        self.control_frame = ctk.CTkFrame(self)
        self.control_frame.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        self.control_frame.grid_columnconfigure((0,1,2), weight=1)

        ctk.CTkButton(self.control_frame, text="Add", command=self._add_new_connection).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.control_frame, text="Edit", command=self._edit_selected).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.control_frame, text="Remove", command=self._remove_selected).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.control_frame, text="↑", width=40, command=self._move_up).grid(row=0, column=3, padx=(2,2), pady=5)
        ctk.CTkButton(self.control_frame, text="↓", width=40, command=self._move_down).grid(row=0, column=4, padx=(2,5), pady=5)

        self.selected_connection_name = None
        self._load_connections_list()

    def _load_connections_list(self):
        for widget in self.connections_frame.winfo_children():
            widget.destroy()
        
        connections = self.connection_manager.get_connections()
        for i, conn in enumerate(connections):
            conn_name = conn.get("name", "Unnamed Connection")
            btn = ctk.CTkButton(self.connections_frame, text=conn_name, 
                                command=lambda name=conn_name: self._select_connection_in_list(name))
            btn.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            if conn_name == self.selected_connection_name:
                btn.configure(fg_color=btn.cget("hover_color")) # Highlight selected

    def _select_connection_in_list(self, name):
        self.selected_connection_name = name
        self._load_connections_list() # Refresh to highlight

    def _add_new_connection(self):
        new_conn_win = NewConnectionWindow(self, self.connection_manager)
        new_conn_win.focus()
        new_conn_win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connections_list(), new_conn_win.destroy()))

    def _edit_selected(self):
        if not self.selected_connection_name:
            CTkMessagebox(title="Warning", message="No connection selected to edit.", icon="warning", option_1="Ok")
            return
        existing = next((c for c in self.connection_manager.get_connections() if c.get("name") == self.selected_connection_name), None)
        if not existing:
            return
        edit_win = NewConnectionWindow(self, self.connection_manager, existing_connection=existing)
        edit_win.focus()
        edit_win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connections_list(), edit_win.destroy()))

    def _remove_selected(self):
        if self.selected_connection_name:
            msg = CTkMessagebox(title="Confirm Removal", message=f"Are you sure you want to remove {self.selected_connection_name}?",
                                icon="question", option_1="No", option_2="Yes")
            if msg.get() == "Yes":
                self.connection_manager.remove_connection(self.selected_connection_name)
                self.selected_connection_name = None
                self._load_connections_list()
                self.master._load_connection_buttons() # Refresh main app's list
        else:
            CTkMessagebox(title="Warning", message="No connection selected to remove.", icon="warning", option_1="Ok")

    def _move_up(self):
        if self.selected_connection_name:
            self.connection_manager.reorder_connection(self.selected_connection_name, -1)
            self._load_connections_list()
            self.master._load_connection_buttons() # Refresh main app's list
        else:
            CTkMessagebox(title="Warning", message="No connection selected to move.", icon="warning", option_1="Ok")

    def _move_down(self):
        if self.selected_connection_name:
            self.connection_manager.reorder_connection(self.selected_connection_name, 1)
            self._load_connections_list()
            self.master._load_connection_buttons() # Refresh main app's list
        else:
            CTkMessagebox(title="Warning", message="No connection selected to move.", icon="warning", option_1="Ok")


class AddEditDataWindow(ctk.CTkToplevel):
    def __init__(self, master, active_connector, item_name, is_collection, columns, initial_data=None, mode="add"):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"{mode.capitalize()} Data: {item_name}")
        self.geometry("500x" + str(100 + len(columns) * 40))
        self.active_connector = active_connector
        self.item_name = item_name
        self.is_collection = is_collection
        self.columns = columns
        self.initial_data = initial_data
        self.mode = mode
        self.entry_widgets = {}

        self.grid_columnconfigure(1, weight=1)

        for i, col_name in enumerate(self.columns):
            if col_name == "_id" and self.is_collection and self.mode == "add": # MongoDB _id is auto-generated
                continue
            if col_name == "_id" and self.is_collection and self.mode == "edit": # MongoDB _id is not editable
                ctk.CTkLabel(self, text=f"{col_name}:").grid(row=i, column=0, padx=10, pady=5, sticky="w")
                label = ctk.CTkLabel(self, text=str(initial_data.get(col_name, "")))
                label.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
                self.entry_widgets[col_name] = label # Store label for consistency, though not editable
                continue

            ctk.CTkLabel(self, text=f"{col_name}:").grid(row=i, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self)
            entry.grid(row=i, column=1, padx=10, pady=5, sticky="ew")
            self.entry_widgets[col_name] = entry

            if self.mode == "edit" and initial_data and col_name != "_id": # Pre-fill for edit mode, skip _id
                entry.insert(0, str(initial_data.get(col_name, "")))

        save_button = ctk.CTkButton(self, text="Save", command=self._save_data)
        save_button.grid(row=len(self.columns), column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def _save_data(self):
        data = {}
        for col_name, widget in self.entry_widgets.items():
            if isinstance(widget, ctk.CTkEntry):
                data[col_name] = widget.get()
            elif isinstance(widget, ctk.CTkLabel): # For non-editable _id
                data[col_name] = widget.cget("text")

        success = False
        message = ""

        if self.mode == "add":
            success, message = self.active_connector.insert_data(self.item_name, data)
        elif self.mode == "edit":
            # For simplicity, assuming the first column is the primary key for SQL, or _id for MongoDB
            condition = {}
            if self.is_collection:
                # MongoDB uses _id for unique identification
                condition["_id"] = self.initial_data["_id"]
            else:
                # For SQL, assume the first column is the primary key for update condition
                pk_col = self.columns[0]
                condition[pk_col] = self.initial_data[pk_col]
            
            # Remove the primary key from data to be updated if it's present
            if pk_col in data and not self.is_collection: # For SQL
                del data[pk_col]
            if "_id" in data and self.is_collection: # For MongoDB
                del data["_id"]

            success, message = self.active_connector.update_data(self.item_name, data, condition)
        
        if success:
            self.master._refresh_inline_table()
            self.destroy()
        else:
            CTkMessagebox(title="Error", message=f"Failed to save data: {message}", icon="cancel", option_1="Ok")


COLUMN_TYPES = ["TEXT", "INTEGER", "REAL", "NUMERIC", "MONEY", "BOOLEAN", "VARCHAR(255)", "TIMESTAMP", "DATE", "BYTEA"]


class AddTableDialog(ctk.CTkToplevel):
    def __init__(self, master, active_connector):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title("Add Table")
        self.geometry("560x560")
        self.active_connector = active_connector
        self._col_rows = []  # list of dicts

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(2, weight=1)

        ctk.CTkLabel(self, text="Table Name:").grid(row=0, column=0, padx=10, pady=(12, 2), sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=1, column=0, padx=10, pady=(0, 8), sticky="ew")

        self.cols_frame = ctk.CTkScrollableFrame(self, label_text="Columns")
        self.cols_frame.grid(row=2, column=0, padx=10, pady=4, sticky="nsew")
        self.cols_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self, text="+ Add Column", command=self._add_col_row).grid(row=3, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="Create Table", command=self._create_table).grid(row=4, column=0, padx=10, pady=(4, 12), sticky="ew")

        self._add_col_row()

    def _add_col_row(self):
        idx = len(self._col_rows)

        outer = ctk.CTkFrame(self.cols_frame, fg_color="transparent")
        outer.grid(row=idx, column=0, padx=0, pady=(2, 6), sticky="ew")
        outer.grid_columnconfigure(0, weight=1)

        # Row 1: name, type, remove button
        row1 = ctk.CTkFrame(outer, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew")
        row1.grid_columnconfigure(0, weight=1)

        name_entry = ctk.CTkEntry(row1, placeholder_text="column name")
        name_entry.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        type_var = ctk.StringVar(value=COLUMN_TYPES[0])
        ctk.CTkOptionMenu(row1, values=COLUMN_TYPES, variable=type_var, width=130).grid(row=0, column=1, padx=(0, 4))

        # Row 2: checkboxes
        row2 = ctk.CTkFrame(outer, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        pk_var   = ctk.BooleanVar(value=False)
        rand_var = ctk.BooleanVar(value=False)
        auto_var = ctk.BooleanVar(value=False)

        max_label  = ctk.CTkLabel(row2, text="Max chars:")
        max_entry  = ctk.CTkEntry(row2, width=65, placeholder_text="36")

        def on_rand_toggle():
            if rand_var.get():
                max_label.grid(row=0, column=2, padx=(10, 2))
                max_entry.grid(row=0, column=3, padx=(0, 10))
            else:
                max_label.grid_remove()
                max_entry.grid_remove()

        ctk.CTkCheckBox(row2, text="Primary Key",  variable=pk_var,   width=110).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkCheckBox(row2, text="Random Gen",   variable=rand_var, width=105, command=on_rand_toggle).grid(row=0, column=1)
        ctk.CTkCheckBox(row2, text="Auto Fill",    variable=auto_var, width=85).grid(row=0, column=4, padx=(10, 0))

        entry = {"name_entry": name_entry, "type_var": type_var,
                 "pk_var": pk_var, "rand_var": rand_var,
                 "max_entry": max_entry, "auto_var": auto_var, "frame": outer}

        def do_remove(e=entry, f=outer):
            self._col_rows[:] = [x for x in self._col_rows if x is not e]
            f.destroy()

        ctk.CTkButton(row1, text="×", width=28, command=do_remove).grid(row=0, column=2)
        self._col_rows.append(entry)

    def _create_table(self):
        table_name = self.name_entry.get().strip()
        if not table_name:
            CTkMessagebox(title="Error", message="Table name is required.", icon="cancel", option_1="Ok")
            return

        col_defs = []
        pk_cols  = []

        for e in self._col_rows:
            name = e["name_entry"].get().strip()
            if not name:
                continue
            col_type = e["type_var"].get()

            if e["rand_var"].get():
                expr = _rand_default_sql(col_type, e["max_entry"].get().strip())
                col_def = f'"{name}" {col_type} DEFAULT {expr}'
            elif e["auto_var"].get() and col_type == "INTEGER":
                col_def = f'"{name}" INTEGER GENERATED ALWAYS AS IDENTITY'
            elif e["auto_var"].get() and col_type in ("TIMESTAMP", "DATE"):
                col_def = f'"{name}" {col_type} DEFAULT CURRENT_TIMESTAMP'
            else:
                col_def = f'"{name}" {col_type}'

            col_defs.append(col_def)
            if e["pk_var"].get():
                pk_cols.append(f'"{name}"')

        if not col_defs:
            CTkMessagebox(title="Error", message="Add at least one column.", icon="cancel", option_1="Ok")
            return

        if pk_cols:
            col_defs.append(f"PRIMARY KEY ({', '.join(pk_cols)})")

        cols_sql = ", ".join(col_defs)
        query = f'CREATE TABLE "{table_name}" ({cols_sql});'
        success, result = self.active_connector.execute_query(query)
        if success:
            self.destroy()
            self.master._refresh_schema()
        else:
            CTkMessagebox(title="Error", message=f"Failed to create table: {result}", icon="cancel", option_1="Ok")


class AddColumnDialog(ctk.CTkToplevel):
    def __init__(self, master, active_connector, table_name):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"Add Column — {table_name}")
        self.geometry("380x200")
        self.active_connector = active_connector
        self.table_name = table_name

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Column Name:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.col_name_entry = ctk.CTkEntry(self)
        self.col_name_entry.grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="Type:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.type_var = ctk.StringVar(value=COLUMN_TYPES[0])
        ctk.CTkOptionMenu(self, values=COLUMN_TYPES, variable=self.type_var).grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(self, text="Add Column", command=self._add_column).grid(row=2, column=0, columnspan=2, padx=10, pady=16, sticky="ew")

    def _add_column(self):
        col_name = self.col_name_entry.get().strip()
        if not col_name:
            CTkMessagebox(title="Error", message="Column name is required.", icon="cancel", option_1="Ok")
            return
        query = f'ALTER TABLE "{self.table_name}" ADD COLUMN "{col_name}" {self.type_var.get()};'
        success, result = self.active_connector.execute_query(query)
        if success:
            self.destroy()
            self.master._refresh_inline_table()
            self.master._refresh_schema()
        else:
            CTkMessagebox(title="Error", message=f"Failed to add column: {result}", icon="cancel", option_1="Ok")


_SCHEMA_TYPE_MAP = {
    "text": "TEXT",
    "integer": "INTEGER",
    "bigint": "INTEGER",
    "smallint": "INTEGER",
    "real": "REAL",
    "double precision": "REAL",
    "numeric": "NUMERIC",
    "decimal": "NUMERIC",
    "money": "MONEY",
    "boolean": "BOOLEAN",
    "character varying": "VARCHAR(255)",
    "timestamp without time zone": "TIMESTAMP",
    "timestamp with time zone": "TIMESTAMP",
    "date": "DATE",
    "bytea": "BYTEA",
}


def _rand_default_sql(col_type: str, max_val: str) -> str:
    """Return a PostgreSQL DEFAULT expression for a random value appropriate to col_type.
    max_val is the raw string from the Max entry (chars for text, digits for numbers)."""
    try:
        n = max(1, int(max_val))
    except (ValueError, TypeError):
        n = 36
    text_types = {"TEXT", "VARCHAR(255)"}
    int_types  = {"INTEGER"}
    float_types = {"REAL", "NUMERIC", "MONEY"}
    bool_types  = {"BOOLEAN"}
    date_types  = {"DATE"}
    ts_types    = {"TIMESTAMP"}
    if col_type in text_types:
        return f"substring(md5(random()::text) from 1 for {n})"
    if col_type in int_types:
        upper = 10 ** n
        return f"floor(random() * {upper})::integer"
    if col_type in float_types:
        upper = 10 ** n
        return f"round((random() * {upper})::numeric, 2)"
    if col_type in bool_types:
        return "(random() > 0.5)"
    if col_type in date_types:
        return f"(current_date - (random() * {n * 30})::integer)"
    if col_type in ts_types:
        return f"(now() - (random() * interval '{n * 30} days'))"
    return f"substring(md5(random()::text) from 1 for {n})"


def _parse_rand_max(col_default: str, col_type: str) -> str:
    """Try to recover the 'max' number from an existing rand DEFAULT expression."""
    import re, math
    if not col_default:
        return "6"
    # TEXT/VARCHAR: substring(md5(random()::text) from 1 for N)
    m = re.search(r"for (\d+)\)", col_default)
    if m:
        return m.group(1)
    # INTEGER: floor(random() * N)::integer
    m = re.search(r"random\(\) \* (\d+)", col_default)
    if m:
        try:
            n = int(m.group(1))
            digits = int(round(math.log10(n))) if n > 1 else 1
            return str(digits)
        except Exception:
            return "6"
    # BOOLEAN / DATE / TIMESTAMP — no meaningful "max" to recover
    return "6"


class EditTableDialog(ctk.CTkToplevel):
    def __init__(self, master, active_connector, table_name, columns):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"Edit Table — {table_name}")
        self.geometry("580x560")
        self.active_connector = active_connector
        self.table_name = table_name
        self._original_cols = {col["name"]: col["type"] for col in columns}
        self._original_unique_map  = active_connector.fetch_unique_columns(table_name)
        self._col_defaults         = active_connector.fetch_column_defaults(table_name)
        self._col_rows = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self, text=f"Table:  {table_name}", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=10, pady=(12, 4), sticky="w")

        self.cols_frame = ctk.CTkScrollableFrame(self, label_text="Columns")
        self.cols_frame.grid(row=1, column=0, padx=10, pady=4, sticky="nsew")
        self.cols_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self, text="+ Add Column", command=self._add_col_row).grid(
            row=2, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="Apply Changes", command=self._apply).grid(
            row=3, column=0, padx=10, pady=(4, 12), sticky="ew")

        for col in columns:
            d = self._col_defaults.get(col["name"], {})
            col_default  = d.get("default") or ""
            is_identity  = d.get("is_identity", False)
            is_auto      = is_identity or ("CURRENT_TIMESTAMP" in col_default.upper())
            is_rand      = "random()" in col_default.lower()
            rand_max     = _parse_rand_max(col_default, col["type"]) if is_rand else ""
            self._add_col_row(col["name"], col["type"],
                              is_unique=col["name"] in self._original_unique_map,
                              is_auto=is_auto, is_rand=is_rand, rand_max=rand_max)

    def _add_col_row(self, name="", col_type="", is_unique=False, is_auto=False, is_rand=False, rand_max=""):
        idx = len(self._col_rows)

        outer = ctk.CTkFrame(self.cols_frame, fg_color="transparent")
        outer.grid(row=idx, column=0, padx=0, pady=(2, 6), sticky="ew")
        outer.grid_columnconfigure(0, weight=1)

        # Row 1: name, format dropdown, remove button
        row1 = ctk.CTkFrame(outer, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew")
        row1.grid_columnconfigure(0, weight=1)

        name_entry = ctk.CTkEntry(row1, placeholder_text="column name")
        name_entry.grid(row=0, column=0, padx=(0, 4), sticky="ew")
        if name:
            name_entry.insert(0, name)

        mapped = _SCHEMA_TYPE_MAP.get(col_type.lower(), col_type.upper()) if col_type else COLUMN_TYPES[0]
        options = COLUMN_TYPES[:]
        if mapped not in options:
            options.append(mapped)
        type_var = ctk.StringVar(value=mapped)
        ctk.CTkOptionMenu(row1, values=options, variable=type_var, width=140).grid(
            row=0, column=1, padx=(0, 4))

        # Row 2: Auto, Rand, Unique checkboxes
        row2 = ctk.CTkFrame(outer, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        auto_var   = ctk.BooleanVar(value=is_auto)
        rand_var   = ctk.BooleanVar(value=is_rand)
        unique_var = ctk.BooleanVar(value=is_unique)

        max_label = ctk.CTkLabel(row2, text="Max chars:")
        max_entry = ctk.CTkEntry(row2, width=65, placeholder_text="36")
        if rand_max:
            max_entry.insert(0, rand_max)

        def on_rand_toggle():
            if rand_var.get():
                max_label.grid(row=0, column=2, padx=(10, 2))
                max_entry.grid(row=0, column=3, padx=(0, 10))
            else:
                max_label.grid_remove()
                max_entry.grid_remove()

        ctk.CTkCheckBox(row2, text="Auto",   variable=auto_var,   width=70).grid(row=0, column=0, padx=(0, 6))
        ctk.CTkCheckBox(row2, text="Rand",   variable=rand_var,   width=70, command=on_rand_toggle).grid(row=0, column=1)
        ctk.CTkCheckBox(row2, text="Unique", variable=unique_var, width=80).grid(row=0, column=4, padx=(10, 0))

        # Show max_label/max_entry immediately if rand is pre-populated
        if is_rand:
            max_label.grid(row=0, column=2, padx=(10, 2))
            max_entry.grid(row=0, column=3, padx=(0, 10))

        entry = {"orig_name": name or None, "orig_type": col_type or None,
                 "name_entry": name_entry, "type_var": type_var,
                 "auto_var": auto_var, "rand_var": rand_var,
                 "max_entry": max_entry, "unique_var": unique_var, "frame": outer}

        def remove(e=entry, f=outer):
            self._col_rows[:] = [x for x in self._col_rows if x is not e]
            f.destroy()

        ctk.CTkButton(row1, text="×", width=28, command=remove).grid(row=0, column=2)
        self._col_rows.append(entry)

    def _apply(self):
        current_originals = {e["orig_name"] for e in self._col_rows if e["orig_name"] is not None}
        dropped = set(self._original_cols.keys()) - current_originals
        errors = []
        effective_names = {}
        backfill_targets = []  # [(effective_name, col_type, rand_expr)]

        # Renames and type changes for existing columns
        for e in self._col_rows:
            orig_name = e["orig_name"]
            if orig_name is None:
                continue
            new_name = e["name_entry"].get().strip()
            new_type = e["type_var"].get()
            if not new_name:
                effective_names[orig_name] = orig_name
                continue

            effective_name = orig_name
            if new_name != orig_name:
                q = f'ALTER TABLE "{self.table_name}" RENAME COLUMN "{orig_name}" TO "{new_name}";'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Rename '{orig_name}' → '{new_name}': {msg}")
                    effective_names[orig_name] = orig_name
                    continue
                effective_name = new_name
            effective_names[orig_name] = effective_name

            orig_mapped = _SCHEMA_TYPE_MAP.get((e["orig_type"] or "").lower(), (e["orig_type"] or "").upper())
            if new_type != orig_mapped:
                q = f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" TYPE {new_type};'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Change type of '{effective_name}': {msg}")

            # Auto default
            if e["auto_var"].get():
                if new_type == "INTEGER":
                    default_expr = "0"
                elif new_type in ("TIMESTAMP", "DATE"):
                    default_expr = "CURRENT_TIMESTAMP"
                else:
                    default_expr = None
                if default_expr:
                    q = f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" SET DEFAULT {default_expr};'
                    ok, msg = self.active_connector.execute_query(q)
                    if not ok:
                        errors.append(f"Set auto default for '{effective_name}': {msg}")

            # Rand default
            if e["rand_var"].get():
                col_type_for_rand = e["type_var"].get()
                expr = _rand_default_sql(col_type_for_rand, e["max_entry"].get().strip())
                q = (f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" '
                     f'SET DEFAULT {expr};')
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Set random default for '{effective_name}': {msg}")
                else:
                    backfill_targets.append((effective_name, col_type_for_rand, expr))

        # Drop removed columns
        for col_name in dropped:
            q = f'ALTER TABLE "{self.table_name}" DROP COLUMN "{col_name}";'
            ok, msg = self.active_connector.execute_query(q)
            if not ok:
                errors.append(f"Drop '{col_name}': {msg}")

        # Add new columns
        for e in self._col_rows:
            if e["orig_name"] is not None:
                continue
            col_name = e["name_entry"].get().strip()
            if not col_name:
                continue
            col_type = e["type_var"].get()
            default_clause = ""
            if e["rand_var"].get():
                expr = _rand_default_sql(col_type, e["max_entry"].get().strip())
                default_clause = f" DEFAULT {expr}"
            elif e["auto_var"].get() and col_type == "INTEGER":
                default_clause = " GENERATED ALWAYS AS IDENTITY"
            elif e["auto_var"].get() and col_type in ("TIMESTAMP", "DATE"):
                default_clause = " DEFAULT CURRENT_TIMESTAMP"
            q = f'ALTER TABLE "{self.table_name}" ADD COLUMN "{col_name}" {col_type}{default_clause};'
            ok, msg = self.active_connector.execute_query(q)
            if not ok:
                errors.append(f"Add '{col_name}': {msg}")

        # Unique constraint changes
        for e in self._col_rows:
            orig_name = e["orig_name"]
            new_unique = e["unique_var"].get()
            if orig_name is not None:
                effective = effective_names.get(orig_name, orig_name)
                was_unique = orig_name in self._original_unique_map
                constraint_name = self._original_unique_map.get(orig_name)
            else:
                effective = e["name_entry"].get().strip()
                if not effective:
                    continue
                was_unique = False
                constraint_name = None

            if new_unique and not was_unique:
                safe = effective.replace('"', '').replace(' ', '_').lower()
                q = f'ALTER TABLE "{self.table_name}" ADD CONSTRAINT "{self.table_name}_{safe}_unique" UNIQUE ("{effective}");'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Add UNIQUE for '{effective}': {msg}")
            elif not new_unique and was_unique and constraint_name:
                q = f'ALTER TABLE "{self.table_name}" DROP CONSTRAINT "{constraint_name}";'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Drop UNIQUE for '{effective}': {msg}")

        if errors:
            CTkMessagebox(title="Some changes failed", message="\n".join(errors), icon="warning", option_1="Ok")

        # Offer to backfill existing rows for any column where Rand was set
        if backfill_targets:
            col_list = "\n".join(f"  • {name} ({ctype})" for name, ctype, _ in backfill_targets)
            msg = CTkMessagebox(
                title="Update existing rows?",
                message=(
                    f"Random defaults have been set for:\n{col_list}\n\n"
                    "Do you want to overwrite ALL existing values in these columns "
                    "with newly generated random values?\n\nThis cannot be undone."
                ),
                icon="question", option_1="Yes, Update All", option_2="Cancel"
            )
            if msg.get() == "Yes, Update All":
                for eff_name, _, rand_expr in backfill_targets:
                    q = f'UPDATE "{self.table_name}" SET "{eff_name}" = {rand_expr};'
                    ok, err_msg = self.active_connector.execute_query(q)
                    if not ok:
                        CTkMessagebox(title="Backfill failed",
                                      message=f"Could not update '{eff_name}': {err_msg}",
                                      icon="cancel", option_1="Ok")

        self.destroy()
        self.master._refresh_schema()


class DeleteColumnDialog(ctk.CTkToplevel):
    def __init__(self, master, active_connector, table_name, columns):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"Delete Column — {table_name}")
        self.geometry("380x160")
        self.active_connector = active_connector
        self.table_name = table_name

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Column:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        self.col_var = ctk.StringVar(value=columns[0])
        ctk.CTkOptionMenu(self, values=columns, variable=self.col_var).grid(row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(self, text="Delete Column", command=self._delete_column).grid(row=1, column=0, columnspan=2, padx=10, pady=16, sticky="ew")

    def _delete_column(self):
        col_name = self.col_var.get()
        msg = CTkMessagebox(title="Confirm", message=f"Drop column '{col_name}'? This cannot be undone.",
                            icon="question", option_1="No", option_2="Yes")
        if msg.get() == "Yes":
            query = f'ALTER TABLE "{self.table_name}" DROP COLUMN "{col_name}";'
            success, result = self.active_connector.execute_query(query)
            if success:
                self.destroy()
                self.master._refresh_inline_table()
                self.master._refresh_schema()
            else:
                CTkMessagebox(title="Error", message=f"Failed to drop column: {result}", icon="cancel", option_1="Ok")


class DBManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("DB Manager GUI")
        self.geometry("1000x700")

        self.connection_manager = ConnectionManager()
        self.active_connector = None
        self.selected_connection_details = None # Store details of the currently selected connection

        self.status_label = None
        self.status_check_id = None
        self.status_queue = queue.Queue()
        self.default_status_color = None
        self.last_connection_status = None
        self._status_stop_event = threading.Event()
        self._status_thread = None

        self._open_table_name = None
        self._open_table_is_collection = False
        self._table_data_columns = []
        self._table_data_rows = []
        self._is_mongodb = False
        self._last_schema = None
        self._gridlines_on = False
        self._cell_editor = None
        self._col_sep_frames = []

        # Configure grid layout (2x1)
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # Left Pane (Connection List)
        self.connection_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.connection_frame.grid(row=0, column=0, sticky="nsew")
        self.connection_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.connection_frame, text="Connections", font=ctk.CTkFont(size=15, weight="bold")) \
            .grid(row=0, column=0, padx=20, pady=20)

        self.connection_buttons_frame = ctk.CTkScrollableFrame(self.connection_frame, label_text="")
        self.connection_buttons_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.connection_buttons_frame.grid_columnconfigure(0, weight=1)

        self.manage_connections_button = ctk.CTkButton(self.connection_frame, text="Manage Connections", command=self._open_manage_connections_window) # Renamed button
        self.manage_connections_button.grid(row=2, column=0, padx=20, pady=10, sticky="s")

        # Right Pane (Workspace)
        self.workspace_frame = ctk.CTkFrame(self, corner_radius=0)
        self.workspace_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.workspace_frame.grid_rowconfigure(0, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        # Connection Info Display Frame (initially visible, replaces welcome label)
        self.connection_info_frame = ctk.CTkFrame(self.workspace_frame)
        self.connection_info_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.connection_info_frame.grid_columnconfigure(0, weight=1)
        self.connection_info_frame.grid_rowconfigure(99, weight=1) # Push connect button to bottom

        # Frame to hold dynamic connection details labels
        self.connection_details_display_frame = ctk.CTkFrame(self.connection_info_frame)
        self.connection_details_display_frame.grid(row=0, column=0, padx=0, pady=0, sticky="nsew")
        self.connection_details_display_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.connection_details_display_frame, text="Select a connection from the left panel or manage connections.", font=ctk.CTkFont(size=16)).grid(row=0, column=0, padx=20, pady=20)
        
        self.connect_button = ctk.CTkButton(self.connection_info_frame, text="Connect", command=self._connect_selected_db) # Connect button for selected info
        self.connect_button.grid(row=100, column=0, padx=20, pady=20, sticky="s")
        self.connect_button.grid_remove() # Hide initially

        # Workspace Tabview (initially hidden)
        self.workspace_tabview = ctk.CTkTabview(self.workspace_frame)
        self.workspace_tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        self.workspace_tabview.grid_remove() # Hide initially

        # Schema Tab
        self.schema_tab = self.workspace_tabview.add("Schema")
        self.schema_tab.grid_rowconfigure(1, weight=1)
        self.schema_tab.grid_columnconfigure(0, weight=1)

        # Toolbar shown when browsing the table/collection list
        self.schema_toolbar = ctk.CTkFrame(self.schema_tab)
        self.schema_toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        self.schema_toolbar.grid_columnconfigure((0, 1, 2, 3, 4), weight=1)
        ctk.CTkButton(self.schema_toolbar, text="Refresh", command=self._refresh_schema).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        self._btn_open_table = ctk.CTkButton(self.schema_toolbar, text="Open Table", command=self._open_selected_table)
        self._btn_open_table.grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self._btn_edit_table = ctk.CTkButton(self.schema_toolbar, text="Edit Table", command=self._edit_selected_table)
        self._btn_edit_table.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        self._btn_add_table = ctk.CTkButton(self.schema_toolbar, text="Add Table", command=self._add_table)
        self._btn_add_table.grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        self._btn_del_table = ctk.CTkButton(self.schema_toolbar, text="Delete Table", command=self._delete_selected_table)
        self._btn_del_table.grid(row=0, column=4, padx=5, pady=5, sticky="ew")

        # Toolbar shown when a table is open inline
        self.table_toolbar = ctk.CTkFrame(self.schema_tab)
        self.table_toolbar.grid_columnconfigure((0, 1, 2, 3, 4, 5, 6, 7), weight=1)
        ctk.CTkButton(self.table_toolbar, text="← Back", command=self._show_schema_view).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.table_toolbar, text="Refresh", command=self._refresh_inline_table).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        self._btn_gridlines = ctk.CTkButton(self.table_toolbar, text="Grid: Off", command=self._toggle_gridlines)
        self._btn_gridlines.grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.table_toolbar, text="Add Row", command=self._add_row_inline).grid(row=0, column=3, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.table_toolbar, text="Edit Row", command=self._edit_row_inline).grid(row=0, column=4, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.table_toolbar, text="Delete Row", command=self._delete_row_inline).grid(row=0, column=5, padx=5, pady=5, sticky="ew")
        self._btn_add_col = ctk.CTkButton(self.table_toolbar, text="Add Column", command=self._add_column)
        self._btn_add_col.grid(row=0, column=6, padx=5, pady=5, sticky="ew")
        self._btn_del_col = ctk.CTkButton(self.table_toolbar, text="Delete Column", command=self._delete_column)
        self._btn_del_col.grid(row=0, column=7, padx=5, pady=5, sticky="ew")

        # Content area — swaps between schema list and inline data view
        self.schema_content = tk.Frame(self.schema_tab, bg="")
        self.schema_content.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.schema_content.grid_rowconfigure(0, weight=1)
        self.schema_content.grid_columnconfigure(0, weight=1)

        # Schema list sub-frame
        self.schema_list_frame = tk.Frame(self.schema_content)
        self.schema_list_frame.grid(row=0, column=0, sticky="nsew")
        self.schema_list_frame.grid_rowconfigure(0, weight=1)
        self.schema_list_frame.grid_columnconfigure(0, weight=1)
        self.schema_list_tree = ttk.Treeview(self.schema_list_frame, show="tree", selectmode="browse")
        self.schema_list_tree.grid(row=0, column=0, sticky="nsew")
        _sl_vsb = ttk.Scrollbar(self.schema_list_frame, orient="vertical", command=self.schema_list_tree.yview)
        _sl_vsb.grid(row=0, column=1, sticky="ns")
        self.schema_list_tree.configure(yscrollcommand=_sl_vsb.set)
        self.schema_list_tree.bind("<Double-Button-1>", self._on_table_double_click)

        # Inline data sub-frame (hidden until a table is opened)
        self.table_data_frame = tk.Frame(self.schema_content)
        self.table_data_frame.grid_rowconfigure(0, weight=1)
        self.table_data_frame.grid_columnconfigure(0, weight=1)
        self.data_tree = ttk.Treeview(self.table_data_frame, show="headings")
        self.data_tree.grid(row=0, column=0, sticky="nsew")
        _dt_vsb = ttk.Scrollbar(self.table_data_frame, orient="vertical", command=self.data_tree.yview)
        _dt_vsb.grid(row=0, column=1, sticky="ns")
        _dt_hsb = ttk.Scrollbar(self.table_data_frame, orient="horizontal", command=self.data_tree.xview)
        _dt_hsb.grid(row=1, column=0, sticky="ew")
        self.data_tree.configure(yscrollcommand=_dt_vsb.set, xscrollcommand=_dt_hsb.set)
        self.data_tree.tag_configure("_odd",  background="#f0f0f0", foreground="#000000")
        self.data_tree.tag_configure("_even", background="#ffffff", foreground="#000000")
        self.data_tree.bind("<Double-Button-1>", self._on_cell_double_click)
        self.data_tree.bind("<ButtonRelease-1>", lambda _: self.after(60, self._update_col_separators))

        # Query Tab
        self.query_tab = self.workspace_tabview.add("Query")
        self.query_tab.grid_rowconfigure(1, weight=1)
        self.query_tab.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self.query_tab, text="SQL/Query Editor:").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.query_editor = ctk.CTkTextbox(self.query_tab, height=150)
        self.query_editor.grid(row=1, column=0, padx=5, pady=5, sticky="nsew")

        # Buttons for Query Tab
        query_buttons_frame = ctk.CTkFrame(self.query_tab)
        query_buttons_frame.grid(row=2, column=0, padx=5, pady=5, sticky="ew")
        query_buttons_frame.grid_columnconfigure((0,1), weight=1)

        self.execute_query_button = ctk.CTkButton(query_buttons_frame, text="Execute Query", command=self._execute_query)
        self.execute_query_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.clear_query_button = ctk.CTkButton(query_buttons_frame, text="Clear", command=self._clear_query_editor)
        self.clear_query_button.grid(row=0, column=1, padx=5, pady=5, sticky="ew")

        ctk.CTkLabel(self.query_tab, text="Results:").grid(row=3, column=0, padx=5, pady=5, sticky="w")
        self.query_results = ctk.CTkTextbox(self.query_tab, wrap="word")
        self.query_results.grid(row=4, column=0, padx=5, pady=5, sticky="nsew")
        self.query_results.configure(state="disabled")

        self._load_connection_buttons()

    def _open_manage_connections_window(self):
        manage_win = ManageConnectionsWindow(self, self.connection_manager)
        manage_win.focus()
        manage_win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connection_buttons(), manage_win.destroy()))

    def _load_connection_buttons(self):
        # Clear existing buttons
        for widget in self.connection_buttons_frame.winfo_children():
            widget.destroy()

        connections = self.connection_manager.get_connections()
        for i, conn in enumerate(connections):
            conn_button = ctk.CTkButton(self.connection_buttons_frame, text=conn.get("name", "Unnamed Connection"),
                                        command=lambda c=conn: self._select_connection(c))
            conn_button.grid(row=i, column=0, padx=5, pady=5, sticky="ew")

    def _select_connection(self, connection_details):
        # Disconnect from current active DB if any
        if self.active_connector:
            self.active_connector.disconnect()
            self.active_connector = None

        self.selected_connection_details = connection_details
        self.last_connection_status = None # Reset status

        # Hide workspace tabview, show connection info frame
        self.workspace_tabview.grid_remove()
        self.connection_info_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5) # Ensure connection_info_frame is gridded

        # Clear previous info from the details display frame
        for widget in self.connection_details_display_frame.winfo_children():
            widget.destroy()

        # Display connection details
        self._display_selected_connection_info_labels(connection_details)

        # Start status check loop
        if self.status_label:
            self.status_label.configure(text="Checking...", text_color=self.default_status_color)
        self._start_status_poller()

        # Show connect button
        self.connect_button.grid(row=100, column=0, padx=20, pady=20, sticky="s")

    def _connect_selected_db(self):
        if not self.selected_connection_details:
            CTkMessagebox(title="Warning", message="No connection selected to connect.", icon="warning", option_1="Ok")
            return
        
        self._stop_status_poller()

        connection_details = self.selected_connection_details

        try:
            self.active_connector = get_connector(connection_details)
            if self.active_connector.connect():
                self.connection_info_frame.grid_remove()
                self.workspace_tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
                self.workspace_tabview.set("Schema")
                self._show_schema_view()

                schema = self.active_connector.fetch_schema()
                if schema:
                    self._display_schema(schema, connection_details["db_type"])

            else:
                # Stay on connection info frame, update status
                # Clear previous info from the details display frame
                for widget in self.connection_details_display_frame.winfo_children():
                    widget.destroy()
                # Re-display info and add error message
                self._display_selected_connection_info_labels(connection_details) # Helper to re-display labels
                ctk.CTkLabel(self.connection_details_display_frame, text=f"Failed to connect to {connection_details['name']}. Check credentials.", text_color="red").grid(row=row_idx+1, column=0, padx=20, pady=5, sticky="w")
                self.active_connector = None
        except ValueError as e:
            # Clear previous info from the details display frame
            for widget in self.connection_details_display_frame.winfo_children():
                widget.destroy()
            # Re-display info and add error message
            self._display_selected_connection_info_labels(connection_details) # Helper to re-display labels
            ctk.CTkLabel(self.connection_details_display_frame, text=f"Connection Error: {e}", text_color="red").grid(row=row_idx+1, column=0, padx=20, pady=5, sticky="w")
            self.active_connector = None
        except Exception as e:
            # Clear previous info from the details display frame
            for widget in self.connection_details_display_frame.winfo_children():
                widget.destroy()
            # Re-display info and add error message
            self._display_selected_connection_info_labels(connection_details) # Helper to re-display labels
            ctk.CTkLabel(self.connection_details_display_frame, text=f"An unexpected error occurred: {e}", text_color="red").grid(row=row_idx+1, column=0, padx=20, pady=5, sticky="w")
            self.active_connector = None

    def _display_selected_connection_info_labels(self, connection_details):
        # This helper function is called by _select_connection and _connect_selected_db
        # to populate the connection_details_display_frame with labels.
        row_idx = 0
        ctk.CTkLabel(self.connection_details_display_frame, text=f"Connection: {connection_details.get('name')}", font=ctk.CTkFont(size=18, weight="bold")).grid(row=row_idx, column=0, padx=20, pady=10, sticky="w")
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"Type: {connection_details.get('db_type')}").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w")
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"Host: {connection_details.get('host')}").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w")
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"Port: {connection_details.get('port')}").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w")
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"User: {connection_details.get('user')}").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w")
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"Database: {connection_details.get('database')}").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w")
        row_idx += 1
        
        status_frame = ctk.CTkFrame(self.connection_details_display_frame, fg_color="transparent")
        status_frame.grid(row=row_idx, column=0, padx=20, pady=2, sticky="w")
        ctk.CTkLabel(status_frame, text="Online Status: ").pack(side="left")
        self.status_label = ctk.CTkLabel(status_frame, text="Checking...")
        self.status_label.pack(side="left")
        self.default_status_color = self.status_label.cget("text_color")
        row_idx += 1

        ctk.CTkLabel(self.connection_details_display_frame, text=f"Size: N/A").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w") # Placeholder
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"Last Connected: N/A").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w") # Placeholder
        row_idx += 1
        ctk.CTkLabel(self.connection_details_display_frame, text=f"First Connected: N/A").grid(row=row_idx, column=0, padx=20, pady=2, sticky="w") # Placeholder
        row_idx += 1

    def _start_status_poller(self):
        self._stop_status_poller()
        self._status_stop_event = threading.Event()
        connection_details = self.selected_connection_details

        def poller_worker(stop_event):
            while True:
                try:
                    connector = get_connector(connection_details)
                    if connector.connect(silent=True):
                        self.status_queue.put("Online")
                        connector.disconnect(silent=True)
                    else:
                        self.status_queue.put("Offline")
                except Exception:
                    self.status_queue.put("Error")
                if stop_event.wait(30):
                    break

        self._status_thread = threading.Thread(target=poller_worker, args=(self._status_stop_event,), daemon=True)
        self._status_thread.start()
        self._poll_status_queue()

    def _stop_status_poller(self):
        self._status_stop_event.set()
        if self.status_check_id:
            self.after_cancel(self.status_check_id)
            self.status_check_id = None

    def _poll_status_queue(self):
        try:
            status = self.status_queue.get_nowait()
            if status != self.last_connection_status:
                self.last_connection_status = status
                if self.status_label and self.status_label.winfo_exists():
                    if status == "Online":
                        self.status_label.configure(text="Online", text_color="green")
                    elif status == "Offline":
                        self.status_label.configure(text="Offline", text_color="red")
                    else:
                        self.status_label.configure(text="Error", text_color="orange")
        except queue.Empty:
            pass

        if not self._status_stop_event.is_set():
            self.status_check_id = self.after(500, self._poll_status_queue)

    def _refresh_schema(self):
        if not self.active_connector:
            CTkMessagebox(title="Warning", message="Not connected to any database.", icon="warning", option_1="Ok")
            return
        schema = self.active_connector.fetch_schema()
        if schema:
            self._display_schema(schema, self.selected_connection_details["db_type"])

    def _display_schema(self, schema, db_type):
        self._is_mongodb = (db_type == "MongoDB")
        self._last_schema = schema
        self.schema_list_tree.delete(*self.schema_list_tree.get_children())

        if self._is_mongodb:
            for name in schema.get("collections", {}):
                self.schema_list_tree.insert("", "end", iid=name, text=name)
            for btn in (self._btn_edit_table, self._btn_add_table, self._btn_del_table, self._btn_add_col, self._btn_del_col):
                btn.configure(state="disabled")
        else:
            for name in schema.get("tables", {}):
                self.schema_list_tree.insert("", "end", iid=name, text=name)
            for btn in (self._btn_edit_table, self._btn_add_table, self._btn_del_table, self._btn_add_col, self._btn_del_col):
                btn.configure(state="normal")

    # ── View switching ────────────────────────────────────────────────────────

    def _show_schema_view(self):
        if self._cell_editor and self._cell_editor.winfo_exists():
            self._cell_editor.destroy()
            self._cell_editor = None
        self._clear_col_separators()
        self.table_toolbar.grid_remove()
        self.table_data_frame.grid_remove()
        self.schema_toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        self.schema_list_frame.grid(row=0, column=0, sticky="nsew")
        self._open_table_name = None

    def _open_table_inline(self, name, is_collection):
        self._open_table_name = name
        self._open_table_is_collection = is_collection
        self.schema_toolbar.grid_remove()
        self.schema_list_frame.grid_remove()
        self.table_toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        self.table_data_frame.grid(row=0, column=0, sticky="nsew")
        self.update_idletasks()
        self._refresh_inline_table()

    def _on_table_double_click(self, event):
        item = self.schema_list_tree.focus()
        if item:
            self._open_table_inline(item, self._is_mongodb)

    def _open_selected_table(self):
        item = self.schema_list_tree.focus()
        if not item:
            CTkMessagebox(title="Warning", message="No table selected.", icon="warning", option_1="Ok")
            return
        self._open_table_inline(item, self._is_mongodb)

    # ── Inline table data operations ──────────────────────────────────────────

    def _refresh_inline_table(self):
        if self._cell_editor and self._cell_editor.winfo_exists():
            self._cell_editor.destroy()
            self._cell_editor = None
        if not self._open_table_name or not self.active_connector:
            return

        success, result = self.active_connector.fetch_data(self._open_table_name)
        if not success:
            CTkMessagebox(title="Error", message=f"Failed to load table: {result}", icon="cancel", option_1="Ok")
            self._table_data_columns = []
            self._table_data_rows = []
            return

        new_cols = result.get("columns", []) if result else []
        new_rows = result.get("rows", []) if result else []
        self._table_data_columns = new_cols
        self._table_data_rows = new_rows

        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree.configure(columns=new_cols if new_cols else [], show="headings")
        for col in new_cols:
            self.data_tree.heading(col, text=col)
            self.data_tree.column(col, width=120, minwidth=60)
        for row in new_rows:
            self.data_tree.insert("", "end", values=row)
        self._apply_row_colors()
        self._update_col_separators()
        self.data_tree.update_idletasks()

    def _toggle_gridlines(self):
        self._gridlines_on = not self._gridlines_on
        self._btn_gridlines.configure(text="Grid: On" if self._gridlines_on else "Grid: Off")
        self._apply_row_colors()
        self._update_col_separators()

    def _apply_row_colors(self):
        for i, iid in enumerate(self.data_tree.get_children()):
            if self._gridlines_on:
                self.data_tree.item(iid, tags=("_odd" if i % 2 else "_even",))
            else:
                self.data_tree.item(iid, tags=())

    def _clear_col_separators(self):
        for f in self._col_sep_frames:
            try:
                f.destroy()
            except Exception:
                pass
        self._col_sep_frames = []

    def _update_col_separators(self):
        self._clear_col_separators()
        if not self._gridlines_on or not self._table_data_columns:
            return
        self.data_tree.update_idletasks()
        x = 0
        for col in self._table_data_columns[:-1]:
            try:
                x += self.data_tree.column(col, "width")
            except Exception:
                continue
            sep = tk.Frame(self.table_data_frame, width=1, bg="#c0c0c0")
            sep.place(x=x, y=0, width=1, relheight=1)
            self._col_sep_frames.append(sep)

    def _on_cell_double_click(self, event):
        item = self.data_tree.identify_row(event.y)
        col  = self.data_tree.identify_column(event.x)
        if not item or col == "#0":
            return
        col_idx = int(col[1:]) - 1
        if col_idx >= len(self._table_data_columns):
            return

        # destroy any existing editor
        if self._cell_editor and self._cell_editor.winfo_exists():
            self._cell_editor.destroy()
            self._cell_editor = None

        bbox = self.data_tree.bbox(item, col)
        if not bbox:
            return
        bx, by, bw, bh = bbox

        values = self.data_tree.item(item)["values"]
        current = str(values[col_idx]) if col_idx < len(values) else ""
        col_name = self._table_data_columns[col_idx]

        mode = ctk.get_appearance_mode()
        bg = "#2b2b2b" if mode == "Dark" else "#ffffff"
        fg = "#ffffff" if mode == "Dark" else "#000000"

        editor = tk.Entry(self.data_tree, bg=bg, fg=fg, relief="flat",
                          insertbackground=fg, font=("", 11), bd=1,
                          highlightbackground="#1f6aa5", highlightthickness=1)
        editor.insert(0, current)
        editor.select_range(0, "end")
        editor.place(x=bx, y=by, width=bw, height=bh)
        editor.focus_set()

        def save(e=None, ed=editor, it=item, ci=col_idx, cn=col_name, vals=list(values)):
            self._save_cell_edit(ed, it, ci, cn, vals)

        editor.bind("<Return>",   save)
        editor.bind("<Escape>",   lambda e, ed=editor: ed.destroy())
        editor.bind("<FocusOut>", save)
        self._cell_editor = editor

    def _save_cell_edit(self, editor, item, col_idx, col_name, original_values):
        if not editor.winfo_exists():
            return
        new_val = editor.get()
        editor.destroy()
        self._cell_editor = None

        if str(original_values[col_idx]) == new_val:
            return  # no change

        pk_col = self._table_data_columns[0]
        pk_val = original_values[0]
        success, msg = self.active_connector.update_data(
            self._open_table_name, {col_name: new_val}, {pk_col: pk_val})
        if success:
            updated = list(original_values)
            updated[col_idx] = new_val
            self.data_tree.item(item, values=updated)
            self._apply_row_colors()
        else:
            CTkMessagebox(title="Error", message=f"Failed to update cell: {msg}", icon="cancel", option_1="Ok")

    def _get_selected_data_row(self):
        item = self.data_tree.focus()
        if not item:
            return None, None
        values = self.data_tree.item(item)["values"]
        return values, dict(zip(self._table_data_columns, values))

    def _add_row_inline(self):
        if not self._table_data_columns:
            CTkMessagebox(title="Warning", message="No columns found. Refresh the table first.", icon="warning", option_1="Ok")
            return
        AddEditDataWindow(self, self.active_connector, self._open_table_name,
                          self._open_table_is_collection, self._table_data_columns, mode="add")

    def _edit_row_inline(self):
        values, row_data = self._get_selected_data_row()
        if values is None:
            CTkMessagebox(title="Warning", message="No row selected to edit.", icon="warning", option_1="Ok")
            return
        if self._open_table_is_collection and "_id" in row_data:
            for row in self._table_data_rows:
                if str(row[self._table_data_columns.index("_id")]) == str(row_data["_id"]):
                    row_data["_id"] = row[self._table_data_columns.index("_id")]
                    break
        AddEditDataWindow(self, self.active_connector, self._open_table_name,
                          self._open_table_is_collection, self._table_data_columns,
                          initial_data=row_data, mode="edit")

    def _delete_row_inline(self):
        values, row_data = self._get_selected_data_row()
        if values is None:
            CTkMessagebox(title="Warning", message="No row selected to delete.", icon="warning", option_1="Ok")
            return
        condition = {}
        if self._open_table_is_collection:
            idx = self._table_data_columns.index("_id")
            for row in self._table_data_rows:
                if str(row[idx]) == str(values[idx]):
                    condition["_id"] = row[idx]
                    break
        else:
            pk_col = self._table_data_columns[0]
            condition[pk_col] = values[0]

        msg = CTkMessagebox(title="Confirm Delete",
                            message=f"Delete selected row from {self._open_table_name}?",
                            icon="question", option_1="No", option_2="Yes")
        if msg.get() == "Yes":
            success, message = self.active_connector.delete_data(self._open_table_name, condition)
            if success:
                self._refresh_inline_table()
            else:
                CTkMessagebox(title="Error", message=f"Delete failed: {message}", icon="cancel", option_1="Ok")

    # ── Schema-level DDL operations ───────────────────────────────────────────

    def _add_table(self):
        if not self.active_connector:
            return
        AddTableDialog(self, self.active_connector)

    def _edit_selected_table(self):
        item = self.schema_list_tree.focus()
        if not item:
            CTkMessagebox(title="Warning", message="No table selected.", icon="warning", option_1="Ok")
            return
        columns = (self._last_schema or {}).get("tables", {}).get(item, {}).get("columns", [])
        EditTableDialog(self, self.active_connector, item, columns)

    def _delete_selected_table(self):
        item = self.schema_list_tree.focus()
        if not item:
            CTkMessagebox(title="Warning", message="No table selected.", icon="warning", option_1="Ok")
            return
        msg = CTkMessagebox(title="Confirm", message=f"Drop table '{item}'? This cannot be undone.",
                            icon="question", option_1="No", option_2="Yes")
        if msg.get() == "Yes":
            success, result = self.active_connector.execute_query(f'DROP TABLE "{item}";')
            if success:
                self._refresh_schema()
            else:
                CTkMessagebox(title="Error", message=f"Failed to drop table: {result}", icon="cancel", option_1="Ok")

    def _add_column(self):
        if not self._open_table_name or not self.active_connector:
            return
        AddColumnDialog(self, self.active_connector, self._open_table_name)

    def _delete_column(self):
        if not self._open_table_name or not self._table_data_columns:
            return
        DeleteColumnDialog(self, self.active_connector, self._open_table_name, self._table_data_columns)

    # ─────────────────────────────────────────────────────────────────────────

    def _execute_query(self):
        if not self.active_connector:
            self.query_results.configure(state="normal")
            self.query_results.delete("1.0", "end")
            self.query_results.insert("end", "Error: Not connected to any database.")
            self.query_results.configure(state="disabled")
            return

        query = self.query_editor.get("1.0", "end").strip()
        if not query:
            self.query_results.configure(state="normal")
            self.query_results.delete("1.0", "end")
            self.query_results.insert("end", "Error: Query cannot be empty.")
            self.query_results.configure(state="disabled")
            return

        self.query_results.configure(state="normal")
        self.query_results.delete("1.0", "end")
        self.query_results.insert("end", "Executing query...\n")
        self.query_results.configure(state="disabled")
        self.workspace_tabview.set("Query") # Switch to query tab

        success, result = self.active_connector.execute_query(query)

        self.query_results.configure(state="normal")
        self.query_results.delete("1.0", "end")
        if success:
            if isinstance(result, dict) and "rows" in result and "columns" in result:
                # Format tabular results
                columns = result["columns"]
                rows = result["rows"]
                
                header = " | ".join(columns)
                self.query_results.insert("end", header + "\n")
                self.query_results.insert("end", "-" * len(header) + "\n")
                for row in rows:
                    self.query_results.insert("end", " | ".join(map(str, row)) + "\n")
            elif isinstance(result, dict) and "message" in result:
                self.query_results.insert("end", result["message"] + "\n")
            else:
                self.query_results.insert("end", str(result) + "\n")

            # Automatically refresh schema if the query might have changed it.
            query_upper = query.upper()
            if any(keyword in query_upper for keyword in ["CREATE", "ALTER", "DROP", "RENAME", "TRUNCATE"]):
                self._refresh_schema()
        else:
            self.query_results.insert("end", f"Error: {result}\n")
        self.query_results.configure(state="disabled")

    def _clear_query_editor(self):
        self.query_editor.delete("1.0", "end")


if __name__ == "__main__":
    app = DBManagerApp()
    app.mainloop()