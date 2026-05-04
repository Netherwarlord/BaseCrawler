import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from .shared import COLUMN_TYPES, _SCHEMA_TYPE_MAP, _rand_default_sql, _parse_rand_max


class EditColumnDialog(ctk.CTkToplevel):
    def __init__(self, master, active_connector, table_name, columns, column_details,
                 col_defaults=None, pk_set=None, pk_constraint_name=None,
                 unique_map=None, default_column=None):
        super().__init__(master)
        self.lift()
        self.focus_force()
        self.grab_set()
        self.title(f"Edit Column — {table_name}")
        self.geometry("420x295")
        self.active_connector = active_connector
        self.table_name = table_name
        self._type_map = {c["name"]: c["type"] for c in column_details}
        self._col_defaults = col_defaults or {}
        self._pk_set = pk_set or set()
        self._pk_constraint_name = pk_constraint_name
        self._unique_map = unique_map or {}

        self.grid_columnconfigure(1, weight=1)

        ctk.CTkLabel(self, text="Column:").grid(row=0, column=0, padx=10, pady=10, sticky="w")
        initial = default_column if default_column in columns else (columns[0] if columns else "")
        self.col_var = ctk.StringVar(value=initial)
        ctk.CTkOptionMenu(self, values=columns, variable=self.col_var,
                          command=self._on_col_select).grid(
            row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkLabel(self, text="New Name:").grid(row=1, column=0, padx=10, pady=5, sticky="w")
        self.name_entry = ctk.CTkEntry(self)
        self.name_entry.grid(row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkLabel(self, text="Type:").grid(row=2, column=0, padx=10, pady=5, sticky="w")
        self.type_var = ctk.StringVar()
        self.type_menu = ctk.CTkOptionMenu(self, values=COLUMN_TYPES, variable=self.type_var)
        self.type_menu.grid(row=2, column=1, padx=10, pady=5, sticky="ew")

        toggles = ctk.CTkFrame(self, fg_color="transparent")
        toggles.grid(row=3, column=0, columnspan=2, padx=10, pady=(4, 2), sticky="ew")

        self.pk_var     = ctk.BooleanVar()
        self.auto_var   = ctk.BooleanVar()
        self.rand_var   = ctk.BooleanVar()
        self.unique_var = ctk.BooleanVar()

        self._len_label = ctk.CTkLabel(toggles, text="Length:")
        self._len_entry = ctk.CTkEntry(toggles, width=55, placeholder_text="6")

        def _on_rand_toggle():
            if self.rand_var.get():
                self._len_label.grid(row=0, column=3, padx=(8, 2))
                self._len_entry.grid(row=0, column=4, padx=(0, 8))
            else:
                self._len_label.grid_remove()
                self._len_entry.grid_remove()

        self._on_rand_toggle = _on_rand_toggle

        ctk.CTkCheckBox(toggles, text="PK",     variable=self.pk_var,     width=55).grid(row=0, column=0, padx=(0, 4))
        ctk.CTkCheckBox(toggles, text="Auto",   variable=self.auto_var,   width=65).grid(row=0, column=1, padx=(0, 4))
        ctk.CTkCheckBox(toggles, text="Rand",   variable=self.rand_var,   width=65,
                        command=_on_rand_toggle).grid(row=0, column=2)
        ctk.CTkCheckBox(toggles, text="Unique", variable=self.unique_var, width=75).grid(row=0, column=5, padx=(10, 0))

        ctk.CTkButton(self, text="Apply", command=self._apply).grid(
            row=4, column=0, columnspan=2, padx=10, pady=14, sticky="ew")

        self._on_col_select(self.col_var.get())

    def _on_col_select(self, col_name):
        self.name_entry.delete(0, "end")
        self.name_entry.insert(0, col_name)

        raw_type = self._type_map.get(col_name, "")
        mapped = _SCHEMA_TYPE_MAP.get(raw_type.lower(), raw_type.upper()) if raw_type else COLUMN_TYPES[0]
        self.type_var.set(mapped if mapped in COLUMN_TYPES else COLUMN_TYPES[0])

        d = self._col_defaults.get(col_name, {})
        col_default  = d.get("default") or ""
        is_identity  = d.get("is_identity", False)
        is_rand      = "random()" in col_default.lower()
        is_auto      = is_identity or ("CURRENT_TIMESTAMP" in col_default.upper()) or is_rand
        rand_max     = _parse_rand_max(col_default, raw_type) if is_rand else ""

        self.pk_var.set(col_name in self._pk_set)
        self.auto_var.set(is_auto)
        self.rand_var.set(is_rand)
        self.unique_var.set(col_name in self._unique_map)

        self._len_entry.delete(0, "end")
        if rand_max:
            self._len_entry.insert(0, rand_max)
        self._on_rand_toggle()

    def _apply(self):
        col_name  = self.col_var.get()
        new_name  = self.name_entry.get().strip()
        new_type  = self.type_var.get()

        if not new_name:
            CTkMessagebox(title="Error", message="Column name cannot be empty.", icon="cancel", option_1="Ok")
            return

        errors = []
        effective_name = col_name
        backfill = None

        # Rename
        if new_name != col_name:
            q = f'ALTER TABLE "{self.table_name}" RENAME COLUMN "{col_name}" TO "{new_name}";'
            ok, msg = self.active_connector.execute_query(q)
            if ok:
                effective_name = new_name
            else:
                errors.append(f"Rename failed: {msg}")

        # Type change
        if not errors:
            raw_type = self._type_map.get(col_name, "")
            orig_mapped = _SCHEMA_TYPE_MAP.get(raw_type.lower(), raw_type.upper()) if raw_type else ""
            if new_type != orig_mapped:
                q = f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" TYPE {new_type};'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Type change failed: {msg}")

        # Default
        if not errors:
            if self.rand_var.get():
                expr = _rand_default_sql(new_type, self._len_entry.get().strip())
                q = f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" SET DEFAULT {expr};'
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Set random default failed: {msg}")
                else:
                    backfill = (effective_name, new_type, expr)
            elif self.auto_var.get():
                if new_type == "INTEGER":
                    default_expr = "0"
                elif new_type in ("TIMESTAMP", "DATE"):
                    default_expr = "CURRENT_TIMESTAMP"
                else:
                    default_expr = None
                if default_expr:
                    q = (f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" '
                         f'SET DEFAULT {default_expr};')
                    ok, msg = self.active_connector.execute_query(q)
                    if not ok:
                        errors.append(f"Set auto default failed: {msg}")
            else:
                d = self._col_defaults.get(col_name, {})
                old_default = d.get("default") or ""
                if old_default and not d.get("is_identity", False):
                    q = f'ALTER TABLE "{self.table_name}" ALTER COLUMN "{effective_name}" DROP DEFAULT;'
                    ok, msg = self.active_connector.execute_query(q)
                    if not ok:
                        errors.append(f"Drop default failed: {msg}")

        # Unique
        if not errors:
            was_unique  = col_name in self._unique_map
            new_unique  = self.unique_var.get()
            if new_unique and not was_unique:
                safe = effective_name.replace('"', '').replace(' ', '_').lower()
                q = (f'ALTER TABLE "{self.table_name}" ADD CONSTRAINT '
                     f'"{self.table_name}_{safe}_unique" UNIQUE ("{effective_name}");')
                ok, msg = self.active_connector.execute_query(q)
                if not ok:
                    errors.append(f"Add UNIQUE failed: {msg}")
            elif not new_unique and was_unique:
                constraint = self._unique_map.get(col_name)
                if constraint:
                    q = f'ALTER TABLE "{self.table_name}" DROP CONSTRAINT "{constraint}";'
                    ok, msg = self.active_connector.execute_query(q)
                    if not ok:
                        errors.append(f"Drop UNIQUE failed: {msg}")

        # PK
        if not errors:
            was_pk  = col_name in self._pk_set
            new_pk  = self.pk_var.get()
            if new_pk != was_pk:
                if self._pk_constraint_name:
                    q = f'ALTER TABLE "{self.table_name}" DROP CONSTRAINT "{self._pk_constraint_name}";'
                    ok, msg = self.active_connector.execute_query(q)
                    if not ok:
                        errors.append(f"Drop PRIMARY KEY failed: {msg}")
                if new_pk and not errors:
                    q = f'ALTER TABLE "{self.table_name}" ADD PRIMARY KEY ("{effective_name}");'
                    ok, msg = self.active_connector.execute_query(q)
                    if not ok:
                        errors.append(f"Set PRIMARY KEY failed: {msg}")

        if errors:
            CTkMessagebox(title="Error", message="\n".join(errors), icon="cancel", option_1="Ok")
            return

        if backfill:
            eff_name, _, rand_expr = backfill
            ans = CTkMessagebox(
                title="Update existing rows?",
                message=(f"Random default set for '{eff_name}'.\n\n"
                         "Overwrite ALL existing values in this column with new random values?\n\n"
                         "This cannot be undone."),
                icon="question", option_1="Yes, Update All", option_2="Cancel")
            if ans.get() == "Yes, Update All":
                q = f'UPDATE "{self.table_name}" SET "{eff_name}" = {rand_expr};'
                ok, err_msg = self.active_connector.execute_query(q)
                if not ok:
                    CTkMessagebox(title="Backfill failed",
                                  message=f"Could not update '{eff_name}': {err_msg}",
                                  icon="cancel", option_1="Ok")

        self.destroy()
        self.master._refresh_inline_table()
        self.master._refresh_schema()


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
        ctk.CTkOptionMenu(self, values=COLUMN_TYPES, variable=self.type_var).grid(
            row=1, column=1, padx=10, pady=5, sticky="ew")

        ctk.CTkButton(self, text="Add Column", command=self._add_column).grid(
            row=2, column=0, columnspan=2, padx=10, pady=16, sticky="ew")

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
        ctk.CTkOptionMenu(self, values=columns, variable=self.col_var).grid(
            row=0, column=1, padx=10, pady=10, sticky="ew")

        ctk.CTkButton(self, text="Delete Column", command=self._delete_column).grid(
            row=1, column=0, columnspan=2, padx=10, pady=16, sticky="ew")

    def _delete_column(self):
        col_name = self.col_var.get()
        msg = CTkMessagebox(title="Confirm",
                            message=f"Drop column '{col_name}'? This cannot be undone.",
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
