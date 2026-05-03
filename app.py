import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
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
    def __init__(self, master, active_connector, item_name, is_collection, columns,
                 initial_data=None, mode="add", auto_fill=None):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"{mode.capitalize()} Data: {item_name}")
        self.active_connector = active_connector
        self.item_name = item_name
        self.is_collection = is_collection
        self.columns = columns
        self.initial_data = initial_data
        self.mode = mode
        self.auto_fill = auto_fill or {}
        self.entry_widgets = {}  # col_name -> CTkEntry | CTkLabel | None (identity)

        self.grid_columnconfigure(1, weight=1)

        row = 0
        for col_name in self.columns:
            # MongoDB _id in add mode: skip entirely
            if col_name == "_id" and self.is_collection and self.mode == "add":
                self.entry_widgets[col_name] = None
                continue
            # MongoDB _id in edit mode: show read-only label
            if col_name == "_id" and self.is_collection and self.mode == "edit":
                ctk.CTkLabel(self, text=f"{col_name}:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
                lbl = ctk.CTkLabel(self, text=str(initial_data.get(col_name, "")))
                lbl.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
                self.entry_widgets[col_name] = lbl
                row += 1
                continue
            # IDENTITY column in add mode: skip field; DB generates the value
            if self.mode == "add" and self.auto_fill.get(col_name) is None and col_name in self.auto_fill:
                self.entry_widgets[col_name] = None
                continue

            ctk.CTkLabel(self, text=f"{col_name}:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self)
            entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            self.entry_widgets[col_name] = entry

            if self.mode == "add" and col_name in self.auto_fill:
                # Auto-fill: pre-populate and lock the field
                entry.insert(0, str(self.auto_fill[col_name]))
                entry.configure(state="disabled")
            elif self.mode == "edit" and initial_data and col_name != "_id":
                entry.insert(0, str(initial_data.get(col_name, "")))

            row += 1

        self.geometry("500x" + str(80 + row * 50))
        save_button = ctk.CTkButton(self, text="Save", command=self._save_data)
        save_button.grid(row=row, column=0, columnspan=2, padx=10, pady=16, sticky="ew")

    def _save_data(self):
        data = {}
        for col_name, widget in self.entry_widgets.items():
            if widget is None:
                continue  # IDENTITY / skipped column
            if isinstance(widget, ctk.CTkEntry):
                data[col_name] = widget.get()
            elif isinstance(widget, ctk.CTkLabel):
                data[col_name] = widget.cget("text")

        success = False
        message = ""

        if self.mode == "add":
            success, message = self.active_connector.insert_data(self.item_name, data)
        elif self.mode == "edit":
            condition = {}
            if self.is_collection:
                condition["_id"] = self.initial_data["_id"]
            else:
                pk_col = self.columns[0]
                condition[pk_col] = self.initial_data[pk_col]
            if pk_col in data and not self.is_collection:
                del data[pk_col]
            if "_id" in data and self.is_collection:
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
        self.geometry("600x580")
        self.active_connector = active_connector
        self._col_rows = []

        self.grid_columnconfigure(0, weight=1)
        self.grid_rowconfigure(1, weight=1)

        # Table name header (matches EditTableDialog style)
        name_row = ctk.CTkFrame(self, fg_color="transparent")
        name_row.grid(row=0, column=0, padx=10, pady=(12, 4), sticky="ew")
        name_row.grid_columnconfigure(1, weight=1)
        ctk.CTkLabel(name_row, text="Table Name:", font=ctk.CTkFont(weight="bold")).grid(
            row=0, column=0, padx=(0, 8), sticky="w")
        self.name_entry = ctk.CTkEntry(name_row, placeholder_text="table_name")
        self.name_entry.grid(row=0, column=1, sticky="ew")

        self.cols_frame = ctk.CTkScrollableFrame(self, label_text="Columns")
        self.cols_frame.grid(row=1, column=0, padx=10, pady=4, sticky="nsew")
        self.cols_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self, text="+ Add Column", command=self._add_col_row).grid(
            row=2, column=0, padx=10, pady=4, sticky="ew")
        ctk.CTkButton(self, text="Create Table", command=self._create_table).grid(
            row=3, column=0, padx=10, pady=(4, 12), sticky="ew")

        self._add_col_row()

    def _add_col_row(self):
        idx = len(self._col_rows)

        outer = ctk.CTkFrame(self.cols_frame, fg_color="transparent")
        outer.grid(row=idx, column=0, padx=0, pady=(2, 6), sticky="ew")
        outer.grid_columnconfigure(0, weight=1)

        row1 = ctk.CTkFrame(outer, fg_color="transparent")
        row1.grid(row=0, column=0, sticky="ew")
        row1.grid_columnconfigure(0, weight=1)

        name_entry = ctk.CTkEntry(row1, placeholder_text="column name")
        name_entry.grid(row=0, column=0, padx=(0, 4), sticky="ew")

        type_var = ctk.StringVar(value=COLUMN_TYPES[0])
        ctk.CTkOptionMenu(row1, values=COLUMN_TYPES, variable=type_var, width=140).grid(
            row=0, column=1, padx=(0, 4))

        # Row 2: identical layout to EditTableDialog
        row2 = ctk.CTkFrame(outer, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        pk_var     = ctk.BooleanVar(value=False)
        auto_var   = ctk.BooleanVar(value=False)
        rand_var   = ctk.BooleanVar(value=False)
        unique_var = ctk.BooleanVar(value=False)

        len_label = ctk.CTkLabel(row2, text="Length:")
        len_entry = ctk.CTkEntry(row2, width=55, placeholder_text="6")

        def on_rand_toggle():
            if rand_var.get():
                len_label.grid(row=0, column=3, padx=(8, 2))
                len_entry.grid(row=0, column=4, padx=(0, 8))
            else:
                len_label.grid_remove()
                len_entry.grid_remove()

        def on_pk_toggle():
            if pk_var.get():
                for other in self._col_rows:
                    if other["pk_var"] is not pk_var:
                        other["pk_cb"].grid_remove()
            else:
                for other in self._col_rows:
                    if other["pk_var"] is not pk_var:
                        other["pk_cb"].grid()

        pk_cb = ctk.CTkCheckBox(row2, text="PK", variable=pk_var, width=55, command=on_pk_toggle)
        pk_cb.grid(row=0, column=0, padx=(0, 4))
        ctk.CTkCheckBox(row2, text="Auto",   variable=auto_var,   width=65).grid(row=0, column=1, padx=(0, 4))
        ctk.CTkCheckBox(row2, text="Rand",   variable=rand_var,   width=65, command=on_rand_toggle).grid(row=0, column=2)
        ctk.CTkCheckBox(row2, text="Unique", variable=unique_var, width=75).grid(row=0, column=5, padx=(10, 0))

        entry = {"name_entry": name_entry, "type_var": type_var,
                 "pk_var": pk_var, "pk_cb": pk_cb,
                 "auto_var": auto_var, "rand_var": rand_var,
                 "max_entry": len_entry, "unique_var": unique_var, "frame": outer}

        def do_remove(e=entry, f=outer):
            was_pk = e["pk_var"].get()
            self._col_rows[:] = [x for x in self._col_rows if x is not e]
            f.destroy()
            if was_pk:
                for other in self._col_rows:
                    if other["pk_cb"].winfo_exists():
                        other["pk_cb"].grid()

        ctk.CTkButton(row1, text="×", width=28, command=do_remove).grid(row=0, column=2)
        self._col_rows.append(entry)

        # If another row already owns PK, hide this new row's PK checkbox
        if any(e["pk_var"].get() for e in self._col_rows if e is not entry):
            pk_cb.grid_remove()

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
            col_type   = e["type_var"].get()
            unique_sql = " UNIQUE" if e["unique_var"].get() else ""

            if e["rand_var"].get():
                expr = _rand_default_sql(col_type, e["max_entry"].get().strip())
                col_def = f'"{name}" {col_type} DEFAULT {expr}{unique_sql}'
            elif e["auto_var"].get() and col_type == "INTEGER":
                col_def = f'"{name}" INTEGER GENERATED ALWAYS AS IDENTITY{unique_sql}'
            elif e["auto_var"].get() and col_type in ("TIMESTAMP", "DATE"):
                col_def = f'"{name}" {col_type} DEFAULT CURRENT_TIMESTAMP{unique_sql}'
            else:
                col_def = f'"{name}" {col_type}{unique_sql}'

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
        ok, result = self.active_connector.execute_query(query)
        if ok:
            self.destroy()
            self.master._refresh_schema()
        else:
            CTkMessagebox(title="Error", message=f"Failed to create table:\n{result}", icon="cancel", option_1="Ok")


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


def _rand_default_sql(col_type: str, length: str) -> str:
    """Return a PostgreSQL DEFAULT expression producing exactly `length` chars/digits."""
    try:
        n = max(1, int(length))
    except (ValueError, TypeError):
        n = 6
    text_types  = {"TEXT", "VARCHAR(255)"}
    int_types   = {"INTEGER"}
    float_types = {"REAL", "NUMERIC", "MONEY"}
    bool_types  = {"BOOLEAN"}
    date_types  = {"DATE"}
    ts_types    = {"TIMESTAMP"}
    if col_type in text_types:
        # md5 always produces 32 hex chars, so substring is exactly n chars
        return f"substring(md5(random()::text) from 1 for {min(n, 32)})"
    if col_type in int_types:
        # range [10^(n-1), 10^n - 1] — always exactly n digits
        low  = 10 ** (n - 1)
        high = 9 * (10 ** (n - 1))
        return f"(floor(random() * {high}) + {low})::integer"
    if col_type in float_types:
        low  = 10 ** (n - 1)
        high = 9 * (10 ** (n - 1))
        return f"round((random() * {high} + {low})::numeric, 2)"
    if col_type in bool_types:
        return "(random() > 0.5)"
    if col_type in date_types:
        return f"(current_date - (random() * {n * 30})::integer)"
    if col_type in ts_types:
        return f"(now() - (random() * interval '{n * 30} days'))"
    return f"substring(md5(random()::text) from 1 for {min(n, 32)})"


def _parse_rand_max(col_default: str, col_type: str) -> str:
    """Recover the length number from a rand DEFAULT expression."""
    import re, math
    if not col_default:
        return "6"
    # TEXT/VARCHAR: substring(md5(random()::text) from 1 for N)
    m = re.search(r"for (\d+)\)", col_default)
    if m:
        return m.group(1)
    # Exact-N integer/numeric: (floor(random() * high) + low)::...
    # low = 10^(n-1), so n = floor(log10(low)) + 1
    m = re.search(r"\) \+ (\d+)\)", col_default)
    if m:
        try:
            low = int(m.group(1))
            return str(int(math.floor(math.log10(low))) + 1) if low > 0 else "6"
        except Exception:
            return "6"
    # Legacy: floor(random() * N)::integer  — N = 10^n
    m = re.search(r"random\(\) \* (\d+)", col_default)
    if m:
        try:
            n = int(m.group(1))
            return str(int(round(math.log10(n)))) if n > 1 else "1"
        except Exception:
            return "6"
    return "6"


def _generate_rand_value_py(col_default: str) -> str:
    """Generate a Python-side random value matching a DB DEFAULT expression."""
    import re as _re, random as _rng, hashlib as _hs, datetime as _dt, math as _math
    if not col_default:
        return ""
    d = col_default.lower()
    if "current_timestamp" in d or "now()" in d:
        return _dt.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    if "random()" not in d:
        return col_default
    # TEXT: substring(md5(random()::text) from 1 for N)
    m = _re.search(r"for (\d+)\)", col_default, _re.IGNORECASE)
    if m:
        n = int(m.group(1))
        return _hs.md5(str(_rng.random()).encode()).hexdigest()[:n]
    # Exact integer/numeric: (floor(random() * high) + low)
    m = _re.search(r"random\(\) \* (\d+)\) \+ (\d+)", col_default)
    if m:
        high, low = int(m.group(1)), int(m.group(2))
        return str(_rng.randint(low, low + high - 1))
    # Exact numeric (no parens before +): random() * high + low
    m = _re.search(r"random\(\) \* (\d+) \+ (\d+)", col_default)
    if m:
        high, low = int(m.group(1)), int(m.group(2))
        return str(round(_rng.uniform(low, low + high), 2))
    # BOOLEAN
    if "random() > 0.5" in d:
        return str(_rng.random() > 0.5)
    # DATE/TIMESTAMP: random() * N days
    m = _re.search(r"random\(\) \* (\d+)", col_default)
    if m:
        days = int(m.group(1))
        offset = _rng.randint(0, days)
        return (_dt.date.today() - _dt.timedelta(days=offset)).strftime("%Y-%m-%d")
    return ""


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
        pk_list, self._pk_constraint_name = active_connector.fetch_primary_keys(table_name)
        self._pk_cols_set = set(pk_list)
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
            is_rand      = "random()" in col_default.lower()
            is_auto      = is_identity or ("CURRENT_TIMESTAMP" in col_default.upper()) or is_rand
            rand_max     = _parse_rand_max(col_default, col["type"]) if is_rand else ""
            self._add_col_row(col["name"], col["type"],
                              is_pk=col["name"] in self._pk_cols_set,
                              is_unique=col["name"] in self._original_unique_map,
                              is_auto=is_auto, is_rand=is_rand, rand_max=rand_max)

    def _add_col_row(self, name="", col_type="", is_pk=False, is_unique=False, is_auto=False, is_rand=False, rand_max=""):
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

        # Row 2: PK, Auto, Rand, Length, Unique checkboxes
        row2 = ctk.CTkFrame(outer, fg_color="transparent")
        row2.grid(row=1, column=0, sticky="ew", pady=(2, 0))

        pk_var     = ctk.BooleanVar(value=is_pk)
        auto_var   = ctk.BooleanVar(value=is_auto)
        rand_var   = ctk.BooleanVar(value=is_rand)
        unique_var = ctk.BooleanVar(value=is_unique)

        len_label = ctk.CTkLabel(row2, text="Length:")
        len_entry = ctk.CTkEntry(row2, width=55, placeholder_text="6")
        if rand_max:
            len_entry.insert(0, rand_max)

        def on_rand_toggle():
            if rand_var.get():
                len_label.grid(row=0, column=3, padx=(8, 2))
                len_entry.grid(row=0, column=4, padx=(0, 8))
            else:
                len_label.grid_remove()
                len_entry.grid_remove()

        def on_pk_toggle():
            if pk_var.get():
                for other in self._col_rows:
                    if other["pk_var"] is not pk_var:
                        other["pk_cb"].grid_remove()
            else:
                for other in self._col_rows:
                    if other["pk_var"] is not pk_var:
                        other["pk_cb"].grid()

        pk_cb = ctk.CTkCheckBox(row2, text="PK", variable=pk_var, width=55, command=on_pk_toggle)
        pk_cb.grid(row=0, column=0, padx=(0, 4))
        ctk.CTkCheckBox(row2, text="Auto",   variable=auto_var,   width=65).grid(row=0, column=1, padx=(0, 4))
        ctk.CTkCheckBox(row2, text="Rand",   variable=rand_var,   width=65, command=on_rand_toggle).grid(row=0, column=2)
        ctk.CTkCheckBox(row2, text="Unique", variable=unique_var, width=75).grid(row=0, column=5, padx=(10, 0))

        # Show length field immediately if rand is pre-populated
        if is_rand:
            len_label.grid(row=0, column=3, padx=(8, 2))
            len_entry.grid(row=0, column=4, padx=(0, 8))

        entry = {"orig_name": name or None, "orig_type": col_type or None,
                 "name_entry": name_entry, "type_var": type_var,
                 "pk_var": pk_var, "pk_cb": pk_cb,
                 "auto_var": auto_var, "rand_var": rand_var,
                 "max_entry": len_entry, "unique_var": unique_var, "frame": outer}

        def remove(e=entry, f=outer):
            was_pk = e["pk_var"].get()
            self._col_rows[:] = [x for x in self._col_rows if x is not e]
            f.destroy()
            if was_pk:
                for other in self._col_rows:
                    if other["pk_cb"].winfo_exists():
                        other["pk_cb"].grid()

        ctk.CTkButton(row1, text="×", width=28, command=remove).grid(row=0, column=2)
        self._col_rows.append(entry)
        if any(e["pk_var"].get() for e in self._col_rows if e is not entry):
            pk_cb.grid_remove()

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

            # Auto default — only applies when Rand is NOT also checked
            # (if Rand is checked, the random() expression IS the auto default)
            if e["auto_var"].get() and not e["rand_var"].get():
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

        # Primary key changes
        new_pk_effective = []
        for e in self._col_rows:
            if not e["pk_var"].get():
                continue
            new_name = e["name_entry"].get().strip()
            if not new_name:
                continue
            orig = e["orig_name"]
            new_pk_effective.append(effective_names.get(orig, orig) if orig else new_name)
        if set(new_pk_effective) != self._pk_cols_set:
            if self._pk_constraint_name:
                q = f'ALTER TABLE "{self.table_name}" DROP CONSTRAINT "{self._pk_constraint_name}";'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Drop PRIMARY KEY: {msg}")
            if new_pk_effective:
                cols_sql = ", ".join(f'"{c}"' for c in new_pk_effective)
                q = f'ALTER TABLE "{self.table_name}" ADD PRIMARY KEY ({cols_sql});'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Set PRIMARY KEY: {msg}")

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


class QueryWindow(ctk.CTkToplevel):
    def __init__(self, master):
        super().__init__(master)
        self.title("Query Editor")
        self.geometry("900x620")
        self.lift()
        self.focus_force()

        self.grid_rowconfigure(1, weight=2)
        self.grid_rowconfigure(4, weight=3)
        self.grid_columnconfigure(0, weight=1)

        ctk.CTkLabel(self, text="SQL / Query Editor:", anchor="w").grid(
            row=0, column=0, padx=10, pady=(10, 2), sticky="ew")
        self.query_editor = ctk.CTkTextbox(self, height=200, wrap="none")
        self.query_editor.grid(row=1, column=0, padx=10, pady=(0, 4), sticky="nsew")

        btn_frame = ctk.CTkFrame(self, fg_color="transparent")
        btn_frame.grid(row=2, column=0, padx=10, pady=(0, 4), sticky="ew")
        btn_frame.grid_columnconfigure(2, weight=1)
        ctk.CTkButton(btn_frame, text="Execute", width=120, command=self._execute).grid(
            row=0, column=0, padx=(0, 6))
        ctk.CTkButton(btn_frame, text="Clear", width=80,
                      fg_color="transparent", border_width=1, command=self._clear).grid(
            row=0, column=1)

        ctk.CTkLabel(self, text="Results:", anchor="w").grid(
            row=3, column=0, padx=10, pady=(4, 2), sticky="ew")
        self.results_box = ctk.CTkTextbox(self, wrap="none")
        self.results_box.grid(row=4, column=0, padx=10, pady=(0, 10), sticky="nsew")
        self.results_box.configure(state="disabled")

    def _execute(self):
        connector = self.master.active_connector
        if not connector:
            self._show("Error: Not connected to any database.")
            return
        query = self.query_editor.get("1.0", "end").strip()
        if not query:
            self._show("Error: Query cannot be empty.")
            return
        self._show("Executing query…\n")
        success, result = connector.execute_query(query)
        if success:
            if isinstance(result, dict) and "rows" in result and "columns" in result:
                cols = result["columns"]
                rows = result["rows"]
                header = " | ".join(cols)
                lines = [header, "-" * len(header)]
                lines += [" | ".join(map(str, r)) for r in rows]
                self._show("\n".join(lines))
            elif isinstance(result, dict) and "message" in result:
                self._show(result["message"])
            else:
                self._show(str(result))
            query_upper = query.upper()
            if any(kw in query_upper for kw in ["CREATE", "ALTER", "DROP", "RENAME", "TRUNCATE"]):
                self.master._refresh_schema()
        else:
            self._show(f"Error: {result}")

    def _clear(self):
        self.query_editor.delete("1.0", "end")

    def _show(self, text: str):
        self.results_box.configure(state="normal")
        self.results_box.delete("1.0", "end")
        self.results_box.insert("end", text)
        self.results_box.configure(state="disabled")


class DBManagerApp(ctk.CTk):
    def __init__(self):
        super().__init__()

        self.title("BaseCrawler 0.7.51-alpha")
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
        self.connect_button = None
        self._user_entry = None
        self._pw_entry = None
        self._save_pw_var = None

        self._open_table_name = None
        self._open_table_is_collection = False
        self._table_data_columns = []
        self._table_data_rows = []
        self._table_col_defaults = {}
        self._is_mongodb = False
        self._last_schema = None
        self._connection_states = {}   # {conn_name: {open_table, is_collection, schema, db_type}}
        self._gridlines_on = True
        self._cell_editor = None
        self._col_sep_frames = []
        self._auto_refresh_id = None
        self._col_widths = {}  # {(table_name, col_name): pixel_width}

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
        self.workspace_frame.grid_rowconfigure(0, weight=0)  # top bar
        self.workspace_frame.grid_rowconfigure(1, weight=1)  # main content
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        # ── Top bar (sidebar toggle + edit mode) ─────────────────────────────
        self._sidebar_visible = True
        self._edit_mode = True
        topbar = ctk.CTkFrame(self.workspace_frame, height=36, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        topbar.grid_columnconfigure(1, weight=1)

        self._sidebar_btn = ctk.CTkButton(topbar, text="◀ Hide Panel", width=110, height=28,
                                          command=self._toggle_sidebar)
        self._sidebar_btn.grid(row=0, column=0, padx=(0, 8))

        self._grid_cb = ctk.CTkCheckBox(topbar, text="⊞", width=50,
                                        command=self._toggle_gridlines)
        self._grid_cb.select()               # grid on by default
        self._grid_cb.grid(row=0, column=2, padx=(0, 4))

        self._edit_mode_cb = ctk.CTkCheckBox(topbar, text="✏", width=50,
                                             command=self._apply_edit_mode)
        self._edit_mode_cb.select()          # edit mode on by default
        self._edit_mode_cb.grid(row=0, column=3, padx=(0, 8))

        # Connection Info Display Frame (initially visible, replaces welcome label)
        self.connection_info_frame = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.connection_info_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.connection_info_frame.grid_columnconfigure(0, weight=1)
        self.connection_info_frame.grid_rowconfigure(0, weight=1)

        # Dynamic content area — rebuilt each time a connection is selected
        self.connection_details_display_frame = ctk.CTkFrame(self.connection_info_frame, fg_color="transparent")
        self.connection_details_display_frame.grid(row=0, column=0, sticky="nsew")
        self.connection_details_display_frame.grid_columnconfigure(0, weight=1)
        self.connection_details_display_frame.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(self.connection_details_display_frame,
                     text="Select a connection from the left panel or manage connections.",
                     font=ctk.CTkFont(size=16)).grid(row=0, column=0, padx=20, pady=20)

        # Workspace panel (initially hidden, replaces old tabview)
        self.workspace_panel = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.workspace_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.workspace_panel.grid_remove()

        self.schema_tab = self.workspace_panel
        self.schema_tab.grid_rowconfigure(1, weight=1)
        self.schema_tab.grid_columnconfigure(0, weight=1)

        # ── Schema ribbon toolbar (table list view) ───────────────────────────
        self.schema_toolbar = ctk.CTkFrame(self.schema_tab, height=72, corner_radius=0)
        self.schema_toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 0))
        self.schema_toolbar.pack_propagate(False)

        [self._btn_open_table] = self._ribbon_group(
            self.schema_toolbar, "View",
            [("▶", "Open", self._open_selected_table)],
        )
        self._ribbon_sep(self.schema_toolbar)
        self._btn_edit_table, self._btn_add_table, self._btn_del_table = self._ribbon_group(
            self.schema_toolbar, "Tables", [
                ("✎", "Edit",   self._edit_selected_table),
                ("⊕", "Add",    self._add_table),
                ("⊗", "Delete", self._delete_selected_table),
            ],
        )
        self._ribbon_sep(self.schema_toolbar)
        self._ribbon_group(
            self.schema_toolbar, "Query",
            [("≡", "SQL", self._open_query_wizard)],
        )
        self._ribbon_sep(self.schema_toolbar)
        [disc_btn] = self._ribbon_group(
            self.schema_toolbar, "Connection",
            [("⏻", "Disconnect", self._disconnect_db)],
        )
        disc_btn.configure(text_color="#DD4444")

        # ── Table ribbon toolbar (inline data view) ───────────────────────────
        self.table_toolbar = ctk.CTkFrame(self.schema_tab, height=72, corner_radius=0)
        self.table_toolbar.pack_propagate(False)

        self._ribbon_group(
            self.table_toolbar, "Navigate",
            [("◀", "Back", self._show_schema_view)],
        )
        self._ribbon_sep(self.table_toolbar)
        self._btn_add_row, self._btn_edit_row, self._btn_del_row = self._ribbon_group(
            self.table_toolbar, "Rows", [
                ("⊕", "Add",    self._add_row_inline),
                ("✎", "Edit",   self._edit_row_inline),
                ("⊗", "Delete", self._delete_row_inline),
            ],
        )
        self._ribbon_sep(self.table_toolbar)
        self._btn_add_col, self._btn_del_col = self._ribbon_group(
            self.table_toolbar, "Columns", [
                ("⊕", "Add",    self._add_column),
                ("⊗", "Delete", self._delete_column),
            ],
        )
        self._ribbon_sep(self.table_toolbar)
        self._ribbon_group(
            self.table_toolbar, "Query",
            [("≡", "SQL", self._open_query_wizard)],
        )

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
        self._reconfigure_tree_tags()
        self.data_tree.bind("<Double-Button-1>", self._on_cell_double_click)
        self.data_tree.bind("<ButtonRelease-1>", self._on_tree_mouse_release)

        self._query_window = None  # singleton QueryWindow reference

        self._load_connection_buttons()

    def _open_manage_connections_window(self):
        manage_win = ManageConnectionsWindow(self, self.connection_manager)
        manage_win.focus()
        manage_win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connection_buttons(), manage_win.destroy()))

    def _toggle_sidebar(self):
        if self._sidebar_visible:
            self.connection_frame.grid_remove()
            self.grid_columnconfigure(0, weight=0, minsize=0)
            self._sidebar_btn.configure(text="▶ Show Panel")
            self._sidebar_visible = False
        else:
            self.connection_frame.grid()
            self.grid_columnconfigure(0, weight=0)
            self._sidebar_btn.configure(text="◀ Hide Panel")
            self._sidebar_visible = True

    def _apply_edit_mode(self):
        self._edit_mode = bool(self._edit_mode_cb.get())
        state = "normal" if self._edit_mode else "disabled"
        for btn in [self._btn_edit_table, self._btn_add_table, self._btn_del_table,
                    self._btn_add_row, self._btn_edit_row, self._btn_del_row,
                    self._btn_add_col, self._btn_del_col]:
            btn.configure(state=state)

    # ── Ribbon helpers ────────────────────────────────────────────────────────

    def _ribbon_group(self, ribbon, title, buttons):
        """Add a labeled group of icon buttons to a ribbon toolbar.

        buttons: list of (icon_char, short_label, command)
        Returns list of CTkButton in order.
        """
        gf = ctk.CTkFrame(ribbon, fg_color="transparent")
        gf.pack(side="left", fill="y")

        # Group title + thin rule — claimed first so pack(side=bottom) reserves the space
        ctk.CTkLabel(
            gf, text=title,
            font=ctk.CTkFont(size=9),
            text_color=("gray45", "gray55"),
        ).pack(side="bottom", pady=(0, 3))
        ctk.CTkFrame(gf, height=1, fg_color=("gray75", "gray40")).pack(
            side="bottom", fill="x", padx=6, pady=(0, 1))

        # Button row
        btn_row = ctk.CTkFrame(gf, fg_color="transparent")
        btn_row.pack(side="top", fill="both", expand=True, padx=4, pady=(5, 2))

        created = []
        for col, (icon, lbl, cmd) in enumerate(buttons):
            item = ctk.CTkFrame(btn_row, fg_color="transparent")
            item.grid(row=0, column=col, padx=2)

            btn = ctk.CTkButton(
                item, text=icon, width=48, height=38,
                font=ctk.CTkFont(size=19),
                fg_color="transparent",
                hover_color=("gray78", "gray28"),
                text_color=("gray10", "gray90"),
                corner_radius=6,
                command=cmd,
            )
            btn.pack()
            ctk.CTkLabel(
                item, text=lbl,
                font=ctk.CTkFont(size=9),
                text_color=("gray35", "gray65"),
            ).pack(pady=(1, 0))
            created.append(btn)

        return created

    def _ribbon_sep(self, ribbon):
        sep = tk.Frame(ribbon, width=1,
                       bg="#666" if ctk.get_appearance_mode() == "Dark" else "#bbb")
        sep.pack(side="left", fill="y", pady=8, padx=3)
        sep.pack_propagate(False)

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
        conn_name = connection_details.get("name")

        # Save workspace state for whichever connection is currently active
        self._stop_auto_refresh()
        if self.active_connector and self.selected_connection_details:
            current_name = self.selected_connection_details.get("name")
            self._connection_states[current_name] = {
                "open_table":    self._open_table_name,
                "is_collection": self._open_table_is_collection,
                "schema":        self._last_schema,
                "db_type":       self.selected_connection_details.get("db_type"),
            }
            self.active_connector.disconnect(silent=True)
            self.active_connector = None

        self.selected_connection_details = connection_details
        self.last_connection_status = None

        # Try to restore a previously saved workspace for this connection
        saved = self._connection_states.get(conn_name)
        if saved:
            try:
                connector = get_connector(connection_details)
                if connector.connect(silent=True):
                    self.active_connector = connector
                    self._last_schema = saved.get("schema")
                    self._is_mongodb = (connection_details.get("db_type") == "MongoDB")

                    self.connection_info_frame.grid_remove()
                    self.workspace_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

                    # Restore schema list first
                    self._show_schema_view()
                    if self._last_schema:
                        self._display_schema(self._last_schema, connection_details.get("db_type"))

                    # Restore open table if one was open
                    if saved.get("open_table"):
                        self._open_table_inline(saved["open_table"], saved.get("is_collection", False))

                    self._start_status_poller()
                    self._start_auto_refresh()
                    return
            except Exception:
                self.active_connector = None

        # No saved state or reconnect failed — show connection info panel
        self.workspace_panel.grid_remove()
        self.connection_info_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        for widget in self.connection_details_display_frame.winfo_children():
            widget.destroy()
        self._display_selected_connection_info_labels(connection_details)
        if self.status_label:
            self.status_label.configure(text="Checking...", text_color=self.default_status_color)
        self._start_status_poller()

    def _disconnect_db(self):
        """Manually disconnect and return to the connection info panel, clearing saved state."""
        self._stop_auto_refresh()
        if self.active_connector:
            self.active_connector.disconnect(silent=True)
            self.active_connector = None
        if self.selected_connection_details:
            conn_name = self.selected_connection_details.get("name")
            self._connection_states.pop(conn_name, None)
        self._show_schema_view()
        self.workspace_panel.grid_remove()
        self.connection_info_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        for widget in self.connection_details_display_frame.winfo_children():
            widget.destroy()
        if self.selected_connection_details:
            self._display_selected_connection_info_labels(self.selected_connection_details)
        if self.status_label:
            self.status_label.configure(text="Checking...", text_color=self.default_status_color)
        self._start_status_poller()

    def _connect_selected_db(self):
        if not self.selected_connection_details:
            CTkMessagebox(title="Warning", message="No connection selected to connect.", icon="warning", option_1="Ok")
            return
        
        self._stop_status_poller()

        # Build effective connection details, overriding with whatever is in the entry fields
        connection_details = dict(self.selected_connection_details)
        if self._user_entry and self._user_entry.winfo_exists():
            connection_details["user"] = self._user_entry.get().strip()
        if self._pw_entry and self._pw_entry.winfo_exists():
            connection_details["password"] = self._pw_entry.get()

        try:
            self.active_connector = get_connector(connection_details)
            if self.active_connector.connect():
                # Persist credentials: always save username; save password only if checked
                save_pw = bool(self._save_pw_var.get()) if self._save_pw_var else False
                to_save = dict(self.selected_connection_details)
                to_save["user"] = connection_details["user"]
                to_save["password"] = connection_details["password"] if save_pw else ""
                self.connection_manager.update_connection(to_save["name"], to_save)
                self.selected_connection_details = to_save

                self.connection_info_frame.grid_remove()
                self.workspace_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
                self._show_schema_view()

                schema = self.active_connector.fetch_schema()
                if schema:
                    self._display_schema(schema, connection_details["db_type"])

                self._start_auto_refresh()

            else:
                CTkMessagebox(title="Connection Failed",
                              message=f"Could not connect to '{connection_details['name']}'.\nCheck your credentials and try again.",
                              icon="cancel", option_1="Ok")
                self.active_connector = None
        except ValueError as e:
            CTkMessagebox(title="Connection Error", message=str(e), icon="cancel", option_1="Ok")
            self.active_connector = None
        except Exception as e:
            CTkMessagebox(title="Unexpected Error", message=str(e), icon="cancel", option_1="Ok")
            self.active_connector = None

    def _display_selected_connection_info_labels(self, connection_details):
        parent = self.connection_details_display_frame
        parent.grid_columnconfigure(0, weight=1)
        parent.grid_columnconfigure(1, weight=1)
        parent.grid_rowconfigure(0, weight=0)
        parent.grid_rowconfigure(1, weight=0)
        parent.grid_rowconfigure(2, weight=1)   # bottom spacer

        # ── Connection name ──────────────────────────────────────────────
        ctk.CTkLabel(
            parent,
            text=connection_details.get("name", ""),
            font=ctk.CTkFont(size=22, weight="bold"),
            anchor="w",
        ).grid(row=0, column=0, columnspan=2, padx=24, pady=(24, 12), sticky="w")

        # ── Info card ────────────────────────────────────────────────────
        card = ctk.CTkFrame(parent, corner_radius=12)
        card.grid(row=1, column=0, padx=(24, 10), pady=(0, 24), sticky="new")
        card.grid_columnconfigure(1, weight=1)

        card_fields = [
            ("Type",   connection_details.get("db_type", "—")),
            ("Host",   connection_details.get("host",    "—")),
            ("Port",   str(connection_details.get("port", "—"))),
            ("DB",     connection_details.get("database", "—")),
            ("Status", None),
            ("Size",   "—"),
        ]
        for i, (lbl, val) in enumerate(card_fields):
            pt = 12 if i == 0 else 4
            pb = 12 if i == len(card_fields) - 1 else 4
            ctk.CTkLabel(card, text=lbl + ":", anchor="w",
                         font=ctk.CTkFont(weight="bold")).grid(
                row=i, column=0, padx=(14, 6), pady=(pt, pb), sticky="w")
            if val is None:
                self.status_label = ctk.CTkLabel(card, text="Checking…", anchor="w")
                self.status_label.grid(row=i, column=1, padx=(0, 14), pady=(pt, pb), sticky="w")
                self.default_status_color = self.status_label.cget("text_color")
            else:
                ctk.CTkLabel(card, text=val, anchor="w").grid(
                    row=i, column=1, padx=(0, 14), pady=(pt, pb), sticky="w")

        # ── Credentials panel ────────────────────────────────────────────
        cred = ctk.CTkFrame(parent, fg_color="transparent")
        cred.grid(row=1, column=1, padx=(10, 24), pady=(0, 24), sticky="new")
        cred.grid_columnconfigure(0, weight=1)
        cred.grid_columnconfigure(1, weight=0)

        ctk.CTkLabel(cred, text="Username", anchor="w").grid(
            row=0, column=0, columnspan=2, pady=(0, 3), sticky="w")
        self._user_entry = ctk.CTkEntry(cred, placeholder_text="username")
        self._user_entry.insert(0, connection_details.get("user", ""))
        self._user_entry.grid(row=1, column=0, columnspan=2, pady=(0, 14), sticky="ew")

        ctk.CTkLabel(cred, text="Password", anchor="w").grid(
            row=2, column=0, columnspan=2, pady=(0, 3), sticky="w")
        self._pw_entry = ctk.CTkEntry(cred, show="•", placeholder_text="password")
        self._pw_entry.insert(0, connection_details.get("password", ""))
        self._pw_entry.grid(row=3, column=0, columnspan=2, pady=(0, 14), sticky="ew")

        has_saved_pw = bool(connection_details.get("password"))
        self._save_pw_var = ctk.BooleanVar(value=has_saved_pw)
        ctk.CTkCheckBox(cred, text="Save password", variable=self._save_pw_var).grid(
            row=4, column=0, sticky="w")

        self.connect_button = ctk.CTkButton(
            cred, text="Connect", width=120, command=self._connect_selected_db)
        self.connect_button.grid(row=4, column=1, padx=(10, 0), sticky="e")

        self._user_entry.bind("<Return>", lambda _: self._connect_selected_db())
        self._pw_entry.bind("<Return>",   lambda _: self._connect_selected_db())

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

    def _refresh_schema(self, silent=False):
        if not self.active_connector:
            if not silent:
                CTkMessagebox(title="Warning", message="Not connected to any database.", icon="warning", option_1="Ok")
            return
        schema = self.active_connector.fetch_schema()
        if schema:
            self._display_schema(schema, self.selected_connection_details["db_type"])

    def _start_auto_refresh(self):
        self._stop_auto_refresh()
        self._auto_refresh_id = self.after(5000, self._auto_refresh)

    def _stop_auto_refresh(self):
        if self._auto_refresh_id is not None:
            self.after_cancel(self._auto_refresh_id)
            self._auto_refresh_id = None

    def _auto_refresh(self):
        if not self.active_connector:
            return
        try:
            if self._open_table_name:
                self._refresh_inline_table()
            else:
                schema = self.active_connector.fetch_schema()
                if schema:
                    self._display_schema(schema, self.selected_connection_details["db_type"])
        except Exception:
            pass
        self._auto_refresh_id = self.after(5000, self._auto_refresh)

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
        self._table_col_defaults = self.active_connector.fetch_column_defaults(self._open_table_name)
        pk_cols, _ = self.active_connector.fetch_primary_keys(self._open_table_name)
        pk_set = set(pk_cols)

        self.data_tree.delete(*self.data_tree.get_children())
        self.data_tree.configure(columns=new_cols if new_cols else [], show="headings")
        for col in new_cols:
            label = f"🔑 {col}" if col in pk_set else col
            self.data_tree.heading(col, text=label)
            saved_w = self._col_widths.get((self._open_table_name, col), 120)
            self.data_tree.column(col, width=saved_w, minwidth=40)
        for row in new_rows:
            self.data_tree.insert("", "end", values=row)
        self._apply_row_colors()
        self._update_col_separators()
        self.data_tree.update_idletasks()

    def _toggle_gridlines(self):
        self._gridlines_on = bool(self._grid_cb.get())
        self._apply_row_colors()
        self._update_col_separators()

    def _reconfigure_tree_tags(self):
        if ctk.get_appearance_mode() == "Dark":
            self.data_tree.tag_configure("_odd",  background="#2a2a2a", foreground="#e0e0e0")
            self.data_tree.tag_configure("_even", background="#1e1e1e", foreground="#e0e0e0")
        else:
            self.data_tree.tag_configure("_odd",  background="#f0f0f0", foreground="#000000")
            self.data_tree.tag_configure("_even", background="#ffffff", foreground="#000000")

    def _apply_row_colors(self):
        self._reconfigure_tree_tags()
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
            sep_color = "#555555" if ctk.get_appearance_mode() == "Dark" else "#c0c0c0"
            sep = tk.Frame(self.table_data_frame, width=1, bg=sep_color)
            sep.place(x=x, y=0, width=1, relheight=1)
            self._col_sep_frames.append(sep)

    def _on_tree_mouse_release(self, _event):
        def _update():
            self._save_col_widths()
            self._update_col_separators()
        self.after(60, _update)

    def _save_col_widths(self):
        if not self._open_table_name or not self._table_data_columns:
            return
        for col in self._table_data_columns:
            try:
                w = self.data_tree.column(col, "width")
                self._col_widths[(self._open_table_name, col)] = w
            except Exception:
                pass

    def _autofit_column(self, event):
        col_id = self.data_tree.identify_column(event.x)
        if not col_id or col_id == "#0":
            return
        col_idx = int(col_id[1:]) - 1
        if col_idx < 0 or col_idx >= len(self._table_data_columns):
            return
        col_name = self._table_data_columns[col_idx]
        try:
            f = tkfont.nametofont("TkDefaultFont")
        except Exception:
            f = tkfont.Font()
        header = self.data_tree.heading(col_name, "text")
        candidates = [header] + [
            str(self.data_tree.set(iid, col_name))
            for iid in self.data_tree.get_children()
        ]
        max_w = max(f.measure(v) for v in candidates) + 24
        max_w = max(max_w, 40)
        self.data_tree.column(col_name, width=max_w)
        self._col_widths[(self._open_table_name, col_name)] = max_w
        self._update_col_separators()

    def _on_cell_double_click(self, event):
        region = self.data_tree.identify_region(event.x, event.y)
        if region == "separator":
            self._autofit_column(event)
            return
        if region == "heading":
            return

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
        auto_fill = {}
        for col in self._table_data_columns:
            d = self._table_col_defaults.get(col, {})
            col_default = d.get("default") or ""
            if d.get("is_identity", False):
                auto_fill[col] = None           # IDENTITY — exclude from INSERT, hide field
            elif col_default:
                # Let PostgreSQL evaluate its own (possibly normalized) DEFAULT expression
                val = self.active_connector.evaluate_expression(col_default)
                if val:
                    auto_fill[col] = val
        AddEditDataWindow(self, self.active_connector, self._open_table_name,
                          self._open_table_is_collection, self._table_data_columns,
                          mode="add", auto_fill=auto_fill)

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

    def _open_query_wizard(self):
        if self._query_window and self._query_window.winfo_exists():
            self._query_window.lift()
            self._query_window.focus_force()
            return
        self._query_window = QueryWindow(self)


if __name__ == "__main__":
    app = DBManagerApp()
    app.mainloop()