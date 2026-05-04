import customtkinter as ctk
from CTkMessagebox import CTkMessagebox


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

        ctk.CTkLabel(self, text="Connection Name:").grid(row=0, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=0, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Database Type:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.db_type_var = ctk.StringVar(value="PostgreSQL")
        self.db_type_optionmenu = ctk.CTkOptionMenu(
            self, values=["PostgreSQL", "MongoDB", "MariaDB", "MySQL"],
            variable=self.db_type_var)
        self.db_type_optionmenu.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Host:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.host_entry = ctk.CTkEntry(self)
        self.host_entry.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Port:").grid(row=3, column=0, padx=10, pady=5, sticky="w")
        self.port_entry = ctk.CTkEntry(self)
        self.port_entry.grid(row=3, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="User:").grid(row=4, column=0, padx=10, pady=5, sticky="w")
        self.user_entry = ctk.CTkEntry(self)
        self.user_entry.grid(row=4, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Password:").grid(row=5, column=0, padx=10, pady=5, sticky="w")
        self.password_entry = ctk.CTkEntry(self, show="*")
        self.password_entry.grid(row=5, column=1, padx=10, pady=5, sticky="ew")
        self._pw_visible = False
        self.pw_toggle_btn = ctk.CTkButton(
            self, text="◡", width=28, height=28, corner_radius=6,
            fg_color="transparent", hover_color=("gray75", "gray35"),
            text_color=("gray10", "gray90"), command=self._toggle_password_visibility)
        self.password_entry.bind("<Configure>", self._reposition_pw_toggle)

        ctk.CTkLabel(self, text="Database Name:").grid(row=6, column=0, padx=10, pady=5, sticky="w")
        self.database_entry = ctk.CTkEntry(self)
        self.database_entry.grid(row=6, column=1, padx=10, pady=5, sticky="ew")

        if self._edit_mode:
            self.name_entry.insert(0, existing_connection.get("name", ""))
            self.db_type_var.set(existing_connection.get("db_type", "PostgreSQL"))
            self.host_entry.insert(0, existing_connection.get("host", ""))
            self.port_entry.insert(0, existing_connection.get("port", ""))
            self.user_entry.insert(0, existing_connection.get("user", ""))
            self.password_entry.insert(0, existing_connection.get("password", ""))
            self.database_entry.insert(0, existing_connection.get("database", ""))

        label = "Update Connection" if self._edit_mode else "Save Connection"
        ctk.CTkButton(self, text=label, command=self._save_connection).grid(
            row=7, column=0, columnspan=2, padx=10, pady=20, sticky="ew")

    def _save_connection(self):
        details = {
            "name":     self.name_entry.get(),
            "db_type":  self.db_type_var.get(),
            "host":     self.host_entry.get(),
            "port":     self.port_entry.get(),
            "user":     self.user_entry.get(),
            "password": self.password_entry.get(),
            "database": self.database_entry.get(),
        }
        if self._edit_mode:
            self.connection_manager.update_connection(self.existing_connection["name"], details)
            CTkMessagebox(title="Success", message="Connection updated successfully.", icon="check", option_1="Ok")
        else:
            self.connection_manager.add_connection(details)
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
        self.master = master

        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1)

        self.connections_frame = ctk.CTkScrollableFrame(self, label_text="Saved Connections")
        self.connections_frame.grid(row=0, column=0, padx=10, pady=10, sticky="nsew")
        self.connections_frame.grid_columnconfigure(0, weight=1)

        ctrl = ctk.CTkFrame(self)
        ctrl.grid(row=1, column=0, padx=10, pady=10, sticky="ew")
        ctrl.grid_columnconfigure((0, 1, 2), weight=1)

        ctk.CTkButton(ctrl, text="Add",    command=self._add_new_connection).grid(row=0, column=0, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(ctrl, text="Edit",   command=self._edit_selected).grid(row=0, column=1, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(ctrl, text="Remove", command=self._remove_selected).grid(row=0, column=2, padx=5, pady=5, sticky="ew")
        ctk.CTkButton(ctrl, text="↑", width=40, command=self._move_up).grid(row=0, column=3, padx=(2, 2), pady=5)
        ctk.CTkButton(ctrl, text="↓", width=40, command=self._move_down).grid(row=0, column=4, padx=(2, 5), pady=5)

        self.selected_connection_name = None
        self._load_connections_list()

    def _load_connections_list(self):
        for widget in self.connections_frame.winfo_children():
            widget.destroy()
        for i, conn in enumerate(self.connection_manager.get_connections()):
            name = conn.get("name", "Unnamed Connection")
            btn = ctk.CTkButton(self.connections_frame, text=name,
                                command=lambda n=name: self._select_connection_in_list(n))
            btn.grid(row=i, column=0, padx=5, pady=2, sticky="ew")
            if name == self.selected_connection_name:
                btn.configure(fg_color=btn.cget("hover_color"))

    def _select_connection_in_list(self, name):
        self.selected_connection_name = name
        self._load_connections_list()

    def _add_new_connection(self):
        win = NewConnectionWindow(self, self.connection_manager)
        win.focus()
        win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connections_list(), win.destroy()))

    def _edit_selected(self):
        if not self.selected_connection_name:
            CTkMessagebox(title="Warning", message="No connection selected to edit.", icon="warning", option_1="Ok")
            return
        existing = next((c for c in self.connection_manager.get_connections()
                         if c.get("name") == self.selected_connection_name), None)
        if not existing:
            return
        win = NewConnectionWindow(self, self.connection_manager, existing_connection=existing)
        win.focus()
        win.protocol("WM_DELETE_WINDOW", lambda: (self._load_connections_list(), win.destroy()))

    def _remove_selected(self):
        if not self.selected_connection_name:
            CTkMessagebox(title="Warning", message="No connection selected to remove.", icon="warning", option_1="Ok")
            return
        msg = CTkMessagebox(title="Confirm Removal",
                            message=f"Are you sure you want to remove '{self.selected_connection_name}'?",
                            icon="question", option_1="No", option_2="Yes")
        if msg.get() == "Yes":
            self.connection_manager.remove_connection(self.selected_connection_name)
            self.selected_connection_name = None
            self._load_connections_list()
            self.master._load_connection_buttons()

    def _move_up(self):
        if not self.selected_connection_name:
            CTkMessagebox(title="Warning", message="No connection selected to move.", icon="warning", option_1="Ok")
            return
        self.connection_manager.reorder_connection(self.selected_connection_name, -1)
        self._load_connections_list()
        self.master._load_connection_buttons()

    def _move_down(self):
        if not self.selected_connection_name:
            CTkMessagebox(title="Warning", message="No connection selected to move.", icon="warning", option_1="Ok")
            return
        self.connection_manager.reorder_connection(self.selected_connection_name, 1)
        self._load_connections_list()
        self.master._load_connection_buttons()
