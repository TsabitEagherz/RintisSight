from __future__ import annotations

import csv
import io
import json
import os
import random
import sqlite3
from datetime import date, datetime, timedelta
from pathlib import Path

import pandas as pd
from flask import Flask, Response, flash, redirect, render_template, request, session, url_for

ROOT = Path(__file__).parent
DB_PATH = ROOT / "rintissight.db"
app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "local-demo-key-change-before-deploy")


def connect():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_db():
    with connect() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS profile (
          id INTEGER PRIMARY KEY CHECK(id=1), name TEXT, sector TEXT, capital INTEGER,
          knowledge INTEGER, skills TEXT, hours INTEGER, mode TEXT
        );
        CREATE TABLE IF NOT EXISTS vendors (
          id INTEGER PRIMARY KEY, name TEXT, item TEXT, unit_cost REAL, moq INTEGER, lead_days INTEGER
        );
        CREATE TABLE IF NOT EXISTS transactions (
          id INTEGER PRIMARY KEY, day TEXT, product TEXT, channel TEXT, vendor_id INTEGER,
          units INTEGER, price REAL, material REAL, packaging REAL, platform_fee REAL, other_cost REAL
        );
        """)
        if conn.execute("SELECT COUNT(*) FROM vendors").fetchone()[0] == 0:
            conn.executemany(
                "INSERT INTO vendors(name,item,unit_cost,moq,lead_days) VALUES(?,?,?,?,?)",
                [("Kebun Pagi", "Bahan utama", 7800, 20, 2),
                 ("Pasar Mitra", "Bahan utama", 8400, 10, 1),
                 ("Pangan Lestari", "Bahan utama", 7200, 50, 4)],
            )
        if conn.execute("SELECT COUNT(*) FROM transactions").fetchone()[0] == 0:
            rng = random.Random(42)
            rows = []
            first_day = date.today() - timedelta(days=29)
            for offset in range(30):
                for product, price, base in [("Granola Madu", 32000, 8), ("Granola Cokelat", 35000, 5)]:
                    units = max(1, base + rng.randint(-3, 5))
                    channel = rng.choice(["Marketplace", "WhatsApp", "Toko"])
                    vendor_id = rng.choice([1, 2, 3])
                    material = {1: 7800, 2: 8400, 3: 7200}[vendor_id]
                    fee_rate = .12 if channel == "Marketplace" else .025 if channel == "WhatsApp" else 0
                    rows.append(((first_day + timedelta(days=offset)).isoformat(), product, channel,
                                 vendor_id, units, price, material, 1800, price * fee_rate, units * 650))
            conn.executemany(
                "INSERT INTO transactions(day,product,channel,vendor_id,units,price,material,packaging,platform_fee,other_cost) VALUES(?,?,?,?,?,?,?,?,?,?)",
                rows,
            )


def fetch_data():
    with connect() as conn:
        tx = pd.read_sql_query(
            "SELECT t.*,v.name AS vendor FROM transactions t LEFT JOIN vendors v ON v.id=t.vendor_id ORDER BY day", conn
        )
        vendors = pd.read_sql_query("SELECT * FROM vendors ORDER BY unit_cost", conn)
        profile = conn.execute("SELECT * FROM profile WHERE id=1").fetchone()
    return tx, vendors, profile


def add_metrics(tx: pd.DataFrame) -> pd.DataFrame:
    data = tx.copy()
    if data.empty:
        for col in ("revenue", "hpp", "profit"):
            data[col] = pd.Series(dtype="float64")
        return data
    data["revenue"] = data["units"] * data["price"]
    data["hpp"] = data["units"] * (data["material"] + data["packaging"] + data["other_cost"]) + data["platform_fee"]
    data["profit"] = data["revenue"] - data["hpp"]
    return data


def money(value):
    return "Rp " + f"{float(value):,.0f}".replace(",", ".")


def page_context(active, **values):
    return {"active": active, **values}


def get_ideas(capital, skills, hours):
    options = [
        {"name": "Granola rumahan", "sector": "Makanan & minuman", "cost": min(capital * .68, 3500000),
         "fit": min(96, 74 + (8 if "Memasak" in skills else 0) + (5 if hours >= 3 else 0)),
         "why": "Mulai dari batch kecil, uji dengan pre-order, dan gunakan bahan yang mudah dicari."},
        {"name": "Hampers hadiah lokal", "sector": "Produk kreatif", "cost": min(capital * .48, 2000000),
         "fit": min(96, 72 + (9 if "Desain" in skills else 0) + (5 if "Jualan" in skills else 0)),
         "why": "Produksi mengikuti pesanan sehingga risiko stok awal relatif rendah."},
        {"name": "Jasa konten UMKM", "sector": "Jasa digital", "cost": min(capital * .25, 1200000),
         "fit": min(96, 70 + (12 if "Desain" in skills else 0) + (8 if "Digital" in skills else 0)),
         "why": "Mengandalkan kemampuan dan waktu, dengan kebutuhan modal fisik ringan."},
    ]
    return sorted(options, key=lambda item: item["fit"], reverse=True)


def recommendation_from_form(form):
    capital = int(form.get("capital", 5_000_000))
    skills = form.getlist("skills")
    hours = int(form.get("hours", 3))
    return get_ideas(capital, skills, hours)


def build_charts(data, vendors):
    if data.empty:
        return {}
    daily = data.groupby("day", as_index=False)[["revenue", "profit"]].sum()
    costs = [
        float((data.units * data.material).sum()), float((data.units * data.packaging).sum()),
        float((data.units * data.other_cost).sum()), float(data.platform_fee.sum()),
    ]
    products = data.groupby("product", as_index=False).units.sum().sort_values("units")
    channels = data.groupby("channel", as_index=False).agg(omzet=("revenue", "sum"), laba=("profit", "sum"))
    vendor_costs = data.groupby("vendor", as_index=False).agg(hpp_bahan=("material", "mean"))
    product_margin = data.groupby("product", as_index=False).agg(omzet=("revenue", "sum"), laba=("profit", "sum"))
    product_margin["margin"] = product_margin.apply(lambda row: row.laba / row.omzet * 100 if row.omzet else 0, axis=1)
    return {
        "daily": {"data": [
            {"type": "scatter", "mode": "lines", "name": "Omzet", "x": daily.day.tolist(), "y": daily.revenue.tolist(), "line": {"color": "#72a87e", "width": 3}},
            {"type": "scatter", "mode": "lines", "name": "Laba", "x": daily.day.tolist(), "y": daily.profit.tolist(), "line": {"color": "#718fa3", "width": 3}},
        ], "layout": {"title": "Omzet dan laba harian", "yaxis": {"title": "Rupiah"}}},
        "costs": {"data": [{"type": "pie", "labels": ["Bahan", "Kemasan", "Biaya lain", "Komisi kanal"], "values": costs,
                            "hole": .58, "marker": {"colors": ["#72a87e", "#a5c59f", "#d8e5c9", "#dfb779"]}}],
                  "layout": {"title": "Anatomi biaya", "showlegend": True}},
        "products": {"data": [{"type": "bar", "orientation": "h", "x": products.units.tolist(), "y": products.product.tolist(),
                                "marker": {"color": "#80ad88"}}], "layout": {"title": "Unit terjual per produk", "xaxis": {"title": "Unit"}}},
        "channels": {"data": [
            {"type": "bar", "name": "Omzet", "x": channels.channel.tolist(), "y": channels.omzet.tolist(), "marker": {"color": "#87b38e"}},
            {"type": "bar", "name": "Laba", "x": channels.channel.tolist(), "y": channels.laba.tolist(), "marker": {"color": "#879fb1"}},
        ], "layout": {"title": "Kinerja per kanal", "barmode": "group", "yaxis": {"title": "Rupiah"}}},
        "vendors": {"data": [{"type": "bar", "x": vendor_costs.vendor.tolist(), "y": vendor_costs.hpp_bahan.tolist(),
                               "marker": {"color": "#91b998"}}], "layout": {"title": "Rata-rata biaya bahan per pemasok", "yaxis": {"title": "Rp / unit"}}},
        "marginProduct": {"data": [{"type": "bar", "x": product_margin.product.tolist(), "y": product_margin.margin.tolist(),
                                     "marker": {"color": "#8ea7b6"}}], "layout": {"title": "Margin bersih per produk", "yaxis": {"title": "%", "ticksuffix": "%"}}},
    }


@app.get("/")
def home():
    return render_template("home.html", **page_context("home"))


@app.route("/asesmen", methods=["GET", "POST"])
def assessment():
    _, _, profile = fetch_data()
    recommendations = session.get("recommendations")
    if request.method == "POST":
        capital = int(request.form.get("capital", 5_000_000))
        knowledge = int(request.form.get("knowledge", 2))
        skills = request.form.getlist("skills")
        hours = int(request.form.get("hours", 3))
        mode = request.form.get("mode", "Baru merintis")
        name = request.form.get("name", "").strip()
        with connect() as conn:
            conn.execute("""INSERT INTO profile(id,name,sector,capital,knowledge,skills,hours,mode)
                VALUES(1,?,'Belum dipilih',?,?,?,?,?) ON CONFLICT(id) DO UPDATE SET
                name=excluded.name,capital=excluded.capital,knowledge=excluded.knowledge,
                skills=excluded.skills,hours=excluded.hours,mode=excluded.mode""",
                (name, capital, knowledge, ",".join(skills), hours, mode))
        session["recommendations"] = get_ideas(capital, skills, hours)
        session.pop("selected_idea", None)
        flash("Asesmen tersimpan. Berikut tiga inspirasi usaha untukmu.", "success")
        return redirect(url_for("assessment"))
    return render_template("assessment.html", **page_context("assessment", profile=profile, recommendations=recommendations,
                           selected=session.get("selected_idea"), skills_list=["Memasak", "Desain", "Jualan", "Digital", "Kerajinan", "Menulis"]))


@app.post("/ide/<int:index>/pilih")
def choose_idea(index):
    recommendations = session.get("recommendations", [])
    if not 0 <= index < len(recommendations):
        flash("Silakan jalankan asesmen terlebih dahulu.", "error")
        return redirect(url_for("assessment"))
    selected = recommendations[index]["name"]
    with connect() as conn:
        conn.execute("UPDATE profile SET sector=? WHERE id=1", (selected,))
    session["selected_idea"] = selected
    flash(f"{selected} dipilih. Workspace siap kamu jelajahi dengan data contoh.", "success")
    return redirect(url_for("workspace"))


@app.get("/ruang-kerja")
def workspace():
    tx, vendors, profile = fetch_data()
    data = add_metrics(tx)
    revenue = float(data.revenue.sum()) if not data.empty else 0
    profit = float(data.profit.sum()) if not data.empty else 0
    margin = profit / revenue * 100 if revenue else 0
    totals = {"revenue": revenue, "profit": profit, "margin": margin, "units": int(data.units.sum()) if not data.empty else 0}
    best_vendor = vendors.iloc[0].to_dict() if not vendors.empty else None
    return render_template("workspace.html", **page_context("workspace", profile=profile, totals=totals,
                           tx=tx.tail(10).iloc[::-1].to_dict("records"), charts=build_charts(data, vendors), vendors=vendors.to_dict("records"),
                           best_vendor=best_vendor, today=date.today().isoformat(), money=money))


@app.post("/transaksi")
def add_transaction():
    try:
        day = datetime.strptime(request.form["day"], "%Y-%m-%d").date().isoformat()
        product = request.form["product"].strip()
        channel = request.form["channel"]
        units = int(request.form["units"])
        price = float(request.form["price"])
        material = float(request.form["material"])
        packaging = float(request.form["packaging"])
        if not product or units < 1 or min(price, material, packaging) < 0 or channel not in {"Marketplace", "WhatsApp", "Toko"}:
            raise ValueError
    except (KeyError, TypeError, ValueError):
        flash("Periksa kembali data transaksi yang kamu masukkan.", "error")
        return redirect(url_for("workspace"))
    rate = .12 if channel == "Marketplace" else .025 if channel == "WhatsApp" else 0
    with connect() as conn:
        conn.execute("""INSERT INTO transactions(day,product,channel,vendor_id,units,price,material,packaging,platform_fee,other_cost)
            VALUES(?,?,?,?,?,?,?,?,?,?)""", (day, product, channel, 1, units, price, material, packaging, price * units * rate, units * 650))
    flash("Transaksi berhasil disimpan.", "success")
    return redirect(url_for("workspace"))


@app.post("/transaksi/impor")
def import_transactions():
    upload = request.files.get("file")
    required = ["day", "product", "channel", "vendor_id", "units", "price", "material", "packaging", "platform_fee", "other_cost"]
    if not upload or not upload.filename.lower().endswith(".csv"):
        flash("Pilih berkas CSV untuk diimpor.", "error")
        return redirect(url_for("workspace"))
    try:
        frame = pd.read_csv(upload)
        if not set(required).issubset(frame.columns):
            raise ValueError("Kolom CSV belum lengkap. Gunakan format yang ditampilkan pada formulir.")
        frame = frame[required].copy()
        for column in ["day", "product", "channel"]:
            frame[column] = frame[column].astype(str)
        numeric = ["vendor_id", "units", "price", "material", "packaging", "platform_fee", "other_cost"]
        for column in numeric:
            frame[column] = pd.to_numeric(frame[column], errors="raise")
        if (frame["units"] < 1).any() or not frame["channel"].isin(["Marketplace", "WhatsApp", "Toko"]).all():
            raise ValueError("Pastikan jumlah unit dan pilihan kanal valid.")
        with connect() as conn:
            frame.to_sql("transactions", conn, if_exists="append", index=False)
    except Exception as exc:
        flash(str(exc) if isinstance(exc, ValueError) else "CSV tidak dapat dibaca. Periksa kembali formatnya.", "error")
        return redirect(url_for("workspace"))
    flash(f"{len(frame)} transaksi berhasil diimpor.", "success")
    return redirect(url_for("workspace"))


@app.get("/transaksi/ekspor")
def export_transactions():
    tx, _, _ = fetch_data()
    output = io.StringIO()
    tx.to_csv(output, index=False)
    return Response("\ufeff" + output.getvalue(), mimetype="text/csv; charset=utf-8",
                    headers={"Content-Disposition": "attachment; filename=laporan-rintissight.csv"})


@app.route("/konsultan", methods=["GET", "POST"])
def consultant():
    tx, _, profile = fetch_data()
    data = add_metrics(tx)
    revenue = float(data.revenue.sum()) if not data.empty else 0
    profit = float(data.profit.sum()) if not data.empty else 0
    context = {"usaha": profile["sector"] if profile else "belum ditentukan", "omzet_30_hari": int(revenue),
               "laba_30_hari": int(profit), "margin_persen": round(profit / revenue * 100, 1) if revenue else 0,
               "kanal": data.groupby("channel").profit.sum().to_dict() if not data.empty else {}}
    if request.method == "POST":
        prompt = request.form.get("prompt", "").strip()
        if not prompt:
            return redirect(url_for("consultant"))
        answer = None
        api_key = os.getenv("GEMINI_API_KEY")
        if api_key:
            try:
                from google import genai
                client = genai.Client(api_key=api_key)
                response = client.models.generate_content(
                    model=os.getenv("GEMINI_MODEL", "gemini-3.8-flash"),
                    contents=("Kamu konsultan UMKM berbahasa Indonesia. Beri saran ringkas, praktis, tidak mengarang, "
                              f"dan gunakan konteks angka ini: {json.dumps(context, ensure_ascii=False)}. Pertanyaan: {prompt}"),
                )
                answer = response.text
            except Exception:
                flash("Gemini belum dapat dihubungi. Aku berikan jawaban demo untuk sementara.", "error")
        if not answer:
            low = prompt.lower()
            if any(word in low for word in ["margin", "harga", "marketplace"]):
                answer = (f"Margin usaha dari data 30 hari sekitar {context['margin_persen']}%. Hitung seluruh biaya per pesanan, "
                          "termasuk komisi dan promo. Uji perubahan harga kecil atau bundling, lalu bandingkan hasilnya selama seminggu.")
            elif any(word in low for word in ["stok", "deadstock"]):
                answer = "Kelompokkan stok berdasarkan lama tersimpan. Untuk stok lambat, uji bundling dengan produk terlaris atau promo terbatas. Catat hasilnya untuk pembelian berikutnya."
            else:
                answer = (f"Ringkasan 30 hari: omzet {money(revenue)}, estimasi laba {money(profit)}, "
                          f"margin {context['margin_persen']}%. Mulai dari satu eksperimen yang bisa diukur minggu ini. "
                          "Tujuan utamamu sekarang penjualan, margin, atau pengelolaan stok?")
        history = session.get("chat", [])
        history.extend([{"role": "user", "content": prompt}, {"role": "assistant", "content": answer}])
        session["chat"] = history[-20:]
        return redirect(url_for("consultant"))
    return render_template("consultant.html", **page_context("consultant", chat=session.get("chat", []),
                           has_gemini=bool(os.getenv("GEMINI_API_KEY")), totals={"revenue": revenue, "profit": profit,
                           "margin": context["margin_persen"]}, money=money))


@app.post("/konsultan/bersihkan")
def clear_chat():
    session.pop("chat", None)
    flash("Percakapan dibersihkan.", "success")
    return redirect(url_for("consultant"))


@app.route("/label", methods=["GET", "POST"])
def label():
    if request.method == "POST":
        session["label_data"] = {key: request.form.get(key, "").strip() for key in ["product", "brand", "ingredients", "net", "contact"]}
        flash("Pratinjau label diperbarui.", "success")
        return redirect(url_for("label"))
    values = session.get("label_data", {"product": "Granola Madu", "brand": "Rintis Kitchen",
                 "ingredients": "Oat, madu, kacang almond", "net": "150 g", "contact": "@rintiskitchen"})
    return render_template("label.html", **page_context("label", values=values))


@app.errorhandler(404)
def not_found(_error):
    return render_template("error.html", **page_context("", code=404, message="Halaman yang kamu cari tidak tersedia.")), 404


initialize_db()

if __name__ == "__main__":
    app.run(debug=os.getenv("FLASK_DEBUG", "0") == "1")
