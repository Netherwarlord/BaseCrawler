import customtkinter as ctk
from CTkMessagebox import CTkMessagebox


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
        self.entry_widgets = {}

        self.grid_columnconfigure(1, weight=1)

        row = 0
        for col_name in self.columns:
            if col_name == "_id" and self.is_collection and self.mode == "add":
                self.entry_widgets[col_name] = None
                continue
            if col_name == "_id" and self.is_collection and self.mode == "edit":
                ctk.CTkLabel(self, text=f"{col_name}:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
                lbl = ctk.CTkLabel(self, text=str(initial_data.get(col_name, "")))
                lbl.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
                self.entry_widgets[col_name] = lbl
                row += 1
                continue
            if self.mode == "add" and self.auto_fill.get(col_name) is None and col_name in self.auto_fill:
                self.entry_widgets[col_name] = None
                continue

            ctk.CTkLabel(self, text=f"{col_name}:").grid(row=row, column=0, padx=10, pady=5, sticky="w")
            entry = ctk.CTkEntry(self)
            entry.grid(row=row, column=1, padx=10, pady=5, sticky="ew")
            self.entry_widgets[col_name] = entry

            if self.mode == "add" and col_name in self.auto_fill:
                entry.insert(0, str(self.auto_fill[col_name]))
                entry.configure(state="disabled")
            elif self.mode == "edit" and initial_data and col_name != "_id":
                entry.insert(0, str(initial_data.get(col_name, "")))

            row += 1

        self.geometry("500x" + str(80 + row * 50))
        ctk.CTkButton(self, text="Save", command=self._save_data).grid(
            row=row, column=0, columnspan=2, padx=10, pady=16, sticky="ew")

    def _save_data(self):
        data = {}
        for col_name, widget in self.entry_widgets.items():
            if widget is None:
                continue
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
            if not self.is_collection and pk_col in data:
                del data[pk_col]
            if self.is_collection and "_id" in data:
                del data["_id"]
            success, message = self.active_connector.update_data(self.item_name, data, condition)

        if success:
            self.master._refresh_inline_table()
            self.destroy()
        else:
            CTkMessagebox(title="Error", message=f"Failed to save data: {message}", icon="cancel", option_1="Ok")
