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
    def __init__(self, master, connection_manager):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title("New Connection")
        self.geometry("400x550")
        self.connection_manager = connection_manager

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

        # Database Name
        ctk.CTkLabel(self, text="Database Name:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.database_entry = ctk.CTkEntry(self)
        self.database_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        # Save Button
        self.save_button = ctk.CTkButton(self, text="Save Connection", command=self._save_connection)
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
        self.connection_manager.add_connection(connection_details)
        CTkMessagebox(title="Success", message="Connection saved successfully.", icon="check", option_1="Ok")
        self.master._load_connections_list() # Refresh the connections list in ManageConnectionsWindow
        self.master.master._load_connection_buttons() # Refresh the main app's connection list
        self.destroy()


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
        self.control_frame.grid_columnconfigure((0,1,2,3), weight=1)

        ctk.CTkButton(self.control_frame, text="Add New", command=self._add_new_connection).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.control_frame, text="Remove", command=self._remove_selected).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.control_frame, text="Move Up", command=self._move_up).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(self.control_frame, text="Move Down", command=self._move_down).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

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
        # After new connection is saved, refresh this list
        new_conn_win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connections_list(), new_conn_win.destroy()))

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
            self.master._load_data() # Refresh parent window's data
            self.destroy()
        else:
            CTkMessagebox(title="Error", message=f"Failed to save data: {message}", icon="cancel", option_1="Ok")


