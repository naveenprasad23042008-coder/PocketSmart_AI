import tkinter as tk
from tkinter import ttk, messagebox, filedialog
import sqlite3
import csv
from datetime import datetime

# =========================================================
# DATABASE SETUP & MIGRATION
# =========================================================

DB_NAME = "pocketsmart_v2.db"

conn = sqlite3.connect(DB_NAME)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS income (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    note TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS expenses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    category TEXT NOT NULL,
    amount REAL NOT NULL,
    date TEXT NOT NULL,
    note TEXT DEFAULT ''
)
""")

cursor.execute("""
CREATE TABLE IF NOT EXISTS settings (
    key TEXT PRIMARY KEY,
    value TEXT NOT NULL
)
""")

cursor.execute("INSERT OR IGNORE INTO settings (key, value) VALUES ('monthly_budget_goal', '25000')")
conn.commit()

selected_period = "This month"


# =========================================================
# COLOR PALETTE & STYLES
# =========================================================

BG = "#F8FAFC"             # Slate 50
CARD = "#FFFFFF"           # White
PRIMARY = "#4F46E5"        # Indigo 600
PRIMARY_HOVER = "#3730A3"  # Indigo 800
PRIMARY_LIGHT = "#EEF2FF"  # Indigo 50
ACCENT_VIOLET = "#7C3AED"  # Violet 600
TEXT_MAIN = "#0F172A"      # Slate 900
TEXT_MUTED = "#64748B"     # Slate 500
GREEN = "#059669"          # Emerald 600
GREEN_BG = "#ECFDF5"       # Emerald 50
RED = "#E11D48"            # Rose 600
RED_BG = "#FFF1F2"         # Rose 50
AMBER = "#D97706"          # Amber 600
AMBER_BG = "#FFFBEB"       # Amber 50
BORDER = "#E2E8F0"         # Slate 200

CATEGORY_COLORS = [
    "#6366F1", "#8B5CF6", "#EC4899", "#F43F5E",
    "#F59E0B", "#10B981", "#06B6D4", "#3B82F6"
]

money_animation_state = {}
progress_animation_state = {"value": 0, "generation": 0}

# Global UI Widget Handles
income_value = expense_value = balance_value = None
progress = None
balance_status = None
spending_percentage_label = None
recommendation_text = None
health_score_label = None
health_status_badge = None
budget_goal_label = None


# =========================================================
# HELPER FUNCTIONS
# =========================================================

def money(value):
    return f"₹{value:,.2f}"


def selected_date_range():
    if selected_period == "All time":
        return None

    today = datetime.now().date()
    month = today.month
    year = today.year
    if selected_period == "Last month":
        month -= 1
        if month == 0:
            month = 12
            year -= 1

    start = datetime(year, month, 1).date()
    if month == 12:
        end = datetime(year + 1, 1, 1).date()
    else:
        end = datetime(year, month + 1, 1).date()
    return start.isoformat(), end.isoformat()


def date_filter_sql(column):
    date_range = selected_date_range()
    if date_range is None:
        return "", ()
    return f" WHERE {column} >= ? AND {column} < ?", date_range


def add_card_hover(widget):
    widget.bind("<Enter>", lambda e: widget.configure(highlightbackground="#C7D2FE"), add="+")
    widget.bind("<Leave>", lambda e: widget.configure(highlightbackground=BORDER), add="+")


def create_button(parent, text, command, bg, width=16, height=38):
    btn_frame = tk.Frame(parent, bg=bg, highlightthickness=0)
    btn = tk.Button(
        btn_frame,
        text=text,
        command=command,
        bg=bg,
        fg="white",
        activebackground=PRIMARY_HOVER,
        activeforeground="white",
        font=("Segoe UI", 9, "bold"),
        relief="flat",
        bd=0,
        cursor="hand2",
        padx=12
    )
    btn.pack(fill="both", expand=True)
    return btn_frame


# =========================================================
# DATABASE OPERATIONS
# =========================================================

def get_setting(key, default_value):
    cursor.execute("SELECT value FROM settings WHERE key = ?", (key,))
    res = cursor.fetchone()
    return res[0] if res else default_value


def set_setting(key, value):
    cursor.execute("INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT(key) DO UPDATE SET value = excluded.value", (key, str(value)))
    conn.commit()


def get_monthly_budget_goal():
    try:
        return float(get_setting("monthly_budget_goal", "25000"))
    except ValueError:
        return 25000.0


def add_income():
    try:
        amount = float(income_entry.get())
        note = income_note_entry.get().strip()
        if amount <= 0:
            raise ValueError

        date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO income (amount, date, note) VALUES (?, ?, ?)", (amount, date, note))
        conn.commit()

        income_entry.delete(0, tk.END)
        income_note_entry.delete(0, tk.END)
        messagebox.showinfo("Success", "Income transaction added successfully!")
        update_dashboard()
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid positive income amount.")


def add_expense():
    try:
        category = category_combo.get()
        amount = float(expense_entry.get())
        note = expense_note_entry.get().strip()

        if not category:
            messagebox.showerror("Missing Category", "Please select an expense category.")
            return

        if amount <= 0:
            raise ValueError

        date = datetime.now().strftime("%Y-%m-%d")
        cursor.execute("INSERT INTO expenses (category, amount, date, note) VALUES (?, ?, ?, ?)", (category, amount, date, note))
        conn.commit()

        expense_entry.delete(0, tk.END)
        expense_note_entry.delete(0, tk.END)
        messagebox.showinfo("Success", "Expense transaction added successfully!")
        update_dashboard()
    except ValueError:
        messagebox.showerror("Invalid Input", "Please enter a valid positive expense amount.")


def get_total_income():
    where, params = date_filter_sql("date")
    cursor.execute(f"SELECT SUM(amount) FROM income{where}", params)
    res = cursor.fetchone()[0]
    return res if res else 0.0


def get_total_expenses():
    where, params = date_filter_sql("date")
    cursor.execute(f"SELECT SUM(amount) FROM expenses{where}", params)
    res = cursor.fetchone()[0]
    return res if res else 0.0


def get_category_expenses():
    where, params = date_filter_sql("date")
    cursor.execute(
        f"SELECT category, SUM(amount) FROM expenses{where} GROUP BY category ORDER BY SUM(amount) DESC",
        params
    )
    return cursor.fetchall()


def get_transactions(search="", kind_filter="All", cat_filter="All"):
    date_range = selected_date_range()
    params = []
    where_inc = []
    where_exp = []

    if date_range:
        where_inc.append("date >= ? AND date < ?")
        where_exp.append("date >= ? AND date < ?")
        params.extend([date_range[0], date_range[1]])

    if search:
        s_term = f"%{search}%"
        where_inc.append("(note LIKE ? OR amount LIKE ?)")
        where_exp.append("(note LIKE ? OR category LIKE ? OR amount LIKE ?)")

    inc_clause = (" WHERE " + " AND ".join(where_inc)) if where_inc else ""
    exp_clause = (" WHERE " + " AND ".join(where_exp)) if where_exp else ""

    query = f"""
    SELECT id, date, 'Income' AS kind, 'Income' AS category, amount, note FROM income {inc_clause}
    UNION ALL
    SELECT id, date, 'Expense' AS kind, category, amount, note FROM expenses {exp_clause}
    ORDER BY date DESC, id DESC
    """

    p_inc = []
    p_exp = []
    if date_range:
        p_inc.extend([date_range[0], date_range[1]])
        p_exp.extend([date_range[0], date_range[1]])
    if search:
        s_term = f"%{search}%"
        p_inc.extend([s_term, s_term])
        p_exp.extend([s_term, s_term, s_term])

    cursor.execute(query, p_inc + p_exp)
    rows = cursor.fetchall()

    # Filter in memory for UI dropdowns
    filtered = []
    for r in rows:
        r_id, r_date, r_kind, r_cat, r_amt, r_note = r
        if kind_filter != "All" and r_kind != kind_filter:
            continue
        if cat_filter != "All" and r_cat != cat_filter and r_kind == "Expense":
            continue
        filtered.append(r)
    return filtered


# =========================================================
# FINANCIAL HEALTH SCORE & AI ENGINE
# =========================================================

def calculate_health_score(income, expenses, budget_goal):
    if income == 0:
        return 50, "Neutral", AMBER, AMBER_BG

    savings_rate = max(0, (income - expenses) / income) * 100
    budget_usage = (expenses / budget_goal * 100) if budget_goal > 0 else 50

    score = 50  # Base score
    score += min(30, savings_rate * 0.75)  # Max +30 for savings rate

    if budget_usage <= 70:
        score += 20
    elif budget_usage <= 90:
        score += 10
    elif budget_usage > 100:
        score -= 25

    score = max(0, min(100, int(score)))

    if score >= 80:
        return score, "Excellent", GREEN, GREEN_BG
    elif score >= 60:
        return score, "Healthy", PRIMARY, PRIMARY_LIGHT
    elif score >= 40:
        return score, "Moderate", AMBER, AMBER_BG
    else:
        return score, "Critical", RED, RED_BG


def generate_recommendation():
    income = get_total_income()
    expenses = get_total_expenses()
    budget_goal = get_monthly_budget_goal()

    if income == 0 and expenses == 0:
        return "👋 Welcome to PocketSmart!\nAdd your first income or expense transaction to unlock real-time financial intelligence."

    balance = income - expenses
    savings_ratio = ((income - expenses) / income * 100) if income > 0 else 0
    categories = get_category_expenses()

    insights = []
    if balance < 0:
        insights.append("⚠️ Deficit Warning: Expenses exceed income. Prioritize cutting non-essential spending.")
    elif savings_ratio >= 30:
        insights.append("🎉 Prime Savings: You are saving >30% of income! Consider moving surplus into long-term investments.")
    elif savings_ratio >= 15:
        insights.append("👍 Stable Cash Flow: Healthy positive balance. Keep aiming for a 20% minimum savings target.")

    if expenses > budget_goal and budget_goal > 0:
        over_by = expenses - budget_goal
        insights.append(f"🔴 Budget Exceeded: You are {money(over_by)} over your set monthly cap.")

    if categories:
        top_cat, top_amt = categories[0]
        cat_ratio = (top_amt / income * 100) if income > 0 else 0
        insights.append(f"📌 Top Outflow: '{top_cat}' accounts for {cat_ratio:.1f}% of total revenue.")

    return "\n\n".join(insights)


# =========================================================
# DASHBOARD RENDERING & ANIMATIONS
# =========================================================

def animate_money(label, target):
    state = money_animation_state.setdefault(label, {"value": 0, "gen": 0})
    state["gen"] += 1
    gen = state["gen"]
    start = state["value"]
    frames = 10

    def step(f=1):
        if not label.winfo_exists() or gen != state["gen"]:
            return
        ratio = f / frames
        eased = 1 - (1 - ratio) ** 3
        val = start + (target - start) * eased
        label.config(text=money(val))
        if f < frames:
            label.after(20, lambda: step(f + 1))
        else:
            state["value"] = target
            label.config(text=money(target))
    step()


def update_dashboard():
    income = get_total_income()
    expenses = get_total_expenses()
    balance = income - expenses
    goal = get_monthly_budget_goal()

    if income_value: animate_money(income_value, income)
    if expense_value: animate_money(expense_value, expenses)
    if balance_value: animate_money(balance_value, balance)

    if balance_status and balance_value:
        if balance >= 0:
            balance_value.config(fg=GREEN)
            balance_status.config(text="● Surplus Flow", fg=GREEN)
        else:
            balance_value.config(fg=RED)
            balance_status.config(text="● Deficit Flow", fg=RED)

    # Budget Progress
    percentage = (expenses / income * 100) if income > 0 else 0
    percentage = min(percentage, 100)
    if progress:
        progress["value"] = percentage

    if spending_percentage_label:
        spending_percentage_label.config(text=f"{selected_period} · {percentage:.1f}% of Income Utilized")

    if budget_goal_label:
        used = min(expenses, goal) if goal > 0 else 0
        budget_goal_label.config(text=f"Cap Target: {money(goal)}  |  Used: {money(expenses)}")

    # Health Score
    score, status, score_col, score_bg = calculate_health_score(income, expenses, goal)
    if health_score_label:
        health_score_label.config(text=f"{score}/100", fg=score_col)
    if health_status_badge:
        health_status_badge.config(text=f" {status} ", fg=score_col, bg=score_bg)

    # AI Insights
    if recommendation_text:
        recommendation_text.config(state="normal")
        recommendation_text.delete("1.0", tk.END)
        recommendation_text.insert(tk.END, generate_recommendation())
        recommendation_text.config(state="disabled")

    render_donut_chart()


# =========================================================
# CANVAS DONUT CHART
# =========================================================

def render_donut_chart():
    chart_canvas.delete("all")
    data = get_category_expenses()

    w = chart_canvas.winfo_width() or 340
    h = chart_canvas.winfo_height() or 220
    cx, cy = 110, h // 2
    r_outer, r_inner = 75, 48

    if not data:
        chart_canvas.create_oval(cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer, fill="#F1F5F9", outline=BORDER)
        chart_canvas.create_oval(cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner, fill=CARD, outline=BORDER)
        chart_canvas.create_text(cx, cy, text="No Data", fill=TEXT_MUTED, font=("Segoe UI", 9, "bold"))
        chart_canvas.create_text(w - 90, h // 2, text="Add expenses to view breakdown", fill=TEXT_MUTED, font=("Segoe UI", 9), width=120)
        return

    total = sum(amt for _, amt in data) or 1
    start_angle = 90

    # Draw Donut Slices
    for idx, (cat, amt) in enumerate(data):
        extent = (amt / total) * 360
        color = CATEGORY_COLORS[idx % len(CATEGORY_COLORS)]

        chart_canvas.create_arc(
            cx - r_outer, cy - r_outer, cx + r_outer, cy + r_outer,
            start=start_angle, extent=-extent, fill=color, outline=CARD, width=2
        )
        start_angle -= extent

    # Inner Circle Hole
    chart_canvas.create_oval(cx - r_inner, cy - r_inner, cx + r_inner, cy + r_inner, fill=CARD, outline="")
    chart_canvas.create_text(cx, cy - 8, text="Total Spent", fill=TEXT_MUTED, font=("Segoe UI", 8))
    chart_canvas.create_text(cx, cy + 8, text=f"₹{int(total):,}", fill=TEXT_MAIN, font=("Segoe UI", 10, "bold"))

    # Render Legend
    leg_x = 210
    leg_y = 20
    for idx, (cat, amt) in enumerate(data[:5]):  # Show top 5
        color = CATEGORY_COLORS[idx % len(CATEGORY_COLORS)]
        pct = (amt / total) * 100

        chart_canvas.create_rectangle(leg_x, leg_y + 3, leg_x + 10, leg_y + 13, fill=color, outline="")
        chart_canvas.create_text(leg_x + 16, leg_y + 8, anchor="w", text=f"{cat[:11]}", fill=TEXT_MAIN, font=("Segoe UI", 9))
        chart_canvas.create_text(leg_x + 115, leg_y + 8, anchor="e", text=f"{pct:.0f}%", fill=TEXT_MUTED, font=("Segoe UI", 8, "bold"))
        leg_y += 26


# =========================================================
# BUDGET DIALOG & CLEAR DATA
# =========================================================

def show_budget_dialog():
    dialog = tk.Toplevel(root)
    dialog.title("Monthly Budget Goal")
    dialog.geometry("340x200")
    dialog.transient(root)
    dialog.grab_set()
    dialog.configure(bg=BG)

    tk.Label(dialog, text="Set Monthly Expense Limit", bg=BG, fg=TEXT_MAIN, font=("Segoe UI", 12, "bold")).pack(pady=(20, 6))
    e = tk.Entry(dialog, font=("Segoe UI", 12), justify="center", bg=CARD, relief="solid", bd=1)
    e.insert(0, str(get_monthly_budget_goal()))
    e.pack(fill="x", padx=28, pady=8)

    def save():
        try:
            val = float(e.get())
            if val <= 0: raise ValueError
            set_setting("monthly_budget_goal", val)
            update_dashboard()
            dialog.destroy()
            messagebox.showinfo("Updated", f"Monthly budget limit set to {money(val)}")
        except ValueError:
            messagebox.showerror("Error", "Please enter a valid positive number.")

    act = tk.Frame(dialog, bg=BG)
    act.pack(fill="x", pady=(12, 0), padx=28)
    create_button(act, "Save Target", save, PRIMARY, width=12).pack(side="left")
    create_button(act, "Cancel", dialog.destroy, TEXT_MUTED, width=10).pack(side="right")


def clear_data():
    if messagebox.askyesno("Confirm Clear", "Are you sure you want to delete ALL financial entries?"):
        cursor.execute("DELETE FROM income")
        cursor.execute("DELETE FROM expenses")
        conn.commit()
        update_dashboard()
        messagebox.showinfo("Cleared", "All financial records have been deleted.")


# =========================================================
# ADVANCED TRANSACTION HISTORY WINDOW
# =========================================================

def show_transaction_history():
    win = tk.Toplevel(root)
    win.title("Transaction Records & Search")
    win.geometry("820x520")
    win.minsize(700, 400)
    win.configure(bg=BG)

    filter_frame = tk.Frame(win, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=10)
    filter_frame.pack(fill="x", padx=16, pady=12)

    tk.Label(filter_frame, text="Search:", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
    search_var = tk.StringVar()
    tk.Entry(filter_frame, textvariable=search_var, font=("Segoe UI", 9), width=18, bg=BG, relief="solid", bd=1).pack(side="left", padx=(0, 12))

    tk.Label(filter_frame, text="Type:", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
    kind_var = tk.StringVar(value="All")
    ttk.Combobox(filter_frame, textvariable=kind_var, values=["All", "Income", "Expense"], state="readonly", width=8).pack(side="left", padx=(0, 12))

    tk.Label(filter_frame, text="Category:", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 9, "bold")).pack(side="left", padx=(0, 4))
    cat_var = tk.StringVar(value="All")
    ttk.Combobox(filter_frame, textvariable=cat_var, values=["All", "Food & Dining", "Transportation", "Shopping", "Bills & Utilities", "Entertainment", "Healthcare", "Education", "Other"], state="readonly", width=14).pack(side="left")

    action_frame = tk.Frame(win, bg=BG)
    action_frame.pack(fill="x", padx=16, pady=(0, 8))

    def refresh_table():
        rows = get_transactions(search_var.get(), kind_var.get(), cat_var.get())
        for item in tree.get_children():
            tree.delete(item)
        for row in rows:
            r_id, r_date, r_kind, r_cat, r_amt, r_note = row
            tree.insert("", tk.END, values=(r_id, r_date, r_kind, r_cat, money(r_amt), r_note or "-"))

    def export_csv():
        rows = get_transactions(search_var.get(), kind_var.get(), cat_var.get())
        if not rows:
            messagebox.showinfo("Export", "No transaction records found to export.")
            return
        path = filedialog.asksaveasfilename(defaultextension=".csv", filetypes=[("CSV", "*.csv")])
        if path:
            with open(path, "w", newline="", encoding="utf-8") as f:
                writer = csv.writer(f)
                writer.writerow(["ID", "Date", "Type", "Category", "Amount", "Note"])
                for r in rows:
                    writer.writerow(list(r))
            messagebox.showinfo("Exported", f"Successfully exported to CSV:\n{path}")

    def import_csv():
        path = filedialog.askopenfilename(filetypes=[("CSV Files", "*.csv")])
        if not path:
            return
        try:
            count = 0
            with open(path, "r", encoding="utf-8", newline="") as f:
                reader = csv.DictReader(f)
                if reader.fieldnames is None:
                    raise ValueError("CSV file is empty or missing a header row.")
                fieldnames = [name.strip() for name in reader.fieldnames]
                normalized = {name.lower(): name for name in fieldnames}
                if not {"date", "type", "category", "amount"}.issubset(set(normalized.keys())):
                    raise ValueError("CSV must include date, type, category, and amount columns.")
                for row in reader:
                    date_value = (row.get(normalized.get("date")) or "").strip()
                    kind = (row.get(normalized.get("type")) or "").strip().lower()
                    category = (row.get(normalized.get("category")) or "").strip()
                    amount_value = (row.get(normalized.get("amount")) or "").strip()
                    note = (row.get(normalized.get("note")) or "").strip() if normalized.get("note") else ""
                    if not date_value or not amount_value:
                        continue
                    amount = float(amount_value)
                    if kind == "income":
                        cursor.execute("INSERT INTO income (amount, date, note) VALUES (?, ?, ?)", (amount, date_value, note))
                    elif kind == "expense":
                        if not category:
                            category = "Other"
                        cursor.execute("INSERT INTO expenses (category, amount, date, note) VALUES (?, ?, ?, ?)", (category, amount, date_value, note))
                    else:
                        continue
                    count += 1
            conn.commit()
            update_dashboard()
            refresh_table()
            messagebox.showinfo("Imported", f"Imported {count} transaction(s) successfully.")
        except Exception as exc:
            messagebox.showerror("Import Error", f"Could not import CSV:\n{exc}")

    ttk.Button(action_frame, text="Export CSV", command=export_csv).pack(side="right")
    ttk.Button(action_frame, text="Import CSV", command=import_csv).pack(side="right", padx=(0, 8))

    table_frame = tk.Frame(win, bg=BG)
    table_frame.pack(fill="both", expand=True, padx=16, pady=(0, 16))

    columns = ("ID", "Date", "Type", "Category", "Amount", "Note")
    tree = ttk.Treeview(table_frame, columns=columns, show="headings", height=18)
    for col in columns:
        tree.heading(col, text=col)
        tree.column(col, anchor="center", width=110 if col not in ("Note",) else 180)
    tree.pack(fill="both", expand=True)

    scroll = ttk.Scrollbar(table_frame, orient="vertical", command=tree.yview)
    tree.configure(yscrollcommand=scroll.set)
    scroll.pack(side="right", fill="y")

    search_var.trace_add("write", lambda *args: refresh_table())
    kind_var.trace_add("write", lambda *args: refresh_table())
    cat_var.trace_add("write", lambda *args: refresh_table())
    refresh_table()


def build_ui():
    global root, income_value, expense_value, balance_value, progress, balance_status, spending_percentage_label, recommendation_text, health_score_label, health_status_badge, budget_goal_label, chart_canvas, income_entry, expense_entry, income_note_entry, expense_note_entry, category_combo

    root = tk.Tk()
    root.title("PocketSmart Budget Planner")
    root.geometry("1180x760")
    root.minsize(980, 680)
    root.configure(bg=BG)

    style = ttk.Style(root)
    style.theme_use("clam")
    style.configure("TCombobox", fieldbackground=CARD, background=CARD)
    style.configure("TButton", padding=(10, 7))

    main = tk.Frame(root, bg=BG)
    main.pack(fill="both", expand=True, padx=18, pady=18)
    main.columnconfigure(1, weight=1)
    main.rowconfigure(0, weight=1)

    sidebar = tk.Frame(main, bg=CARD, highlightbackground=BORDER, highlightthickness=1, width=310)
    sidebar.grid(row=0, column=0, sticky="ns", padx=(0, 18), pady=0)

    tk.Label(sidebar, text="PocketSmart", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 22, "bold")).pack(anchor="w", padx=18, pady=(20, 10))
    tk.Label(sidebar, text="Budget intelligence in real time", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 10)).pack(anchor="w", padx=18, pady=(0, 18))

    add_income_frame = tk.Frame(sidebar, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
    add_income_frame.pack(fill="x", padx=18, pady=(0, 14))
    tk.Label(add_income_frame, text="Add income", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
    tk.Label(add_income_frame, text="Amount", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    income_entry = tk.Entry(add_income_frame, font=("Segoe UI", 11), bg=BG, relief="solid", bd=1)
    income_entry.pack(fill="x", pady=(4, 8))
    tk.Label(add_income_frame, text="Note", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    income_note_entry = tk.Entry(add_income_frame, font=("Segoe UI", 10), bg=BG, relief="solid", bd=1)
    income_note_entry.pack(fill="x", pady=(4, 10))
    create_button(add_income_frame, "Add Income", add_income, GREEN, width=18).pack(fill="x")

    add_expense_frame = tk.Frame(sidebar, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
    add_expense_frame.pack(fill="x", padx=18, pady=(0, 18))
    tk.Label(add_expense_frame, text="Add expense", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 11, "bold")).pack(anchor="w", pady=(0, 8))
    tk.Label(add_expense_frame, text="Category", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    category_combo = ttk.Combobox(add_expense_frame, values=["Food & Dining", "Transportation", "Shopping", "Bills & Utilities", "Entertainment", "Healthcare", "Education", "Other"], state="readonly", width=24)
    category_combo.pack(fill="x", pady=(4, 8))
    tk.Label(add_expense_frame, text="Amount", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    expense_entry = tk.Entry(add_expense_frame, font=("Segoe UI", 11), bg=BG, relief="solid", bd=1)
    expense_entry.pack(fill="x", pady=(4, 8))
    tk.Label(add_expense_frame, text="Note", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9)).pack(anchor="w")
    expense_note_entry = tk.Entry(add_expense_frame, font=("Segoe UI", 10), bg=BG, relief="solid", bd=1)
    expense_note_entry.pack(fill="x", pady=(4, 10))
    create_button(add_expense_frame, "Add Expense", add_expense, RED, width=18).pack(fill="x")

    actions_bar = tk.Frame(sidebar, bg=CARD)
    actions_bar.pack(fill="x", padx=18, pady=(0, 18))
    create_button(actions_bar, "Set Budget", show_budget_dialog, PRIMARY, width=12).pack(side="left", expand=True, fill="x", padx=(0, 6))
    create_button(actions_bar, "History", show_transaction_history, ACCENT_VIOLET, width=12).pack(side="left", expand=True, fill="x")
    create_button(sidebar, "Clear All Data", clear_data, TEXT_MUTED, width=18).pack(fill="x", padx=18)

    content = tk.Frame(main, bg=BG)
    content.grid(row=0, column=1, sticky="nsew")

    header = tk.Frame(content, bg=BG)
    header.pack(fill="x", pady=(0, 16))
    tk.Label(header, text="Financial overview", bg=BG, fg=TEXT_MAIN, font=("Segoe UI", 24, "bold")).pack(side="left")

    period_var = tk.StringVar(value=selected_period)
    def on_period_change(*_):
        global selected_period
        selected_period = period_var.get()
        update_dashboard()
    period_options = ttk.Combobox(header, textvariable=period_var, values=["This month", "Last month", "All time"], state="readonly", width=14)
    period_options.pack(side="right")
    period_var.trace_add("write", on_period_change)

    stats = tk.Frame(content, bg=BG)
    stats.pack(fill="x")

    def stat_card(parent, title, value_var, color, label_text):
        card = tk.Frame(parent, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=16, pady=14)
        card.pack(side="left", fill="both", expand=True, padx=(0, 12))
        tk.Label(card, text=title, bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9, "bold")).pack(anchor="w")
        value_label = tk.Label(card, text="₹0.00", bg=CARD, fg=color, font=("Segoe UI", 18, "bold"))
        value_label.pack(anchor="w", pady=(8, 0))
        status_label = tk.Label(card, text=label_text, bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9))
        status_label.pack(anchor="w", pady=(4, 0))
        return value_label, status_label

    income_value, income_status = stat_card(stats, "Income", None, GREEN, "Total inflow")
    expense_value, expense_status = stat_card(stats, "Expense", None, RED, "Total outflow")
    balance_value, balance_status = stat_card(stats, "Balance", None, PRIMARY, "Net cash flow")

    dashboard_grid = tk.Frame(content, bg=BG)
    dashboard_grid.pack(fill="both", expand=True, pady=(18, 0))

    left_panel = tk.Frame(dashboard_grid, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=18, pady=16)
    left_panel.pack(side="left", fill="both", expand=True)

    tk.Label(left_panel, text="Spending health", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(0, 6))
    progress = ttk.Progressbar(left_panel, orient="horizontal", length=330, mode="determinate", maximum=100)
    progress.pack(fill="x", pady=(8, 8))
    spending_percentage_label = tk.Label(left_panel, text="This month · 0.0% of Income Utilized", bg=CARD, fg=TEXT_MUTED, font=("Segoe UI", 9, "bold"))
    spending_percentage_label.pack(anchor="w")

    budget_goal_label = tk.Label(left_panel, text="Cap Target: ₹0.00 | Used: ₹0.00", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 10, "bold"))
    budget_goal_label.pack(anchor="w", pady=(12, 10))

    score_row = tk.Frame(left_panel, bg=CARD)
    score_row.pack(fill="x", pady=(4, 8))
    health_score_label = tk.Label(score_row, text="0/100", bg=CARD, fg=PRIMARY, font=("Segoe UI", 24, "bold"))
    health_score_label.pack(side="left")
    health_status_badge = tk.Label(score_row, text=" Neutral ", bg=AMBER_BG, fg=AMBER, font=("Segoe UI", 9, "bold"), padx=10, pady=4)
    health_status_badge.pack(side="left", padx=(12, 0))

    recommendation_text = tk.Text(left_panel, height=9, width=42, bg=BG, fg=TEXT_MAIN, font=("Segoe UI", 9), wrap="word", relief="flat")
    recommendation_text.pack(fill="both", expand=True, pady=(12, 0))
    recommendation_text.configure(state="disabled")

    right_panel = tk.Frame(dashboard_grid, bg=CARD, highlightbackground=BORDER, highlightthickness=1, padx=14, pady=12)
    right_panel.pack(side="right", fill="y", padx=(12, 0))

    tk.Label(right_panel, text="Expense breakdown", bg=CARD, fg=TEXT_MAIN, font=("Segoe UI", 14, "bold")).pack(anchor="w", pady=(6, 8))
    chart_canvas = tk.Canvas(right_panel, width=360, height=230, bg=CARD, highlightthickness=0)
    chart_canvas.pack(fill="both", expand=True)

    update_dashboard()
    root.mainloop()


if __name__ == "__main__":
    build_ui()
