import tkinter as tk
from tkinter import ttk, filedialog, messagebox
from datetime import datetime, timezone, timedelta

from .storage import load_history, save_history, export_xlsx

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


class App:
    def __init__(self):
        self.root = tk.Tk()
        self.root.title("Gold Macro Compass - Monitor")
        self.root.geometry("680x520")
        self.root.minsize(600, 400)

        self._sound_enabled = tk.BooleanVar(value=True)
        self._play_sound_cb = None

        self._build_ui()
        self._history = load_history()
        self._refresh_history_table()
        self.root.after(100, self._on_startup)

    def set_poller_callback(self, fn):
        self._play_sound_cb = fn

    def _on_startup(self):
        if self._history:
            last = self._history[-1]
            self._show_last_signal(last)

    def _build_ui(self):
        self.root.configure(bg="#0d1117")
        style = ttk.Style()
        style.theme_use("clam")
        style.configure("TNotebook", background="#161b22", borderwidth=0)
        style.configure("TNotebook.Tab", background="#0d1117", foreground="#c9d1d9",
                        padding=[12, 4], borderwidth=0)
        style.map("TNotebook.Tab", background=[("selected", "#1f2937")],
                  foreground=[("selected", "#ffffff")])
        style.configure("Treeview", background="#0d1117", foreground="#c9d1d9",
                        fieldbackground="#0d1117", borderwidth=0, rowheight=28)
        style.configure("Treeview.Heading", background="#1f2937", foreground="#ffffff",
                        borderwidth=0)
        style.map("Treeview.Heading", background=[("active", "#2d3748")])
        style.configure("TButton", background="#1f2937", foreground="#ffffff",
                        borderwidth=0, padding=[10, 4])
        style.map("TButton", background=[("active", "#2d3748")])

        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True, padx=6, pady=(6, 0))

        frame_sinal = tk.Frame(notebook, bg="#0d1117")
        frame_historico = tk.Frame(notebook, bg="#0d1117")
        notebook.add(frame_sinal, text="  Último Sinal  ")
        notebook.add(frame_historico, text="  Histórico  ")

        self._build_sinal_tab(frame_sinal)
        self._build_historico_tab(frame_historico)
        self._build_statusbar()

    def _build_sinal_tab(self, parent):
        self._sinal_label = tk.Label(
            parent, text="---", font=("Segoe UI", 28, "bold"),
            bg="#0d1117", fg="#c9d1d9", anchor="center"
        )
        self._sinal_label.pack(pady=(30, 0))

        self._detalhes_label = tk.Label(
            parent, text="Aguardando primeiro sinal...",
            font=("Consolas", 14), bg="#0d1117", fg="#8b949e", anchor="center"
        )
        self._detalhes_label.pack(pady=(10, 0))

        sep = tk.Frame(parent, height=1, bg="#30363d")
        sep.pack(fill="x", padx=40, pady=20)

        info_frame = tk.Frame(parent, bg="#0d1117")
        info_frame.pack()
        fields = [("Ativo", "ticker"), ("Preço", "price"), ("Horário", "time_str")]
        self._info_labels = {}
        for label, key in fields:
            row = tk.Frame(info_frame, bg="#0d1117")
            row.pack(pady=3)
            tk.Label(row, text=f"{label}:", font=("Segoe UI", 11),
                     bg="#0d1117", fg="#8b949e", width=8, anchor="e").pack(side="left")
            lbl = tk.Label(row, text="-", font=("Segoe UI", 11, "bold"),
                           bg="#0d1117", fg="#c9d1d9", anchor="w")
            lbl.pack(side="left", padx=(8, 0))
            self._info_labels[key] = lbl

        sound_frame = tk.Frame(parent, bg="#0d1117")
        sound_frame.pack(pady=(20, 0))
        cb = tk.Checkbutton(
            sound_frame, text="Tocar som ao receber sinal",
            variable=self._sound_enabled, bg="#0d1117", fg="#c9d1d9",
            selectcolor="#0d1117", activebackground="#0d1117",
            activeforeground="#c9d1d9", font=("Segoe UI", 10)
        )
        cb.pack()

    def _build_historico_tab(self, parent):
        columns = ("time_str", "action", "ticker", "price")
        self._tree = ttk.Treeview(parent, columns=columns, show="headings",
                                  selectmode="browse")
        self._tree.heading("time_str", text="Data/Hora")
        self._tree.heading("action", text="Sinal")
        self._tree.heading("ticker", text="Ativo")
        self._tree.heading("price", text="Preço")
        self._tree.column("time_str", width=180, anchor="center")
        self._tree.column("action", width=140, anchor="center")
        self._tree.column("ticker", width=100, anchor="center")
        self._tree.column("price", width=100, anchor="center")

        scroll = ttk.Scrollbar(parent, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=scroll.set)

        self._tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")

        btn_frame = tk.Frame(parent, bg="#0d1117")
        btn_frame.pack(fill="x", pady=6)

        ttk.Button(btn_frame, text="Exportar Excel", command=self._export).pack(side="left", padx=(10, 4))
        ttk.Button(btn_frame, text="Limpar Histórico", command=self._clear_history).pack(side="left", padx=4)

    def _build_statusbar(self):
        bar = tk.Frame(self.root, bg="#161b22", height=28)
        bar.pack(fill="x", side="bottom")
        self._status_label = tk.Label(
            bar, text="Pronto", bg="#161b22", fg="#8b949e",
            font=("Segoe UI", 9), anchor="w"
        )
        self._status_label.pack(side="left", padx=10)

    def _show_last_signal(self, record: dict):
        action = record.get("action", "---")
        ticker = record.get("ticker", "")
        price = record.get("price", "")
        time_str = record.get("time_str", "")

        emoji = EMOJI_MAP.get(action, "")
        cor = COR_MAP.get(action, "#c9d1d9")
        self._sinal_label.config(text=f"{emoji} {action}", fg=cor)

        self._info_labels["ticker"].config(text=ticker)
        self._info_labels["price"].config(text=str(price))
        self._info_labels["time_str"].config(text=time_str)
        self._detalhes_label.config(text="")

    def new_signal(self, record: dict):
        self._history.append(record)
        save_history(self._history)
        self._show_last_signal(record)
        self._refresh_history_table()
        self._status_label.config(
            text=f"Último sinal: {record.get('action', '')} - {record.get('ticker', '')} @ {record.get('price', '')}"
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
            self._status_label.config(text="Histórico limpo")

    @property
    def sound_enabled(self):
        return self._sound_enabled.get()

    def run(self):
        self.root.mainloop()