class DataEditorWindow(ctk.CTkToplevel):
    def __init__(self, master, active_connector, item_name, is_collection):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"Data Editor: {item_name}")
        self.geometry("1200x700")
        self.active_connector = active_connector
        self.item_name = item_name
        self.is_collection = is_collection
        self.data_columns = [] # To store column names for Add/Edit operations
        self.data_rows = [] # To store fetched rows

        self.grid_rowconfigure(1, weight=1)
        self.grid_columnconfigure(0, weight=1)

        # Control buttons
        control_frame = ctk.CTkFrame(self)
        control_frame.grid(row=0, column=0, padx=10, pady=10, sticky="ew")
        control_frame.grid_columnconfigure((0,1,2,3), weight=1)

        ctk.CTkButton(control_frame, text="Refresh", command=self._load_data).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(control_frame, text="Add Row/Document", command=self._add_data).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(control_frame, text="Edit Selected", command=self._edit_data).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(control_frame, text="Delete Selected", command=self._delete_data).grid(row=0, column=3, padx=5, pady=5, sticky="ew")

        # Data display area
        self.data_display_frame = ctk.CTkFrame(self)
        self.data_display_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.data_display_frame.grid_rowconfigure(0, weight=1)
        self.data_display_frame.grid_columnconfigure(0, weight=1)

        self.tree = ttk.Treeview(self.data_display_frame)
        self.tree.grid(row=0, column=0, sticky="nsew")

        # Add scrollbars
        vsb = ttk.Scrollbar(self.data_display_frame, orient="vertical", command=self.tree.yview)
        vsb.grid(row=0, column=1, sticky='ns')
        hsb = ttk.Scrollbar(self.data_display_frame, orient="horizontal", command=self.tree.xview)
        hsb.grid(row=1, column=0, sticky='ew')
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._load_data()

    def _load_data(self):
        # Clear previous data
        for i in self.tree.get_children():
            self.tree.delete(i)
        self.tree["columns"] = []
        self.tree["show"] = "headings"

        success, result = self.active_connector.fetch_data(self.item_name)

        if success:
            if result and result["rows"]:
                self.data_columns = result["columns"]
                self.data_rows = result["rows"]

                self.tree["columns"] = self.data_columns
                for col in self.data_columns:
                    self.tree.heading(col, text=col)
                    self.tree.column(col, width=100) # default width

                for row in self.data_rows:
                    self.tree.insert("", "end", values=row)
            else:
                # handle no data
                self.data_columns = []
                self.data_rows = []
        else:
            # handle error
            self.data_columns = []
            self.data_rows = []

    def _add_data(self):
        if not self.data_columns:
            CTkMessagebox(title="Warning", message="Cannot add data: No schema/columns found. Fetch data first.", icon="warning", option_1="Ok")
            return
        AddEditDataWindow(self, self.active_connector, self.item_name, self.is_collection, self.data_columns, mode="add")

    def _edit_data(self):
        selected_item = self.tree.focus()
        if not selected_item:
            CTkMessagebox(title="Warning", message="No row selected to edit.", icon="warning", option_1="Ok")
            return

        selected_row_values = self.tree.item(selected_item)['values']
        selected_row_data = dict(zip(self.data_columns, selected_row_values))
        
        # For MongoDB, we need the ObjectId, not the string representation
        if self.is_collection and '_id' in selected_row_data:
            # Find the original document to get the ObjectId
            for row in self.data_rows:
                if str(row[self.data_columns.index('_id')]) == selected_row_data['_id']:
                    selected_row_data['_id'] = row[self.data_columns.index('_id')]
                    break
        
        AddEditDataWindow(self, self.active_connector, self.item_name, self.is_collection, self.data_columns, initial_data=selected_row_data, mode="edit")

    def _delete_data(self):
        selected_item = self.tree.focus()
        if not selected_item:
            CTkMessagebox(title="Warning", message="No row selected to delete.", icon="warning", option_1="Ok")
            return

        selected_row_values = self.tree.item(selected_item)['values']
        
        condition = {}
        if self.is_collection:
            # MongoDB uses _id for unique identification
            _id_index = self.data_columns.index("_id")
            _id_str = selected_row_values[_id_index]
            # Find the original document to get the ObjectId
            for row in self.data_rows:
                if str(row[_id_index]) == _id_str:
                    condition["_id"] = row[_id_index]
                    break
        else:
            # For SQL, assume the first column is the primary key for deletion condition
            pk_col = self.data_columns[0]
            pk_val = selected_row_values[0]
            condition[pk_col] = pk_val

        msg = CTkMessagebox(title="Confirm Delete", message=f"Are you sure you want to delete the selected row from {self.item_name}?",
                            icon="question", option_1="No", option_2="Yes")
        if msg.get() == "Yes":
            success, message = self.active_connector.delete_data(self.item_name, condition)
            if success:
                CTkMessagebox(title="Success", message=message, icon="check", option_1="Ok")
                self._load_data() # Refresh data after deletion
            else:
                CTkMessagebox(title="Error", message=f"Failed to delete data: {message}", icon="cancel", option_1="Ok")


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

        self.schema_controls_frame = ctk.CTkFrame(self.schema_tab)
        self.schema_controls_frame.grid(row=0, column=0, sticky="ew", padx=5, pady=0)
        self.schema_controls_frame.grid_columnconfigure(0, weight=1)

        self.refresh_schema_button = ctk.CTkButton(self.schema_controls_frame, text="Refresh Schema", command=self._refresh_schema)
        self.refresh_schema_button.grid(row=0, column=0, padx=5, pady=5, sticky="ew")

        self.schema_display_frame = ctk.CTkScrollableFrame(self.schema_tab, label_text="Database Schema")
        self.schema_display_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.schema_display_frame.grid_columnconfigure(0, weight=1)
        ctk.CTkLabel(self.schema_display_frame, text="Connect to a database to view its schema.").grid(row=0, column=0, padx=5, pady=5)

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
        self._schedule_status_check()

        # Show connect button
        self.connect_button.grid(row=100, column=0, padx=20, pady=20, sticky="s")

    def _connect_selected_db(self):
        if not self.selected_connection_details:
            CTkMessagebox(title="Warning", message="No connection selected to connect.", icon="warning", option_1="Ok")
            return
        
        # Cancel status check loop
        if self.status_check_id:
            self.after_cancel(self.status_check_id)
            self.status_check_id = None
        
        connection_details = self.selected_connection_details

        # Clear schema display
        for widget in self.schema_display_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.schema_display_frame, text=f"Connecting to {connection_details['name']}...").grid(row=0, column=0, padx=5, pady=5)

        try:
            self.active_connector = get_connector(connection_details)
            if self.active_connector.connect():
                # Hide connection info, show workspace tabview
                self.connection_info_frame.grid_remove()
                self.workspace_tabview.grid(row=0, column=0, sticky="nsew", padx=5, pady=5) # Ensure workspace_tabview is gridded
                self.workspace_tabview.set("Schema") # Switch to schema tab
                
                # Clear previous status message
                for widget in self.schema_display_frame.winfo_children():
                    widget.destroy()
                ctk.CTkLabel(self.schema_display_frame, text=f"Successfully connected to {connection_details['name']}!\n\nFetching schema...\n").grid(row=0, column=0, padx=5, pady=5)
                
                schema = self.active_connector.fetch_schema()
                if schema:
                    self._display_schema(schema, connection_details["db_type"])
                else:
                    ctk.CTkLabel(self.schema_display_frame, text="Failed to fetch schema.").grid(row=1, column=0, padx=5, pady=5)

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

    def _schedule_status_check(self):
        if self.status_check_id:
            self.after_cancel(self.status_check_id)

        def check_worker():
            if self.selected_connection_details:
                try:
                    connector = get_connector(self.selected_connection_details)
                    if connector.connect(silent=True):
                        self.status_queue.put("Online")
                        connector.disconnect(silent=True)
                    else:
                        self.status_queue.put("Offline")
                except Exception:
                    self.status_queue.put("Error")
        
        threading.Thread(target=check_worker, daemon=True).start()
        self._process_status_queue()

    def _process_status_queue(self):
        try:
            status = self.status_queue.get_nowait()
            if status != self.last_connection_status:
                self.last_connection_status = status
                if self.status_label:
                    if status == "Online":
                        self.status_label.configure(text="Online", text_color="green")
                    elif status == "Offline":
                        self.status_label.configure(text="Offline", text_color="red")
                    else: # Error
                        self.status_label.configure(text="Error", text_color="orange")
            
            self.status_check_id = self.after(1000, self._schedule_status_check)

        except queue.Empty:
            self.status_check_id = self.after(100, self._process_status_queue)

    def _refresh_schema(self):
        if not self.active_connector:
            CTkMessagebox(title="Warning", message="Not connected to any database.", icon="warning", option_1="Ok")
            return

        if not self.selected_connection_details:
            CTkMessagebox(title="Warning", message="No connection details found.", icon="warning", option_1="Ok")
            return

        # Clear schema display
        for widget in self.schema_display_frame.winfo_children():
            widget.destroy()
        ctk.CTkLabel(self.schema_display_frame, text="Refreshing schema...").grid(row=0, column=0, padx=5, pady=5)

        schema = self.active_connector.fetch_schema()
        if schema:
            self._display_schema(schema, self.selected_connection_details["db_type"])
        else:
            for widget in self.schema_display_frame.winfo_children():
                widget.destroy()
            ctk.CTkLabel(self.schema_display_frame, text="Failed to fetch schema.").grid(row=0, column=0, padx=5, pady=5)

    def _display_schema(self, schema, db_type):
        for widget in self.schema_display_frame.winfo_children():
            widget.destroy()
        
        row_idx = 0
        if db_type == "MongoDB":
            ctk.CTkLabel(self.schema_display_frame, text="Collections:", font=ctk.CTkFont(weight="bold")).grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
            row_idx += 1
            for collection_name in schema.get("collections", {}):
                btn = ctk.CTkButton(self.schema_display_frame, text=collection_name, 
                                    command=lambda name=collection_name: self._open_data_editor_window(name, is_collection=True))
                btn.grid(row=row_idx, column=0, sticky="ew", padx=10, pady=2)
                row_idx += 1
        else: # SQL databases
            ctk.CTkLabel(self.schema_display_frame, text="Tables:", font=ctk.CTkFont(weight="bold")).grid(row=row_idx, column=0, sticky="w", padx=5, pady=2)
            row_idx += 1
            for table_name in schema.get("tables", {}):
                btn = ctk.CTkButton(self.schema_display_frame, text=table_name, 
                                    command=lambda name=table_name: self._open_data_editor_window(name, is_collection=False))
                btn.grid(row=row_idx, column=0, sticky="ew", padx=10, pady=2)
                row_idx += 1

    def _open_data_editor_window(self, item_name, is_collection):
        if self.active_connector:
            DataEditorWindow(self, self.active_connector, item_name, is_collection)
        else:
            CTkMessagebox(title="Error", message="No active connection to open data editor.", icon="cancel", option_1="Ok")

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