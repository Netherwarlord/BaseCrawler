import customtkinter as ctk
import tkinter as tk
from tkinter import ttk
from tkinter import font as tkfont
import threading
import queue

from CTkMessagebox import CTkMessagebox

from Modules.ConnectionManager import ConnectionManager
from Modules.ConnectionWizard import ManageConnectionsWindow
from Modules.RowWizard import AddEditDataWindow
from Modules.TableWizard import AddTableDialog, EditTableDialog
from Modules.ColumnWizard import AddColumnDialog, EditColumnDialog, DeleteColumnDialog
from Core.dbConnector import get_connector


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
            if any(kw in query.upper() for kw in ["CREATE", "ALTER", "DROP", "RENAME", "TRUNCATE"]):
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

        self.title("BaseCrawler v0.8.3-alpha")
        self.geometry("1000x700")

        self.connection_manager = ConnectionManager()
        self.active_connector = None
        self.selected_connection_details = None

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
        self._gridlines_on = True
        self._cell_editor = None
        self._col_sep_frames = []
        self._auto_refresh_id = None
        self._col_widths = {}

        self._fetch_queue = queue.Queue()
        self._fetch_event = threading.Event()
        self._fetch_stop_event = threading.Event()
        self._fetch_thread = None
        self._fetch_poll_id = None
        self._cached_pk_set = {}
        self._cached_col_defaults = {}
        self._selected_col_name = None

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)

        # ── Left pane ─────────────────────────────────────────────────────────
        self.connection_frame = ctk.CTkFrame(self, width=200, corner_radius=0)
        self.connection_frame.grid(row=0, column=0, sticky="nsew")
        self.connection_frame.grid_rowconfigure(1, weight=1)

        ctk.CTkLabel(self.connection_frame, text="Connections",
                     font=ctk.CTkFont(size=15, weight="bold")).grid(row=0, column=0, padx=20, pady=20)

        self.connection_buttons_frame = ctk.CTkScrollableFrame(self.connection_frame, label_text="")
        self.connection_buttons_frame.grid(row=1, column=0, padx=10, pady=10, sticky="nsew")
        self.connection_buttons_frame.grid_columnconfigure(0, weight=1)

        ctk.CTkButton(self.connection_frame, text="Manage Connections",
                      command=self._open_manage_connections_window).grid(
            row=2, column=0, padx=20, pady=10, sticky="s")

        # ── Right pane ────────────────────────────────────────────────────────
        self.workspace_frame = ctk.CTkFrame(self, corner_radius=0)
        self.workspace_frame.grid(row=0, column=1, sticky="nsew", padx=5, pady=5)
        self.workspace_frame.grid_rowconfigure(0, weight=0)
        self.workspace_frame.grid_rowconfigure(1, weight=1)
        self.workspace_frame.grid_columnconfigure(0, weight=1)

        # Top bar
        self._sidebar_visible = True
        self._edit_mode = True
        topbar = ctk.CTkFrame(self.workspace_frame, height=36, fg_color="transparent")
        topbar.grid(row=0, column=0, sticky="ew", padx=4, pady=(4, 0))
        topbar.grid_columnconfigure(1, weight=1)

        self._sidebar_btn = ctk.CTkButton(topbar, text="◀ Hide Panel", width=110, height=28,
                                          command=self._toggle_sidebar)
        self._sidebar_btn.grid(row=0, column=0, padx=(0, 8))

        self._grid_cb = ctk.CTkCheckBox(topbar, text="⊞", width=50, command=self._toggle_gridlines)
        self._grid_cb.select()
        self._grid_cb.grid(row=0, column=2, padx=(0, 4))

        self._edit_mode_cb = ctk.CTkCheckBox(topbar, text="✏", width=50, command=self._apply_edit_mode)
        self._edit_mode_cb.select()
        self._edit_mode_cb.grid(row=0, column=3, padx=(0, 8))

        # Connection info frame
        self.connection_info_frame = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.connection_info_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.connection_info_frame.grid_columnconfigure(0, weight=1)
        self.connection_info_frame.grid_rowconfigure(0, weight=1)

        self.connection_details_display_frame = ctk.CTkFrame(self.connection_info_frame, fg_color="transparent")
        self.connection_details_display_frame.grid(row=0, column=0, sticky="nsew")
        self.connection_details_display_frame.grid_columnconfigure(0, weight=1)
        self.connection_details_display_frame.grid_rowconfigure(0, weight=1)

        ctk.CTkLabel(self.connection_details_display_frame,
                     text="Select a connection from the left panel or manage connections.",
                     font=ctk.CTkFont(size=16)).grid(row=0, column=0, padx=20, pady=20)

        # Workspace panel
        self.workspace_panel = ctk.CTkFrame(self.workspace_frame, fg_color="transparent")
        self.workspace_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.workspace_panel.grid_remove()

        self.schema_tab = self.workspace_panel
        self.schema_tab.grid_rowconfigure(1, weight=1)
        self.schema_tab.grid_columnconfigure(0, weight=1)

        # Schema ribbon
        self.schema_toolbar = ctk.CTkFrame(self.schema_tab, height=72, corner_radius=0)
        self.schema_toolbar.grid(row=0, column=0, sticky="ew", padx=0, pady=(0, 0))
        self.schema_toolbar.pack_propagate(False)

        [self._btn_open_table] = self._ribbon_group(
            self.schema_toolbar, "View", [("▶", "Open", self._open_selected_table)])
        self._ribbon_sep(self.schema_toolbar)
        self._btn_edit_table, self._btn_add_table, self._btn_del_table = self._ribbon_group(
            self.schema_toolbar, "Tables", [
                ("✎", "Edit",   self._edit_selected_table),
                ("⊕", "Add",    self._add_table),
                ("⊗", "Delete", self._delete_selected_table),
            ])
        self._ribbon_sep(self.schema_toolbar)
        self._ribbon_group(self.schema_toolbar, "Query", [("🔍", "SQL", self._open_query_wizard)])
        self._ribbon_sep(self.schema_toolbar)
        [disc_btn] = self._ribbon_group(
            self.schema_toolbar, "Connection", [("⏻", "Disconnect", self._disconnect_db)])
        disc_btn.configure(text_color="#DD4444")

        # Table ribbon
        self.table_toolbar = ctk.CTkFrame(self.schema_tab, height=72, corner_radius=0)
        self.table_toolbar.pack_propagate(False)

        self._ribbon_group(self.table_toolbar, "Navigate", [("◀", "Back", self._show_schema_view)])
        self._ribbon_sep(self.table_toolbar)
        self._btn_add_row, self._btn_edit_row, self._btn_del_row = self._ribbon_group(
            self.table_toolbar, "Rows", [
                ("⊕", "Add",    self._add_row_inline),
                ("✎", "Edit",   self._edit_row_inline),
                ("⊗", "Delete", self._delete_row_inline),
            ])
        self._ribbon_sep(self.table_toolbar)
        self._btn_add_col, self._btn_edit_col, self._btn_del_col = self._ribbon_group(
            self.table_toolbar, "Columns", [
                ("⊕", "Add",    self._add_column),
                ("✎", "Edit",   self._edit_column),
                ("⊗", "Delete", self._delete_column),
            ])
        self._ribbon_sep(self.table_toolbar)
        self._ribbon_group(self.table_toolbar, "Query", [("🔍", "SQL", self._open_query_wizard)])

        # Content area
        self.schema_content = tk.Frame(self.schema_tab, bg="")
        self.schema_content.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        self.schema_content.grid_rowconfigure(0, weight=1)
        self.schema_content.grid_columnconfigure(0, weight=1)

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
        self.data_tree.bind("<Button-1>",        self._on_tree_button_down)
        self.data_tree.bind("<Double-Button-1>", self._on_cell_double_click)
        self.data_tree.bind("<ButtonRelease-1>", self._on_tree_mouse_release)

        self._query_window = None

        self._load_connection_buttons()

    # ── Manage connections ────────────────────────────────────────────────────

    def _open_manage_connections_window(self):
        win = ManageConnectionsWindow(self, self.connection_manager)
        win.focus()
        win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connection_buttons(), win.destroy()))

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
                    self._btn_add_col, self._btn_edit_col, self._btn_del_col]:
            btn.configure(state=state)

    # ── Ribbon helpers ────────────────────────────────────────────────────────

    def _ribbon_group(self, ribbon, title, buttons):
        gf = ctk.CTkFrame(ribbon, fg_color="transparent")
        gf.pack(side="left", fill="y")

        ctk.CTkLabel(gf, text=title, font=ctk.CTkFont(size=9),
                     text_color=("gray45", "gray55")).pack(side="bottom", pady=(0, 3))
        ctk.CTkFrame(gf, height=1, fg_color=("gray75", "gray40")).pack(
            side="bottom", fill="x", padx=6, pady=(0, 1))

        btn_row = ctk.CTkFrame(gf, fg_color="transparent")
        btn_row.pack(side="top", fill="both", expand=True, padx=4, pady=(5, 2))

        created = []
        for col, (icon, lbl, cmd) in enumerate(buttons):
            item = ctk.CTkFrame(btn_row, fg_color="transparent")
            item.grid(row=0, column=col, padx=2)
            btn = ctk.CTkButton(item, text=icon, width=48, height=38,
                                font=ctk.CTkFont(size=19), fg_color="transparent",
                                hover_color=("gray78", "gray28"), text_color=("gray10", "gray90"),
                                corner_radius=6, command=cmd)
            btn.pack()
            ctk.CTkLabel(item, text=lbl, font=ctk.CTkFont(size=9),
                         text_color=("gray35", "gray65")).pack(pady=(1, 0))
            created.append(btn)
        return created

    def _ribbon_sep(self, ribbon):
        sep = tk.Frame(ribbon, width=1,
                       bg="#666" if ctk.get_appearance_mode() == "Dark" else "#bbb")
        sep.pack(side="left", fill="y", pady=8, padx=3)
        sep.pack_propagate(False)

    def _load_connection_buttons(self):
        for widget in self.connection_buttons_frame.winfo_children():
            widget.destroy()
        for i, conn in enumerate(self.connection_manager.get_connections()):
            btn = ctk.CTkButton(self.connection_buttons_frame,
                                text=conn.get("name", "Unnamed Connection"),
                                command=lambda c=conn: self._select_connection(c))
            btn.grid(row=i, column=0, padx=5, pady=5, sticky="ew")

    # ── Connection lifecycle ──────────────────────────────────────────────────

    def _select_connection(self, connection_details):
        conn_name = connection_details.get("name")

        self._stop_auto_refresh()
        if self.active_connector and self.selected_connection_details:
            current_name = self.selected_connection_details.get("name")
            self.connection_manager.save_state(current_name, {
                "open_table":    self._open_table_name,
                "is_collection": self._open_table_is_collection,
                "db_type":       self.selected_connection_details.get("db_type"),
            })
            self.active_connector.disconnect(silent=True)
            self.active_connector = None

        self.selected_connection_details = connection_details
        self.last_connection_status = None

        saved = self.connection_manager.load_state(conn_name)
        if saved:
            try:
                connector = get_connector(connection_details)
                if connector.connect(silent=True):
                    self.active_connector = connector
                    self._is_mongodb = (connection_details.get("db_type") == "MongoDB")

                    self.connection_info_frame.grid_remove()
                    self.workspace_panel.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)

                    self._show_schema_view()
                    if saved.get("open_table"):
                        self._open_table_inline(saved["open_table"], saved.get("is_collection", False))

                    self._start_status_poller()
                    self._start_auto_refresh()
                    return
            except Exception:
                self.active_connector = None

        self.workspace_panel.grid_remove()
        self.connection_info_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        for widget in self.connection_details_display_frame.winfo_children():
            widget.destroy()
        self._display_selected_connection_info_labels(connection_details)
        if self.status_label:
            self.status_label.configure(text="Checking...", text_color=self.default_status_color)
        self._start_status_poller()

    def _disconnect_db(self):
        self._stop_auto_refresh()
        if self.active_connector:
            self.active_connector.disconnect(silent=True)
            self.active_connector = None
        if self.selected_connection_details:
            conn_name = self.selected_connection_details.get("name")
            self.connection_manager.save_state(conn_name, {})
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
            CTkMessagebox(title="Warning", message="No connection selected to connect.",
                          icon="warning", option_1="Ok")
            return

        self._stop_status_poller()

        connection_details = dict(self.selected_connection_details)
        if self._user_entry and self._user_entry.winfo_exists():
            connection_details["user"] = self._user_entry.get().strip()
        if self._pw_entry and self._pw_entry.winfo_exists():
            connection_details["password"] = self._pw_entry.get()

        try:
            self.active_connector = get_connector(connection_details)
            if self.active_connector.connect():
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
                              message=f"Could not connect to '{connection_details['name']}'.\n"
                                      "Check your credentials and try again.",
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
        parent.grid_rowconfigure(2, weight=1)

        name = connection_details.get("name", "Unknown")
        ctk.CTkLabel(parent, text=name, font=ctk.CTkFont(size=22, weight="bold"),
                     anchor="w").grid(row=0, column=0, columnspan=2, padx=16, pady=(16, 8), sticky="w")

        card = ctk.CTkFrame(parent, corner_radius=12)
        card.grid(row=1, column=0, padx=(16, 8), pady=4, sticky="nsew")
        card.grid_columnconfigure(1, weight=1)

        fields = [
            ("Type",   connection_details.get("db_type", "—")),
            ("Host",   connection_details.get("host", "—")),
            ("Port",   connection_details.get("port", "—")),
            ("DB",     connection_details.get("database", "—")),
            ("Status", "Checking…"),
            ("Size",   "—"),
        ]
        for i, (label, value) in enumerate(fields):
            ctk.CTkLabel(card, text=f"{label}:", anchor="e",
                         text_color=("gray40", "gray60")).grid(
                row=i, column=0, padx=(12, 4), pady=3, sticky="e")
            lbl = ctk.CTkLabel(card, text=str(value), anchor="w")
            lbl.grid(row=i, column=1, padx=(0, 12), pady=3, sticky="w")
            if label == "Status":
                self.status_label = lbl
                self.default_status_color = lbl.cget("text_color")

        cred = ctk.CTkFrame(parent, fg_color="transparent")
        cred.grid(row=1, column=1, padx=(8, 16), pady=4, sticky="n")
        cred.grid_columnconfigure(0, weight=1)
        cred.grid_columnconfigure(1, weight=0)

        saved_user = connection_details.get("user", "")
        saved_pw   = connection_details.get("password", "")
        has_saved_pw = bool(saved_pw)

        ctk.CTkLabel(cred, text="Username", anchor="w").grid(row=0, column=0, columnspan=2, sticky="w")
        self._user_entry = ctk.CTkEntry(cred, placeholder_text="username")
        self._user_entry.grid(row=1, column=0, columnspan=2, pady=(0, 8), sticky="ew")
        if saved_user:
            self._user_entry.insert(0, saved_user)

        ctk.CTkLabel(cred, text="Password", anchor="w").grid(row=2, column=0, columnspan=2, sticky="w")
        self._pw_entry = ctk.CTkEntry(cred, show="•", placeholder_text="password")
        self._pw_entry.grid(row=3, column=0, columnspan=2, pady=(0, 4), sticky="ew")
        if saved_pw:
            self._pw_entry.insert(0, saved_pw)

        self._save_pw_var = ctk.BooleanVar(value=has_saved_pw)
        ctk.CTkCheckBox(cred, text="Save password", variable=self._save_pw_var).grid(
            row=4, column=0, sticky="w")

        self.connect_button = ctk.CTkButton(cred, text="Connect", width=120,
                                            command=self._connect_selected_db)
        self.connect_button.grid(row=4, column=1, padx=(10, 0), sticky="e")

        self._user_entry.bind("<Return>", lambda _: self._connect_selected_db())
        self._pw_entry.bind("<Return>",   lambda _: self._connect_selected_db())

    # ── Status poller ─────────────────────────────────────────────────────────

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

        self._status_thread = threading.Thread(
            target=poller_worker, args=(self._status_stop_event,), daemon=True)
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
                    color = {"Online": "green", "Offline": "red"}.get(status, "orange")
                    self.status_label.configure(text=status, text_color=color)
        except queue.Empty:
            pass
        if not self._status_stop_event.is_set():
            self.status_check_id = self.after(500, self._poll_status_queue)

    # ── Background fetch worker ───────────────────────────────────────────────

    def _start_auto_refresh(self):
        self._stop_auto_refresh()
        self._fetch_stop_event = threading.Event()
        self._fetch_event = threading.Event()
        self._fetch_thread = threading.Thread(target=self._fetch_worker_loop, daemon=True)
        self._fetch_thread.start()
        self._fetch_event.set()
        self._poll_fetch_queue()

    def _stop_auto_refresh(self):
        self._fetch_stop_event.set()
        self._fetch_event.set()
        self._fetch_thread = None
        if self._fetch_poll_id is not None:
            self.after_cancel(self._fetch_poll_id)
            self._fetch_poll_id = None

    def _fetch_worker_loop(self):
        stop    = self._fetch_stop_event
        trigger = self._fetch_event
        while not stop.is_set():
            trigger.wait(timeout=1.0)
            trigger.clear()
            if stop.is_set():
                break
            connector = self.active_connector
            table     = self._open_table_name
            if not connector:
                continue
            try:
                if table:
                    success, result = connector.fetch_data(table)
                    new_cols = result.get("columns", []) if (success and result) else []
                    if new_cols != self._table_data_columns:
                        pk_cols, _ = connector.fetch_primary_keys(table)
                        col_defaults = connector.fetch_column_defaults(table)
                    else:
                        pk_cols = None
                        col_defaults = None
                    self._fetch_queue.put(("table", table, success, result, pk_cols, col_defaults))
                else:
                    schema = connector.fetch_schema()
                    self._fetch_queue.put(("schema", schema))
            except Exception:
                pass

    def _trigger_fetch(self):
        self._fetch_event.set()

    def _poll_fetch_queue(self):
        try:
            while True:
                item = self._fetch_queue.get_nowait()
                kind = item[0]
                if kind == "table":
                    _, table, success, result, pk_cols, col_defaults = item
                    if table == self._open_table_name:
                        self._apply_table_data(success, result, pk_cols, col_defaults)
                elif kind == "schema":
                    _, schema = item
                    if not self._open_table_name and schema and self.selected_connection_details:
                        self._display_schema(schema, self.selected_connection_details["db_type"])
        except queue.Empty:
            pass
        if self.active_connector and not self._fetch_stop_event.is_set():
            self._fetch_poll_id = self.after(50, self._poll_fetch_queue)

    # ── Schema display ────────────────────────────────────────────────────────

    def _refresh_schema(self, silent=False):
        if not self.active_connector:
            if not silent:
                CTkMessagebox(title="Warning", message="Not connected to any database.",
                              icon="warning", option_1="Ok")
            return
        self._trigger_fetch()

    def _display_schema(self, schema, db_type):
        self._is_mongodb = (db_type == "MongoDB")
        self._last_schema = schema

        old_selection = self.schema_list_tree.selection()
        old_focus     = self.schema_list_tree.focus()
        self.schema_list_tree.delete(*self.schema_list_tree.get_children())

        if self._is_mongodb:
            for name in schema.get("collections", {}):
                self.schema_list_tree.insert("", "end", iid=name, text=name)
            for btn in (self._btn_edit_table, self._btn_add_table, self._btn_del_table,
                        self._btn_add_col, self._btn_del_col):
                btn.configure(state="disabled")
        else:
            for name in schema.get("tables", {}):
                self.schema_list_tree.insert("", "end", iid=name, text=name)
            for btn in (self._btn_edit_table, self._btn_add_table, self._btn_del_table,
                        self._btn_add_col, self._btn_del_col):
                btn.configure(state="normal")

        for iid in old_selection:
            if self.schema_list_tree.exists(iid):
                self.schema_list_tree.selection_add(iid)
        if old_focus and self.schema_list_tree.exists(old_focus):
            self.schema_list_tree.focus(old_focus)

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
        self._table_data_columns = []
        self._selected_col_name = None
        self.schema_toolbar.grid_remove()
        self.schema_list_frame.grid_remove()
        self.table_toolbar.grid(row=0, column=0, sticky="ew", padx=5, pady=(5, 0))
        self.table_data_frame.grid(row=0, column=0, sticky="nsew")
        self.update_idletasks()
        self._trigger_fetch()

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

    # ── Inline table data ─────────────────────────────────────────────────────

    def _refresh_inline_table(self):
        if self._cell_editor and self._cell_editor.winfo_exists():
            self._cell_editor.destroy()
            self._cell_editor = None
        self._trigger_fetch()

    def _apply_table_data(self, success, result, pk_cols, col_defaults):
        if not self._open_table_name:
            return
        if not success:
            return

        new_cols = result.get("columns", []) if result else []
        new_rows = result.get("rows", []) if result else []

        cols_changed = new_cols != self._table_data_columns
        if cols_changed:
            self._table_data_columns = new_cols

        if pk_cols is not None:
            pk_set = set(pk_cols)
            self._cached_pk_set[self._open_table_name] = pk_set
        else:
            pk_set = self._cached_pk_set.get(self._open_table_name, set())

        if col_defaults is not None:
            self._table_col_defaults = col_defaults
            self._cached_col_defaults[self._open_table_name] = col_defaults
        elif self._open_table_name in self._cached_col_defaults:
            self._table_col_defaults = self._cached_col_defaults[self._open_table_name]

        if cols_changed:
            self.data_tree.configure(columns=new_cols if new_cols else [], show="headings")
            for col in new_cols:
                label = self._col_heading_text(col, pk_set)
                self.data_tree.heading(col, text=label)
                saved_w = self._col_widths.get((self._open_table_name, col), 120)
                self.data_tree.column(col, width=saved_w, minwidth=40)

        sel = self.data_tree.selection()
        old_values = self.data_tree.item(sel[0], "values") if sel else None

        self.data_tree.delete(*self.data_tree.get_children())
        self._table_data_rows = new_rows
        restore_iid = None
        for row in new_rows:
            iid = self.data_tree.insert("", "end", values=row)
            if old_values and self.data_tree.item(iid, "values") == old_values:
                restore_iid = iid
        if restore_iid:
            self.data_tree.selection_set(restore_iid)
            self.data_tree.focus(restore_iid)
        self._apply_row_colors()
        self._update_col_separators()

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

    def _col_heading_text(self, col, pk_set=None):
        if pk_set is None:
            pk_set = self._cached_pk_set.get(self._open_table_name, set())
        pk_mark  = "🔑 " if col in pk_set else ""
        sel_mark = "▾ " if col == self._selected_col_name else ""
        return f"{sel_mark}{pk_mark}{col}"

    def _on_tree_button_down(self, event):
        if self.data_tree.identify_region(event.x, event.y) == "heading":
            col_id = self.data_tree.identify_column(event.x)
            if col_id and col_id != "#0":
                col_idx = int(col_id[1:]) - 1
                if 0 <= col_idx < len(self._table_data_columns):
                    self._select_column(self._table_data_columns[col_idx])

    def _select_column(self, col_name):
        self._selected_col_name = col_name
        pk_set = self._cached_pk_set.get(self._open_table_name, set())
        for col in self._table_data_columns:
            try:
                self.data_tree.heading(col, text=self._col_heading_text(col, pk_set))
            except Exception:
                pass

    def _on_tree_mouse_release(self, _event):
        self.after(60, lambda: (self._save_col_widths(), self._update_col_separators()))

    def _save_col_widths(self):
        if not self._open_table_name or not self._table_data_columns:
            return
        for col in self._table_data_columns:
            try:
                self._col_widths[(self._open_table_name, col)] = self.data_tree.column(col, "width")
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
        candidates = [header] + [str(self.data_tree.set(iid, col_name))
                                  for iid in self.data_tree.get_children()]
        max_w = max(max(f.measure(v) for v in candidates) + 24, 40)
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

        if self._cell_editor and self._cell_editor.winfo_exists():
            self._cell_editor.destroy()
            self._cell_editor = None

        bbox = self.data_tree.bbox(item, col)
        if not bbox:
            return
        bx, by, bw, bh = bbox

        values  = self.data_tree.item(item)["values"]
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
            return

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
            CTkMessagebox(title="Error", message=f"Failed to update cell: {msg}",
                          icon="cancel", option_1="Ok")

    def _get_selected_data_row(self):
        item = self.data_tree.focus()
        if not item:
            return None, None
        values = self.data_tree.item(item)["values"]
        return values, dict(zip(self._table_data_columns, values))

    def _add_row_inline(self):
        if not self._table_data_columns:
            CTkMessagebox(title="Warning", message="No columns found. Refresh the table first.",
                          icon="warning", option_1="Ok")
            return
        auto_fill = {}
        for col in self._table_data_columns:
            d = self._table_col_defaults.get(col, {})
            col_default = d.get("default") or ""
            if d.get("is_identity", False):
                auto_fill[col] = None
            elif col_default:
                val = self.active_connector.evaluate_expression(col_default)
                if val:
                    auto_fill[col] = val
        AddEditDataWindow(self, self.active_connector, self._open_table_name,
                          self._open_table_is_collection, self._table_data_columns,
                          mode="add", auto_fill=auto_fill)

    def _edit_row_inline(self):
        values, row_data = self._get_selected_data_row()
        if values is None:
            CTkMessagebox(title="Warning", message="No row selected to edit.",
                          icon="warning", option_1="Ok")
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
            CTkMessagebox(title="Warning", message="No row selected to delete.",
                          icon="warning", option_1="Ok")
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
                CTkMessagebox(title="Error", message=f"Delete failed: {message}",
                              icon="cancel", option_1="Ok")

    # ── DDL operations ────────────────────────────────────────────────────────

    def _add_table(self):
        if self.active_connector:
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
        msg = CTkMessagebox(title="Confirm",
                            message=f"Drop table '{item}'? This cannot be undone.",
                            icon="question", option_1="No", option_2="Yes")
        if msg.get() == "Yes":
            success, result = self.active_connector.execute_query(f'DROP TABLE "{item}";')
            if success:
                self._refresh_schema()
            else:
                CTkMessagebox(title="Error", message=f"Failed to drop table: {result}",
                              icon="cancel", option_1="Ok")

    def _add_column(self):
        if self._open_table_name and self.active_connector:
            AddColumnDialog(self, self.active_connector, self._open_table_name)

    def _edit_column(self):
        if not self._open_table_name or not self._table_data_columns:
            return
        column_details = (self._last_schema or {}).get("tables", {}).get(
            self._open_table_name, {}).get("columns", [])
        pk_list, pk_constraint_name = self.active_connector.fetch_primary_keys(self._open_table_name)
        unique_map = self.active_connector.fetch_unique_columns(self._open_table_name)
        EditColumnDialog(
            self, self.active_connector, self._open_table_name,
            self._table_data_columns, column_details,
            col_defaults=self._table_col_defaults,
            pk_set=set(pk_list),
            pk_constraint_name=pk_constraint_name,
            unique_map=unique_map,
            default_column=self._selected_col_name,
        )

    def _delete_column(self):
        if self._open_table_name and self._table_data_columns:
            DeleteColumnDialog(self, self.active_connector, self._open_table_name,
                               self._table_data_columns)

    def _open_query_wizard(self):
        if self._query_window and self._query_window.winfo_exists():
            self._query_window.lift()
            self._query_window.focus_force()
            return
        self._query_window = QueryWindow(self)


def main():
    app = DBManagerApp()
    app.mainloop()
