import os
from flask import Flask, render_template, request, redirect, url_for, session, send_file
import sqlite3
from datetime import datetime, timedelta
import pandas as pd
import matplotlib.pyplot as plt
import io
import base64

app = Flask(__name__)
app.secret_key = 'your_secret_key'
DB_NAME = 'fitness_web.db'
PASSWORD = '1234'

def init_db():
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("""CREATE TABLE IF NOT EXISTS records (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            type TEXT,
            data TEXT
        )""")
        conn.commit()

def add_record(record_type, data, date):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("INSERT INTO records (date, type, data) VALUES (?, ?, ?)", (date, record_type, data))
        conn.commit()

def get_records(date):
    with sqlite3.connect(DB_NAME) as conn:
        c = conn.cursor()
        c.execute("SELECT type, data FROM records WHERE date=?", (date,))
        rows = c.fetchall()
        grouped = {}
        for r_type, r_data in rows:
            grouped.setdefault(r_type, []).append(r_data)
        return grouped

def get_weekly_data():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM records", conn)
    df['date'] = pd.to_datetime(df['date'])
    last_week = datetime.now() - timedelta(days=6)
    df = df[df['date'] >= last_week]
    df['data'] = pd.to_numeric(df['data'], errors='coerce')
    df = df.dropna()
    return df

def plot_weekly(df):
    types_to_plot = ['water', 'sleep', 'food', 'steps']
    plots = {}
    for t in types_to_plot:
        plt.figure()
        plot_df = df[df['type'] == t].groupby('date')['data'].sum()
        plot_df.plot(kind='line', marker='o', title=f"{t.capitalize()} за неделю")
        plt.tight_layout()
        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        plots[t] = base64.b64encode(buf.getvalue()).decode('utf-8')
        plt.close()
    return plots

@app.route("/export")
def export_data():
    with sqlite3.connect(DB_NAME) as conn:
        df = pd.read_sql_query("SELECT * FROM records", conn)
    output = io.StringIO()
    df.to_csv(output, index=False)
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype='text/csv', as_attachment=True, download_name='fitness_data.csv')

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        if request.form["password"] == PASSWORD:
            session["logged_in"] = True
            return redirect(url_for("index"))
    return render_template("login.html")

@app.route("/", methods=["GET", "POST"])
def index():
    if not session.get("logged_in"):
        return redirect(url_for("login"))

    today = datetime.now().strftime('%Y-%m-%d')
    if request.method == "POST":
        date = request.form.get("date") or today
        add_record(request.form["type"], request.form["data"], date)
        return redirect(url_for('index', date=date))

    selected_date = request.args.get("date") or today
    records = get_records(selected_date)
    df = get_weekly_data()
    plots = plot_weekly(df)
    return render_template("index.html", records=records, selected_date=selected_date, plots=plots)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))

if __name__ == "__main__":
    init_db()
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)))
