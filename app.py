from flask import Flask, render_template, request, redirect, url_for, flash
from db import q


app = Flask(__name__)
app.secret_key = "lab3-secret"


@app.route("/")
def index():
    stats = q("""
        SELECT
            (SELECT COUNT(DISTINCT account_id) FROM charges) AS accounts,
            (SELECT COUNT(*) FROM charges) AS total_charges,
            (SELECT COUNT(*) FROM payments) AS total_payments,
            (SELECT COALESCE(SUM(saldo_end), 0) FROM saldo) AS total_debt
    """)[0]
    return render_template("index.html", stats=stats)

# ---------- Формы ввода ----------

@app.route("/charges", methods=["GET", "POST"])
def charges():
    flash_msg = ""
    flash_type = ""

    if request.method == "POST":
        period = request.form["period"] + "-01"
        try:
            q("""INSERT INTO charges
                     (account_id, period, amount, service_type, doc_number)
                 VALUES (%s, %s, %s, %s, %s)""",
              (request.form["account_id"], period,
               request.form["amount"], request.form.get("service_type"),
               request.form["doc_number"]),
              fetch=False)
            flash_msg = "Начисление сохранено"
            flash_type = "ok"
        except UniqueViolation:
            flash_msg = "Документ с таким номером уже введён"
            flash_type = "err"
        except Exception as e:
            flash_msg = f"Ошибка: {e}"
            flash_type = "err"

    account_id = request.args.get("account_id", type=int)
    if account_id:
        recent = q("""SELECT * FROM charges
                      WHERE account_id = %s
                      ORDER BY id DESC LIMIT 10""", (account_id,))
    else:
        recent = q("""SELECT * FROM charges
                      ORDER BY id DESC LIMIT 10""")

    return render_template("charges_form.html",
                           flash=flash_msg, flash_type=flash_type,
                           recent=recent)


from psycopg2.errors import UniqueViolation

@app.route("/payments", methods=["GET", "POST"])
def payments():
    flash_msg = ""
    flash_type = ""

    if request.method == "POST":
        period = request.form["period"] + "-01"
        try:
            q("""INSERT INTO payments
                     (account_id, period, amount, pay_date, doc_number)
                 VALUES (%s, %s, %s, %s, %s)""",
              (request.form["account_id"], period,
               request.form["amount"], request.form["pay_date"],
               request.form["doc_number"]),
              fetch=False)
            flash_msg = "Платёж сохранён"
            flash_type = "ok"
        except UniqueViolation:
            flash_msg = "Документ с таким номером уже введён"
            flash_type = "err"
        except Exception as e:
            flash_msg = f"Ошибка: {e}"
            flash_type = "err"


    account_id = request.args.get("account_id", type=int)
    if account_id:
        recent = q("""SELECT * FROM payments
                      WHERE account_id = %s
                      ORDER BY id DESC LIMIT 10""", (account_id,))
    else:
        recent = q("""SELECT * FROM payments
                      ORDER BY id DESC LIMIT 10""")

    return render_template("payments_form.html",
                           flash=flash_msg, flash_type=flash_type,
                           recent=recent)


@app.route("/saldo", methods=["GET", "POST"])
def saldo():
    flash_msg = ""
    flash_type = ""

    if request.method == "POST":
        period = request.form["period"] + "-01"
        try:
            q("""INSERT INTO saldo(account_id, period, saldo_begin, saldo_end)
                 VALUES (%s, %s, %s, %s)
                 ON CONFLICT (account_id, period) DO UPDATE
                 SET saldo_begin = EXCLUDED.saldo_begin,
                     saldo_end   = EXCLUDED.saldo_end""",
              (request.form["account_id"], period,
               request.form["saldo_begin"], request.form["saldo_end"]),
              fetch=False)
            flash_msg = "Сальдо сохранено"
            flash_type = "ok"
        except Exception as e:
            flash_msg = f"Ошибка: {e}"
            flash_type = "err"

    recent = q("""SELECT * FROM saldo ORDER BY id DESC LIMIT 10""")

    return render_template("saldo_form.html",
                           flash=flash_msg, flash_type=flash_type,
                           recent=recent)




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