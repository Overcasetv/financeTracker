import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from matplotlib.figure import Figure

# --- 1. Database Management ---

class DatabaseManager:
    """Handles all SQLite database operations for the finance tracker."""

    def __init__(self, db_name="finance_data.db"):
        self.conn = sqlite3.connect(db_name)
        self.cursor = self.conn.cursor()
        self.init_db()

    def init_db(self):
        """Creates the transactions table if it doesn't exist."""
        try:
            self.cursor.execute('''
                CREATE TABLE IF NOT EXISTS transactions (
                    id INTEGER PRIMARY KEY,
                    date TEXT NOT NULL,
                    type TEXT NOT NULL, -- 'Income' or 'Expense'
                    category TEXT NOT NULL,
                    amount REAL NOT NULL,
                    description TEXT
                )
            ''')
            self.conn.commit()
        except sqlite3.Error as e:
            print(f"Database initialization error: {e}")

    def add_transaction(self, date, type, category, amount, description):
        """Inserts a new transaction into the database."""
        try:
            self.cursor.execute('''
                INSERT INTO transactions (date, type, category, amount, description)
                VALUES (?, ?, ?, ?, ?)
            ''', (date, type, category, amount, description))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", f"Could not add transaction: {e}")
            return False

    def get_all_transactions(self, start_date=None, end_date=None, trans_type=None, category=None):
        """
        Retrieves all or filtered transactions, ordered by date.
        This single method now handles all filtering logic.
        """
        query = "SELECT id, date, type, category, amount, description FROM transactions WHERE 1=1"
        params = []
        
        if start_date:
            query += " AND date >= ?"
            params.append(start_date)
        if end_date:
            query += " AND date <= ?"
            params.append(end_date)
        if trans_type and trans_type != 'All':
            query += " AND type = ?"
            params.append(trans_type)
        if category and category != 'All':
            query += " AND category = ?"
            params.append(category)

        query += " ORDER BY date, id"
        
        try:
            self.cursor.execute(query, tuple(params))
            return self.cursor.fetchall()
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", f"Could not retrieve transactions: {e}")
            return []


    def delete_transaction(self, transaction_id):
        """Deletes a specific transaction by ID."""
        try:
            self.cursor.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
            self.conn.commit()
            return True
        except sqlite3.Error as e:
            messagebox.showerror("DB Error", f"Could not delete transaction: {e}")
            return False

    def close(self):
        """Closes the database connection."""
        self.conn.close()

# --- 2. Main Application Class ---

class FinanceApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Professional Personal Finance Manager")
        
        try:
            self.tk.call('::tk::mac::setAppName', 'Finance Manager')
        except:
            pass
            
        self.geometry("1200x800")
        self.db = DatabaseManager()

        self.income_categories = ['Salary', 'Freelance', 'Investment', 'Other Income']
        self.expense_categories = ['Rent', 'Groceries', 'Utilities', 'Transportation', 'Entertainment', 'Savings', 'Other Expense']
        
        # Filter variables
        self.filter_start_date = tk.StringVar(value="")
        self.filter_end_date = tk.StringVar(value="")
        self.filter_type = tk.StringVar(value="All")

        # Configure the main grid layout
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(0, weight=1, minsize=350) # Input Panel
        self.grid_columnconfigure(1, weight=3) # Visualization Panel

        # Apply a clean, modern style
        self.style = ttk.Style(self)
        self.style.theme_use('clam')
        self.style.configure('.', font=('Inter', 10))
        self.style.configure('TFrame', background='#f0f4f8', borderwidth=1, relief='flat')
        self.style.configure('TButton', font=('Inter', 10, 'bold'), padding=6, background='#007aff', foreground='white')
        self.style.map('TButton', background=[('active', '#005bb5')])
        self.style.configure('TLabel', background='#f0f4f8', font=('Inter', 10, 'bold'))
        self.style.configure('Accent.TFrame', background='#e8f0fe')
        self.style.configure('Treeview.Heading', font=('Inter', 10, 'bold'), background='#007aff', foreground='white')
        self.style.configure('Treeview', font=('Inter', 10), rowheight=25)

        # Initialize UI Components
        self._create_input_panel()
        self._create_visualization_panel() # This now calls summary and filter setup
        self._create_transaction_table()
        
        # Load data on startup
        self.load_transactions()
        self.update_plots()

    def _create_input_panel(self):
        """Creates the frame for adding new transactions."""
        # ... (Input panel creation logic remains the same)
        input_frame = ttk.Frame(self, padding="20", style='Accent.TFrame')
        input_frame.grid(row=0, column=0, sticky="nsew")
        input_frame.grid_rowconfigure(9, weight=1)

        ttk.Label(input_frame, text="Add New Transaction", font=('Inter', 14, 'bold')).grid(row=0, column=0, columnspan=2, pady=(0, 20), sticky="w")

        # Input fields setup
        self.fields = {}
        row = 1
        
        # Date Input
        ttk.Label(input_frame, text="Date (YYYY-MM-DD):").grid(row=row, column=0, sticky="w", pady=5)
        self.fields['date'] = ttk.Entry(input_frame, width=30)
        self.fields['date'].grid(row=row, column=1, sticky="we", pady=5, padx=5)
        self.fields['date'].insert(0, datetime.now().strftime("%Y-%m-%d"))
        row += 1

        # Type (Income/Expense) Radio Buttons
        self.transaction_type = tk.StringVar(value='Expense')
        ttk.Label(input_frame, text="Type:").grid(row=row, column=0, sticky="w", pady=5)
        type_frame = ttk.Frame(input_frame)
        type_frame.grid(row=row, column=1, sticky="w", pady=5, padx=5)
        ttk.Radiobutton(type_frame, text="Income", variable=self.transaction_type, value='Income', command=self._update_categories).pack(side='left', padx=10)
        ttk.Radiobutton(type_frame, text="Expense", variable=self.transaction_type, value='Expense', command=self._update_categories).pack(side='left')
        row += 1

        # Category Dropdown
        ttk.Label(input_frame, text="Category:").grid(row=row, column=0, sticky="w", pady=5)
        self.fields['category_var'] = tk.StringVar(self)
        self.fields['category_menu'] = ttk.Combobox(input_frame, textvariable=self.fields['category_var'], state="readonly", width=28)
        self.fields['category_menu'].grid(row=row, column=1, sticky="we", pady=5, padx=5)
        self._update_categories()
        row += 1

        # Amount Input
        ttk.Label(input_frame, text="Amount ($):").grid(row=row, column=0, sticky="w", pady=5)
        self.fields['amount'] = ttk.Entry(input_frame, width=30)
        self.fields['amount'].grid(row=row, column=1, sticky="we", pady=5, padx=5)
        row += 1

        # Description Input
        ttk.Label(input_frame, text="Description:").grid(row=row, column=0, sticky="w", pady=5)
        self.fields['description'] = ttk.Entry(input_frame, width=30)
        self.fields['description'].grid(row=row, column=1, sticky="we", pady=5, padx=5)
        row += 1

        # Add Button
        ttk.Button(input_frame, text="Add Transaction", command=self.add_transaction_handler).grid(row=row, column=0, columnspan=2, pady=20, sticky="we")
        row += 1
    
    def _update_categories(self):
        """Updates the category dropdown based on the selected transaction type."""
        selected_type = self.transaction_type.get()
        if selected_type == 'Income':
            categories = self.income_categories
        else:
            categories = self.expense_categories
        
        self.fields['category_menu']['values'] = categories
        if categories:
            self.fields['category_var'].set(categories[0]) # Set default to the first item

    def _create_visualization_panel(self):
        """Creates the frame for the transaction table and charts."""
        viz_frame = ttk.Frame(self, padding="10")
        viz_frame.grid(row=0, column=1, sticky="nsew")
        viz_frame.grid_columnconfigure(0, weight=1)

        # Row 0: Charts
        self.chart_frame = ttk.Frame(viz_frame, padding="10", height=300)
        self.chart_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))
        self.chart_frame.grid_columnconfigure(0, weight=1)
        self.chart_frame.grid_rowconfigure(0, weight=1)
        
        # Row 1: Summary Statistics
        self._create_summary_panel(viz_frame, row=1)

        # Row 2: Filters
        self._create_filter_controls(viz_frame, row=2)
        
        # Row 3: Transaction Table
        self.table_frame = ttk.Frame(viz_frame, padding="10")
        self.table_frame.grid(row=3, column=0, sticky="nsew")
        viz_frame.grid_rowconfigure(3, weight=1) # Give table most vertical space

    def _create_summary_panel(self, master, row):
        """Creates a panel to display summary statistics."""
        summary_frame = ttk.Frame(master, padding="10", style='Accent.TFrame')
        summary_frame.grid(row=row, column=0, sticky="ew", pady=5)
        
        self.summary_labels = {}
        metrics = [("Net Worth", '#007aff'), ("Total Income", '#4CAF50'), ("Total Expenses", '#FF6347')]
        
        for i, (text, color) in enumerate(metrics):
            label = ttk.Label(summary_frame, text=f"{text}: $0.00", foreground=color, font=('Inter', 11, 'bold'))
            label.grid(row=0, column=i, padx=20, pady=5)
            self.summary_labels[text] = label
        
        # Calculate summary initially
        self.calculate_summary_stats()

    def _create_filter_controls(self, master, row):
        """Creates date and type filter controls."""
        filter_frame = ttk.Frame(master, padding="10")
        filter_frame.grid(row=row, column=0, sticky="ew", pady=5)
        
        ttk.Label(filter_frame, text="Filter:").pack(side=tk.LEFT, padx=(0, 10))

        # Date Range Filter
        ttk.Label(filter_frame, text="Start Date:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(filter_frame, textvariable=self.filter_start_date, width=15).pack(side=tk.LEFT, padx=5)

        ttk.Label(filter_frame, text="End Date:").pack(side=tk.LEFT, padx=(10, 5))
        ttk.Entry(filter_frame, textvariable=self.filter_end_date, width=15).pack(side=tk.LEFT, padx=5)
        
        # Type Filter
        ttk.Label(filter_frame, text="Type:").pack(side=tk.LEFT, padx=(10, 5))
        type_options = ['All', 'Income', 'Expense']
        ttk.Combobox(filter_frame, textvariable=self.filter_type, values=type_options, state="readonly", width=10).pack(side=tk.LEFT, padx=5)
        
        # Apply Button
        ttk.Button(filter_frame, text="Apply Filters", command=self.apply_filters).pack(side=tk.LEFT, padx=15)
        
        # Reset Button
        ttk.Button(filter_frame, text="Reset", command=self.reset_filters).pack(side=tk.LEFT)

    def _create_transaction_table(self):
        """Sets up the Treeview for displaying transactions."""
        # ... (Table creation logic remains the same)
        table_columns = ('id', 'date', 'type', 'category', 'amount', 'description')
        self.tree = ttk.Treeview(self.table_frame, columns=table_columns, show='headings', selectmode='browse')

        # Configure headings and widths
        self.tree.heading('id', text='ID')
        self.tree.heading('date', text='Date')
        self.tree.heading('type', text='Type')
        self.tree.heading('category', text='Category')
        self.tree.heading('amount', text='Amount')
        self.tree.heading('description', text='Description')

        self.tree.column('id', width=50, anchor='center')
        self.tree.column('date', width=100, anchor='center')
        self.tree.column('type', width=80, anchor='center')
        self.tree.column('category', width=120)
        self.tree.column('amount', width=100, anchor='e')
        self.tree.column('description', width=200)

        # Scrollbar
        scrollbar = ttk.Scrollbar(self.table_frame, orient=tk.VERTICAL, command=self.tree.yview)
        self.tree.configure(yscrollcommand=scrollbar.set)

        self.tree.pack(fill='both', expand=True, side='left')
        scrollbar.pack(fill='y', side='right')

        # Delete Button for selected item
        ttk.Button(self.table_frame, text="Delete Selected", command=self.delete_selected_transaction).pack(pady=10)

    # --- 3. Data Handling Logic (Enhanced) ---

    def apply_filters(self):
        """Applies the current filter settings and reloads data/plots."""
        self.load_transactions()
        self.update_plots()
        self.calculate_summary_stats()

    def reset_filters(self):
        """Clears all filters and reloads data/plots."""
        self.filter_start_date.set("")
        self.filter_end_date.set("")
        self.filter_type.set("All")
        self.load_transactions()
        self.update_plots()
        self.calculate_summary_stats()


    def load_transactions(self):
        """Fetches transactions from DB using current filters and populates the Treeview."""
        # Get filter values
        start_date = self.filter_start_date.get()
        end_date = self.filter_end_date.get()
        trans_type = self.filter_type.get()
        
        # Basic date format validation
        try:
            if start_date: datetime.strptime(start_date, "%Y-%m-%d")
            if end_date: datetime.strptime(end_date, "%Y-%m-%d")
        except ValueError:
            messagebox.showerror("Filter Error", "Invalid date format in filters. Use YYYY-MM-DD.")
            return

        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        transactions = self.db.get_all_transactions(start_date=start_date, end_date=end_date, trans_type=trans_type)

        # Insert new data
        for row in transactions:
            transaction_id, date, type, category, amount, description = row
            formatted_amount = f"${amount:,.2f}"
            
            tag = 'income' if type == 'Income' else 'expense'
            self.tree.tag_configure('income', background='#e6ffe6', foreground='#006600')
            self.tree.tag_configure('expense', background='#ffe6e6', foreground='#cc0000')

            self.tree.insert('', tk.END, values=(transaction_id, date, type, category, formatted_amount, description), tags=(tag,))
        
        # Note: update_plots and calculate_summary_stats are now called separately via apply_filters/reset_filters
        # and on startup.

    def add_transaction_handler(self):
        """Validates and adds a new transaction."""
        try:
            date_str = self.fields['date'].get()
            transaction_type = self.transaction_type.get()
            category = self.fields['category_var'].get()
            amount = float(self.fields['amount'].get())
            description = self.fields['description'].get()

            # Simple validation
            datetime.strptime(date_str, "%Y-%m-%d") # Check date format
            if amount <= 0:
                raise ValueError("Amount must be positive.")
            if not category:
                raise ValueError("Category is required.")

            if self.db.add_transaction(date_str, transaction_type, category, amount, description):
                messagebox.showinfo("Success", "Transaction added successfully.")
                self.load_transactions()
                self.update_plots()
                self.calculate_summary_stats()
                # Clear inputs after success (except date)
                self.fields['amount'].delete(0, tk.END)
                self.fields['description'].delete(0, tk.END)

        except ValueError as e:
            messagebox.showerror("Input Error", f"Invalid input: {e}\nEnsure date is YYYY-MM-DD and amount is a positive number.")
        except Exception as e:
            messagebox.showerror("Error", f"An unexpected error occurred: {e}")

    def delete_selected_transaction(self):
        """Deletes the transaction selected in the Treeview."""
        selected_item = self.tree.selection()
        if not selected_item:
            messagebox.showwarning("Selection Error", "Please select a transaction to delete.")
            return
        
        values = self.tree.item(selected_item[0], 'values')
        transaction_id = values[0]

        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete Transaction ID: {transaction_id}?"):
            if self.db.delete_transaction(transaction_id):
                messagebox.showinfo("Success", "Transaction deleted.")
                self.load_transactions()
                self.update_plots()
                self.calculate_summary_stats()
            else:
                messagebox.showerror("Error", "Failed to delete transaction.")

    # --- 4. Summary & Visualization ---
    
    def calculate_summary_stats(self):
        """Calculates and updates Net Worth, Total Income, and Total Expenses."""
        df = self._prepare_data_for_plots(for_plots=False) # Get all data, not just filtered
        
        if df.empty:
            total_income = 0
            total_expense = 0
        else:
            total_income = df[df['type'] == 'Income']['amount'].sum()
            total_expense = df[df['type'] == 'Expense']['amount'].sum()

        net_worth = total_income - total_expense
        
        # Update labels
        self.summary_labels["Net Worth"].config(text=f"Net Worth: ${net_worth:,.2f}")
        self.summary_labels["Total Income"].config(text=f"Total Income: ${total_income:,.2f}")
        self.summary_labels["Total Expenses"].config(text=f"Total Expenses: ${total_expense:,.2f}")


    def _prepare_data_for_plots(self, for_plots=True):
        """
        Fetches transactions and prepares a pandas DataFrame for plotting. 
        If for_plots is True, it applies the current filters.
        """
        if for_plots:
            start_date = self.filter_start_date.get()
            end_date = self.filter_end_date.get()
            trans_type = self.filter_type.get()
        else:
            # When calculating overall summary, we want ALL data
            start_date, end_date, trans_type = None, None, 'All'
            
        transactions = self.db.get_all_transactions(start_date=start_date, end_date=end_date, trans_type=trans_type)

        if not transactions:
            return pd.DataFrame()

        # Create DataFrame
        df = pd.DataFrame(transactions, columns=['id', 'date', 'type', 'category', 'amount', 'description'])
        df['date'] = pd.to_datetime(df['date'])
        
        # Convert all expenses to negative numbers for running balance
        df['signed_amount'] = df.apply(
            lambda row: -row['amount'] if row['type'] == 'Expense' else row['amount'], axis=1
        )
        
        # Sort by date for accurate running balance calculation
        df = df.sort_values(by='date').reset_index(drop=True)
        
        # Calculate Running Balance
        df['running_balance'] = df['signed_amount'].cumsum()
        
        return df

    def update_plots(self):
        """Generates and displays the Running Balance and Category Summary charts based on filters."""
        df = self._prepare_data_for_plots(for_plots=True)

        # Clear existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if df.empty:
            ttk.Label(self.chart_frame, text="No transactions available for the selected filters.", 
                      font=('Inter', 12), foreground='gray').pack(expand=True)
            return

        # 1. Running Balance Chart (Left side of chart frame)
        self.plot_running_balance(df)

        # 2. Category Summary (Right side of chart frame)
        self.plot_category_summary(df)

    def plot_running_balance(self, df):
        """Generates the main line chart for balance over time."""
        fig = Figure(figsize=(5, 3.5), dpi=100)
        ax = fig.add_subplot(111)

        ax.plot(df['date'], df['running_balance'], 
                color='#007aff', linewidth=2, marker='o', markersize=4, linestyle='-')
        
        # Styling
        ax.set_title('Cumulative Balance Over Time (Filtered)', fontsize=12, weight='bold')
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Balance ($)', fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        fig.autofmt_xdate(rotation=45)
        
        final_balance = df['running_balance'].iloc[-1]
        balance_color = '#006600' if final_balance >= 0 else '#cc0000'
        ax.axhline(0, color='gray', linestyle='--')

        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        canvas.draw()
        
        ttk.Label(self.chart_frame, 
                  text=f"End Balance: ${final_balance:,.2f}", 
                  font=('Inter', 12, 'bold'), 
                  foreground=balance_color).pack(side=tk.TOP, anchor='w', padx=10)


    def plot_category_summary(self, df):
        """Generates a bar chart summary of Income and Expense by category."""
        income_summary = df[df['type'] == 'Income'].groupby('category')['amount'].sum().sort_values(ascending=False)
        expense_summary = df[df['type'] == 'Expense'].groupby('category')['amount'].sum().sort_values(ascending=False)
        
        top_n = 5
        plot_data = pd.concat([
            income_summary.head(top_n).rename('Income'),
            expense_summary.head(top_n).rename('Expense')
        ], axis=1).fillna(0)

        fig = Figure(figsize=(5, 3.5), dpi=100)
        ax = fig.add_subplot(111)
        
        categories = plot_data.index
        x = np.arange(len(categories))
        width = 0.35

        rects1 = ax.bar(x - width/2, plot_data['Income'], width, label='Income', color='#4CAF50')
        rects2 = ax.bar(x + width/2, plot_data['Expense'], width, label='Expense', color='#FF6347')

        # Styling
        ax.set_title(f'Top {top_n} Category Summary (Filtered)', fontsize=12, weight='bold')
        ax.set_ylabel('Total Amount ($)', fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        fig.tight_layout(pad=1.5)

        # Add canvas to the chart frame
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.RIGHT, fill=tk.BOTH, expand=True, padx=10)
        canvas.draw()
        
    def on_closing(self):
        """Handles closing the application and closing the DB connection."""
        if messagebox.askyesno("Quit", "Do you want to quit the application?"):
            self.db.close()
            self.destroy()

if __name__ == "__main__":
    app = FinanceApp()
    app.protocol("WM_DELETE_WINDOW", app.on_closing)
    app.mainloop()
