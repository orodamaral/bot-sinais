import customtkinter as ctk
from tkinter import filedialog, messagebox, ttk

from .storage import load_history, save_history, export_xlsx

ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("green")

EMOJI_MAP = {
    "COMPRA":        "\U0001f7e2",
    "VENDA":         "\U0001f534",
    "TAKE":          "\u2705",
    "STOP LOSS":     "\u274c",
    "VIRADA DE MÃO": "\U0001f504",
}
COR_MAP = {
    "COMPRA":        "#00ff88",
    "VENDA":         "#ff4444",
    "TAKE":          "#4caf50",
    "STOP LOSS":     "#f44336",
    "VIRADA DE MÃO": "#ff9800",
}
COR_HEX_MAP = {
    "COMPRA":        "00ff88",
    "VENDA":         "ff4444",
    "TAKE":          "4caf50",
    "STOP LOSS":     "f44336",
    "VIRADA DE MÃO": "ff9800",
}


class App:
    def __init__(self):
        self.root = ctk.CTk()
        self.root.title("Gold Macro Compass — Monitor")
        self.root.geometry("820x580")
        self.root.minsize(720, 460)

        self._sound_enabled = ctk.BooleanVar(value=True)
        self._history = load_history()

        self._build_ui()
        if self._history:
            self._show_last_signal(self._history[-1])

    def _build_ui(self):
        tabview = ctk.CTkTabview(self.root, corner_radius=12)
        tabview.pack(fill="both", expand=True, padx=10, pady=(10, 4))

        tab_sinal = tabview.add("  Último Sinal  ")
        tab_historico = tabview.add("  Histórico  ")

        self._build_sinal_tab(tab_sinal)
        self._build_historico_tab(tab_historico)
        self._build_statusbar()

    def _build_sinal_tab(self, parent):
        self._sinal_label = ctk.CTkLabel(
            parent, text="---", font=("Segoe UI", 32, "bold"),
            text_color="#c9d1d9"
        )
        self._sinal_label.pack(pady=(40, 4))

        self._detalhes_label = ctk.CTkLabel(
            parent, text="Aguardando primeiro sinal...",
            font=("Consolas", 14), text_color="#8b949e"
        )
        self._detalhes_label.pack(pady=(2, 0))

        sep = ctk.CTkFrame(parent, height=2, corner_radius=0)
        sep.configure(fg_color="#30363d")
        sep.pack(fill="x", padx=60, pady=24)

        info_frame = ctk.CTkFrame(parent, fg_color="transparent")
        info_frame.pack()
        fields = [("Ativo", "ticker"), ("Preço", "price"), ("Horário", "time_str")]
        self._info_labels = {}
        for label, key in fields:
            row = ctk.CTkFrame(info_frame, fg_color="transparent")
            row.pack(pady=4)
            ctk.CTkLabel(row, text=f"{label}:", font=("Segoe UI", 13),
                         text_color="#8b949e", width=80, anchor="e").pack(side="left")
            lbl = ctk.CTkLabel(row, text="-", font=("Segoe UI", 13, "bold"),
                               text_color="#c9d1d9", anchor="w")
            lbl.pack(side="left", padx=(10, 0))
            self._info_labels[key] = lbl

        cb = ctk.CTkCheckBox(
            parent, text="Tocar som ao receber sinal",
            variable=self._sound_enabled,
            font=("Segoe UI", 11), corner_radius=6
        )
        cb.pack(pady=(28, 0))

    def _build_historico_tab(self, parent):
        columns = ("time_str", "action", "ticker", "price")
        tree_frame = ctk.CTkFrame(parent, corner_radius=10)
        tree_frame.pack(fill="both", expand=True, padx=6, pady=(10, 0))

        style = ttk.Style()
        style.theme_use("clam")
        style.configure("CT.Treeview", background="#1a1a2e",
                        foreground="#c9d1d9", fieldbackground="#1a1a2e",
                        borderwidth=0, rowheight=30, font=("Segoe UI", 10))
        style.configure("CT.Treeview.Heading", background="#2d2d44",
                        foreground="#ffffff", borderwidth=0,
                        font=("Segoe UI", 10, "bold"))
        style.map("CT.Treeview.Heading", background=[("active", "#3d3d54")])
        style.map("CT.Treeview", background=[("selected", "#2d4a3e")])
        style.layout("CT.Treeview", [("CT.Treeview.treearea", {"sticky": "nswe"})])

        self._tree = ttk.Treeview(tree_frame, columns=columns, show="headings",
                                  style="CT.Treeview", selectmode="browse")
        self._tree.heading("time_str", text="Data/Hora")
        self._tree.heading("action", text="Sinal")
        self._tree.heading("ticker", text="Ativo")
        self._tree.heading("price", text="Preço")
        self._tree.column("time_str", width=180, anchor="center")
        self._tree.column("action", width=140, anchor="center")
        self._tree.column("ticker", width=100, anchor="center")
        self._tree.column("price", width=100, anchor="center")

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=vsb.set)
        self._tree.pack(side="left", fill="both", expand=True)
        vsb.pack(side="right", fill="y")

        btn_frame = ctk.CTkFrame(parent, fg_color="transparent")
        btn_frame.pack(fill="x", pady=(12, 10))

        ctk.CTkButton(btn_frame, text="Exportar Excel",
                       command=self._export, width=130,
                       corner_radius=8).pack(side="left", padx=(10, 6))
        ctk.CTkButton(btn_frame, text="Limpar Histórico",
                       command=self._clear_history, width=130,
                       corner_radius=8, fg_color="#5c2e2e",
                       hover_color="#7a3d3d").pack(side="left", padx=6)

        self._refresh_history_table()

    def _build_statusbar(self):
        bar = ctk.CTkFrame(self.root, height=32, corner_radius=0)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)
        self._status_label = ctk.CTkLabel(
            bar, text="Pronto", font=("Segoe UI", 10),
            text_color="#8b949e", anchor="w"
        )
        self._status_label.pack(side="left", padx=12)

    def _show_last_signal(self, record: dict):
        action = record.get("action", "---")
        ticker = record.get("ticker", "")
        price = record.get("price", "")
        time_str = record.get("time_str", "")

        emoji = EMOJI_MAP.get(action, "")
        cor = COR_MAP.get(action, "#c9d1d9")
        self._sinal_label.configure(text=f"{emoji}  {action}", text_color=cor)

        self._info_labels["ticker"].configure(text=ticker)
        self._info_labels["price"].configure(text=str(price))
        self._info_labels["time_str"].configure(text=time_str)
        self._detalhes_label.configure(text="")

    def new_signal(self, record: dict):
        self._history.append(record)
        save_history(self._history)
        self._show_last_signal(record)
        self._refresh_history_table()
        self._status_label.configure(
            text=f"Último sinal: {record.get('action', '')} — {record.get('ticker', '')} @ {record.get('price', '')}"
        )

    def _refresh_history_table(self):
        for row in self._tree.get_children():
            self._tree.delete(row)
        for r in self._history:
            self._tree.insert("", "end", values=(
                r.get("time_str", ""),
                r.get("action", ""),
                r.get("ticker", ""),
                r.get("price", ""),
            ))

    def _export(self):
        if not self._history:
            messagebox.showinfo("Exportar", "Nenhum sinal no histórico.")
            return
        path = filedialog.asksaveasfilename(
            defaultextension=".xlsx",
            filetypes=[("Excel files", "*.xlsx")],
            title="Salvar histórico como Excel"
        )
        if path:
            try:
                n = export_xlsx(path)
                messagebox.showinfo("Exportar", f"{n} sinais exportados para:\n{path}")
            except Exception as e:
                messagebox.showerror("Erro", f"Falha ao exportar:\n{e}")

    def _clear_history(self):
        if not self._history:
            return
        if messagebox.askyesno("Limpar", "Limpar todo o histórico?"):
            self._history = []
            save_history([])
            self._refresh_history_table()
            self._status_label.configure(text="Histórico limpo")

    @property
    def sound_enabled(self):
        return self._sound_enabled.get()

    def run(self):
        self.root.mainloop()
