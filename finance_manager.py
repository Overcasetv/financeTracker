import tkinter as tk
from tkinter import ttk, messagebox
import sqlite3
import pandas as pd
from datetime import datetime
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
import numpy as np
from matplotlib.figure import Figure # <-- FIX: Import Figure explicitly

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

    def get_all_transactions(self):
        """Retrieves all transactions, ordered by date."""
        self.cursor.execute("SELECT id, date, type, category, amount, description FROM transactions ORDER BY date, id")
        return self.cursor.fetchall()

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
        self.geometry("1200x800")
        self.db = DatabaseManager()

        # Define default categories
        self.income_categories = ['Salary', 'Freelance', 'Investment', 'Other Income']
        self.expense_categories = ['Rent', 'Groceries', 'Utilities', 'Transportation', 'Entertainment', 'Savings', 'Other Expense']

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
        self._create_visualization_panel()
        self._create_transaction_table()
        
        # Load data on startup
        self.load_transactions()
        self.update_plots()

    def _create_input_panel(self):
        """Creates the frame for adding new transactions."""
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
        self.fields['category_var'].set(categories[0]) # Set default to the first item

    def _create_visualization_panel(self):
        """Creates the frame for the transaction table and charts."""
        viz_frame = ttk.Frame(self, padding="20")
        viz_frame.grid(row=0, column=1, sticky="nsew")
        viz_frame.grid_rowconfigure(0, weight=1) # Chart frame
        viz_frame.grid_rowconfigure(1, weight=1) # Table frame
        viz_frame.grid_columnconfigure(0, weight=1)

        # 2a. Chart Display Frame
        self.chart_frame = ttk.Frame(viz_frame, padding="10")
        self.chart_frame.grid(row=0, column=0, sticky="nsew", pady=(0, 10))

        # 2b. Transaction Table (Will be placed below the chart)
        self.table_frame = ttk.Frame(viz_frame, padding="10")
        self.table_frame.grid(row=1, column=0, sticky="nsew")

    def _create_transaction_table(self):
        """Sets up the Treeview for displaying transactions."""
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

    # --- 3. Data Handling Logic ---

    def load_transactions(self):
        """Fetches transactions from DB and populates the Treeview."""
        # Clear existing data
        for item in self.tree.get_children():
            self.tree.delete(item)

        transactions = self.db.get_all_transactions()

        # Insert new data
        for row in transactions:
            transaction_id, date, type, category, amount, description = row
            # Format amount nicely
            formatted_amount = f"${amount:,.2f}"
            
            # Apply color tag for visual distinction
            tag = 'income' if type == 'Income' else 'expense'
            
            # Configure tags (requires mapping the tag name to style)
            self.tree.tag_configure('income', background='#e6ffe6', foreground='#006600') # Light green for income
            self.tree.tag_configure('expense', background='#ffe6e6', foreground='#cc0000') # Light red for expense

            self.tree.insert('', tk.END, values=(transaction_id, date, type, category, formatted_amount, description), tags=(tag,))
        
        self.update_plots()

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
        
        # Get the first item's values (assuming single selection)
        values = self.tree.item(selected_item[0], 'values')
        transaction_id = values[0]

        # Use a custom 'dialog' instead of the blocked tk.confirm
        if messagebox.askyesno("Confirm Deletion", f"Are you sure you want to delete Transaction ID: {transaction_id}?"):
            if self.db.delete_transaction(transaction_id):
                messagebox.showinfo("Success", "Transaction deleted.")
                self.load_transactions()
            else:
                messagebox.showerror("Error", "Failed to delete transaction.")

    # --- 4. Visualization (Matplotlib) ---
    
    def _prepare_data_for_plots(self):
        """Fetches transactions and prepares a pandas DataFrame for plotting."""
        transactions = self.db.get_all_transactions()
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
        """Generates and displays the Running Balance and Category Summary charts."""
        df = self._prepare_data_for_plots()

        # Clear existing charts
        for widget in self.chart_frame.winfo_children():
            widget.destroy()

        if df.empty:
            ttk.Label(self.chart_frame, text="No transactions recorded yet. Add some data to see the charts!", 
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

        # Plot the cumulative balance
        ax.plot(df['date'], df['running_balance'], 
                color='#007aff', linewidth=2, marker='o', markersize=4, linestyle='-')
        
        # Styling
        ax.set_title('Cumulative Balance Over Time', fontsize=12, weight='bold')
        ax.set_xlabel('Date', fontsize=10)
        ax.set_ylabel('Balance ($)', fontsize=10)
        ax.grid(True, linestyle='--', alpha=0.6)
        
        # Rotate and format x-axis dates
        fig.autofmt_xdate(rotation=45)
        
        # Display the current total balance
        final_balance = df['running_balance'].iloc[-1]
        balance_color = '#006600' if final_balance >= 0 else '#cc0000'
        ax.axhline(0, color='gray', linestyle='--') # Zero line

        # Add canvas to the chart frame
        canvas = FigureCanvasTkAgg(fig, master=self.chart_frame)
        canvas_widget = canvas.get_tk_widget()
        canvas_widget.pack(side=tk.LEFT, fill=tk.BOTH, expand=True, padx=10)
        canvas.draw()
        
        # Display the total balance clearly above the chart
        ttk.Label(self.chart_frame, 
                  text=f"Total Balance: ${final_balance:,.2f}", 
                  font=('Inter', 12, 'bold'), 
                  foreground=balance_color).pack(side=tk.TOP, anchor='w', padx=10)


    def plot_category_summary(self, df):
        """Generates a bar chart summary of Income and Expense by category."""
        # Calculate totals
        income_summary = df[df['type'] == 'Income'].groupby('category')['amount'].sum().sort_values(ascending=False)
        expense_summary = df[df['type'] == 'Expense'].groupby('category')['amount'].sum().sort_values(ascending=False)
        
        # Combine top categories for visualization
        top_n = 5
        plot_data = pd.concat([
            income_summary.head(top_n).rename('Income'),
            expense_summary.head(top_n).rename('Expense')
        ], axis=1).fillna(0)

        # Matplotlib Figure setup
        fig = Figure(figsize=(5, 3.5), dpi=100)
        ax = fig.add_subplot(111)
        
        # Plotting the data
        categories = plot_data.index
        x = np.arange(len(categories))
        width = 0.35

        rects1 = ax.bar(x - width/2, plot_data['Income'], width, label='Income', color='#4CAF50')
        rects2 = ax.bar(x + width/2, plot_data['Expense'], width, label='Expense', color='#FF6347')

        # Styling
        ax.set_title(f'Top {top_n} Category Summary', fontsize=12, weight='bold')
        ax.set_ylabel('Total Amount ($)', fontsize=10)
        ax.set_xticks(x)
        ax.set_xticklabels(categories, rotation=45, ha='right')
        ax.legend()
        fig.tight_layout(pad=1.5) # Adjust layout to prevent labels from overlapping

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
