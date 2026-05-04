import customtkinter as ctk
from CTkMessagebox import CTkMessagebox
from .shared import COLUMN_TYPES, _SCHEMA_TYPE_MAP, _rand_default_sql, _parse_rand_max


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

        entry = {
            "name_entry": name_entry, "type_var": type_var,
            "pk_var": pk_var, "pk_cb": pk_cb,
            "auto_var": auto_var, "rand_var": rand_var,
            "max_entry": len_entry, "unique_var": unique_var, "frame": outer,
        }

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

        query = f'CREATE TABLE "{table_name}" ({", ".join(col_defs)});'
        ok, result = self.active_connector.execute_query(query)
        if ok:
            self.destroy()
            self.master._refresh_schema()
        else:
            CTkMessagebox(title="Error", message=f"Failed to create table:\n{result}", icon="cancel", option_1="Ok")


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

    def _add_col_row(self, name="", col_type="", is_pk=False, is_unique=False,
                     is_auto=False, is_rand=False, rand_max=""):
        idx = len(self._col_rows)

        outer = ctk.CTkFrame(self.cols_frame, fg_color="transparent")
        outer.grid(row=idx, column=0, padx=0, pady=(2, 6), sticky="ew")
        outer.grid_columnconfigure(0, weight=1)

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

        if is_rand:
            len_label.grid(row=0, column=3, padx=(8, 2))
            len_entry.grid(row=0, column=4, padx=(0, 8))

        entry = {
            "orig_name": name or None, "orig_type": col_type or None,
            "name_entry": name_entry, "type_var": type_var,
            "pk_var": pk_var, "pk_cb": pk_cb,
            "auto_var": auto_var, "rand_var": rand_var,
            "max_entry": len_entry, "unique_var": unique_var, "frame": outer,
        }

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
        backfill_targets = []

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

        for col_name in dropped:
            q = f'ALTER TABLE "{self.table_name}" DROP COLUMN "{col_name}";'
            ok, msg = self.active_connector.execute_query(q)
            if not ok:
                errors.append(f"Drop '{col_name}': {msg}")

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

        if backfill_targets:
            col_list = "\n".join(f"  • {n} ({t})" for n, t, _ in backfill_targets)
            msg = CTkMessagebox(
                title="Update existing rows?",
                message=(f"Random defaults have been set for:\n{col_list}\n\n"
                         "Do you want to overwrite ALL existing values in these columns "
                         "with newly generated random values?\n\nThis cannot be undone."),
                icon="question", option_1="Yes, Update All", option_2="Cancel")
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
