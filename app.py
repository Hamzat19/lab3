from flask import Flask, render_template, request, redirect, url_for, flash
from db import q
from psycopg2.errors import UniqueViolation
import re
from io import BytesIO
import openpyxl

app = Flask(__name__)
app.secret_key = "lab3-secret"


# ---------- Главная ----------

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


# ---------- Начисления ----------

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


# ---------- Платежи ----------

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


# ---------- Сальдо ----------

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

    recent = q("SELECT * FROM saldo ORDER BY id DESC LIMIT 10")

    return render_template("saldo_form.html",
                           flash=flash_msg, flash_type=flash_type,
                           recent=recent)


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


# ---------- Загрузка выписки из Excel ----------

@app.route("/payments/upload", methods=["GET"])
def payments_upload_form():
    return render_template("payments_upload.html")


def extract_account_id(purpose: str):
    """Пытается вытащить номер квартиры из назначения платежа."""
    if not purpose:
        return None
    patterns = [
        r'квартира\s+(\d+)',
        r'\bкв[\s\.]*(\d+)',
        r'л[\s/\.]*с[\s\.]*(\d+)',
        r'лс[\s\.]*(\d+)',
    ]
    for pat in patterns:
        m = re.search(pat, purpose, re.IGNORECASE)
        if m:
            return int(m.group(1))
    return None


@app.route("/payments/upload", methods=["POST"])
def payments_upload_parse():
    file = request.files.get("file")
    if not file or file.filename == "":
        flash("Файл не выбран", "err")
        return redirect(url_for("payments_upload_form"))

    data = file.read()

    try:
        wb = openpyxl.load_workbook(BytesIO(data), data_only=True, read_only=True)
        ws = wb.active
    except Exception as e:
        flash(f"Не удалось прочитать файл: {e}", "err")
        return redirect(url_for("payments_upload_form"))

    existing = {row["doc_number"] for row in
                q("SELECT doc_number FROM payments WHERE doc_number IS NOT NULL")}

    parsed = []
    skipped_no_account = 0
    skipped_no_doc = 0
    errors = []
    MAX_ROWS = 500

    # Индексы колонок в листе выписки Сбербизнеса:
    # 1  — Дата проводки
    # 13 — Сумма по кредиту
    # 14 — № документа
    # 19 — Назначение платежа
    COL_DATE    = 1
    COL_AMOUNT  = 13
    COL_DOC     = 14
    COL_PURPOSE = 20

    row_num = 0
    for i, row in enumerate(ws.iter_rows(min_row=12, values_only=True), start=12):
        row_num = i
        if len(parsed) >= MAX_ROWS:
            break



        try:
            pay_date = row[COL_DATE]
            amount   = row[COL_AMOUNT]
            doc_num  = row[COL_DOC]
            purpose  = row[COL_PURPOSE]

            # пропускаем строки без даты или суммы
            if not pay_date or not amount:
                continue

            if not doc_num:
                skipped_no_doc += 1
                continue

            # ищем номер квартиры
            account_id = extract_account_id(str(purpose) if purpose else "")
            if account_id is None:
                skipped_no_account += 1
                continue

            period = pay_date.strftime("%Y-%m-01")
            status = "duplicate" if str(doc_num) in existing else "new"

            parsed.append({
                "row":        i,
                "pay_date":   pay_date.strftime("%Y-%m-%d"),
                "period":     period,
                "amount":     float(amount),
                "doc_number": str(doc_num),
                "account_id": account_id,
                "purpose":    str(purpose) if purpose else "",
                "status":     status,
            })
        except Exception as e:
            errors.append(f"Строка {i}: {e}")

    if not parsed:
        flash(f"Не найдено ни одной подходящей строки. "
              f"Всего просмотрено строк: {row_num - 11}. "
              f"Пропущено без квартиры: {skipped_no_account}, "
              f"без № документа: {skipped_no_doc}. "
              f"Ошибок: {len(errors)}. "
              + ("Первые ошибки: " + "; ".join(errors[:3]) if errors else ""),
              "err")
        return redirect(url_for("payments_upload_form"))

    return render_template("payments_upload_preview.html",
                           parsed=parsed,
                           skipped_no_account=skipped_no_account,
                           skipped_no_doc=skipped_no_doc,
                           errors=errors)


@app.route("/payments/upload/confirm", methods=["POST"])
def payments_upload_confirm():
    inserted = 0
    skipped = 0

    for key in request.form:
        if not key.startswith("row_"):
            continue
        idx = key[4:]
        account_id = request.form.get(f"account_id_{idx}")
        amount     = request.form.get(f"amount_{idx}")
        pay_date   = request.form.get(f"pay_date_{idx}")
        period     = request.form.get(f"period_{idx}")
        doc_number = request.form.get(f"doc_number_{idx}")

        if not account_id or not amount or not pay_date or not doc_number:
            continue

        try:
            q("""INSERT INTO payments
                     (account_id, period, amount, pay_date, doc_number)
                 VALUES (%s, %s, %s, %s, %s)
                 ON CONFLICT (doc_number) DO NOTHING""",
              (int(account_id), period, float(amount),
               pay_date, doc_number),
              fetch=False)
            inserted += 1
        except Exception:
            skipped += 1

    flash(f"Загружено: {inserted}. Пропущено (дубли): {skipped}.", "ok")
    return redirect(url_for("payments"))


if __name__ == "__main__":
    app.run(debug=True)