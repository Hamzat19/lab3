from flask import Flask, render_template, request, redirect, url_for, flash
from db import q

app = Flask(__name__)
app.secret_key = "lab3-secret"


@app.route("/")
def index():
    return render_template("index.html")


# ---------- Формы ввода ----------

@app.route("/charges", methods=["GET", "POST"])
def charges():
    if request.method == "POST":
        period = request.form["period"] + "-01"
        q("""INSERT INTO charges(account_id, period, amount, service_type)
             VALUES (%s, %s, %s, %s)""",
          (request.form["account_id"], period,
           request.form["amount"], request.form.get("service_type")),
          fetch=False)
        flash("Начисление сохранено")
        return redirect(url_for("charges"))
    return render_template("charges_form.html")


@app.route("/payments", methods=["GET", "POST"])
def payments():
    if request.method == "POST":
        period = request.form["period"] + "-01"
        q("""INSERT INTO payments(account_id, period, amount, pay_date)
             VALUES (%s, %s, %s, %s)""",
          (request.form["account_id"], period,
           request.form["amount"], request.form["pay_date"]),
          fetch=False)
        flash("Платёж сохранён")
        return redirect(url_for("payments"))
    return render_template("payments_form.html")


@app.route("/saldo", methods=["GET", "POST"])
def saldo():
    if request.method == "POST":
        period = request.form["period"] + "-01"
        q("""INSERT INTO saldo(account_id, period, saldo_begin, saldo_end)
             VALUES (%s, %s, %s, %s)
             ON CONFLICT (account_id, period) DO UPDATE
             SET saldo_begin = EXCLUDED.saldo_begin,
                 saldo_end   = EXCLUDED.saldo_end""",
          (request.form["account_id"], period,
           request.form["saldo_begin"], request.form["saldo_end"]),
          fetch=False)
        flash("Сальдо сохранено")
        return redirect(url_for("saldo"))
    return render_template("saldo_form.html")


# ---------- Отчёты ----------

@app.route("/report/turnover")
def report_turnover():
    year = request.args.get("year", 2024, type=int)
    rows = q("SELECT * FROM get_turnover_sheet(%s)", (year,))
    return render_template("report_turnover.html", rows=rows, year=year)


@app.route("/report/account/<int:account_id>")
def report_account(account_id):
    year = request.args.get("year", 2024, type=int)
    rows = q("SELECT * FROM get_account_turnover(%s, %s)", (account_id, year))
    return render_template("report_account.html",
                           rows=rows, account_id=account_id, year=year)


@app.route("/report/debtors")
def report_debtors():
    period = request.args.get("period", "2024-12-01")
    rows = q("SELECT * FROM get_debtors_summary(%s)", (period,))
    return render_template("report_debtors.html", rows=rows, period=period)


if __name__ == "__main__":
    app.run(debug=True)