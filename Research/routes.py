from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_login import login_required, current_user
import pandas as pd
import os
import re
from datetime import datetime
from werkzeug.utils import secure_filename
from models import get_db

# ✅ Import ฟังก์ชันส่งเมล
from notifications.email_service import send_alert_email

research_bp = Blueprint("research", __name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)

# ---------------------------------------------------------
# 🛠️ Helper: Smart Reader (PATCHED)
# ---------------------------------------------------------
def get_smart_df(path, sheet=None):
    raw_df = None
    try:
        if path.lower().endswith('.csv'):
            for enc in ['utf-8-sig', 'tis-620', 'cp874', 'utf-8']:
                try:
                    raw_df = pd.read_csv(path, header=None, encoding=enc, skip_blank_lines=True)
                    break
                except:
                    continue
        else:
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None)

        if raw_df is None or raw_df.empty:
            return pd.DataFrame()

        sample = raw_df.head(20)
        header_idx = sample.count(axis=1).idxmax()
        if header_idx == 0:
            for i in range(len(sample)):
                filled = sample.iloc[i].notna().sum()
                if filled >= len(sample.columns) * 0.5:
                    header_idx = i
                    break
        df = raw_df.iloc[header_idx:].reset_index(drop=True)

        clean_cols = []
        for c in df.iloc[0]:
            c_str = re.sub(r'\s+', ' ', str(c)).strip()
            if not c_str or "Unnamed" in c_str or c_str.lower() == "nan":
                clean_cols.append(f"Field_{len(clean_cols)+1}")
            else:
                clean_cols.append(c_str)

        df.columns = clean_cols
        df = df.iloc[1:]
        df = df.dropna(how='all').fillna("")

        try:
            df = df.map(lambda x: str(x).strip() if x is not None else "")
        except AttributeError:
            df = df.applymap(lambda x: str(x).strip() if x is not None else "")

        # 🔥 FINAL NORMALIZATION PATCH
        df.columns = (
            df.columns.astype(str)
            .str.replace('\n', ' ')
            .str.replace('\r', ' ')
            .str.replace(r'\s+', ' ', regex=True)
            .str.strip()
        )

        return df

    except Exception as e:
        print(f"Smart Reader Error: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# 🚀 Routes
# ---------------------------------------------------------

@research_bp.route("/")
@login_required
def landing():
    conn = get_db()
    try:
        deadlines = conn.execute("SELECT deadline FROM research_projects").fetchall()
    except:
        deadlines = []
    conn.close()

    today = datetime.today().date()
    on_track = near_deadline = overdue = 0
    next_deadline = None

    for row in deadlines:
        dt = pd.to_datetime(row['deadline'], errors="coerce")
        if pd.isna(dt):
            continue
        days_left = (dt.date() - today).days

        if days_left < 0:
            overdue += 1
        elif days_left <= 7:
            near_deadline += 1
        else:
            on_track += 1

        if days_left >= 0:
            next_deadline = days_left if next_deadline is None else min(next_deadline, days_left)

    return render_template("research/index.html",
                           total=len(deadlines),
                           on_track=on_track,
                           near_deadline=near_deadline,
                           overdue=overdue,
                           next_deadline=next_deadline,
                           sheets=session.get("sheets"),
                           columns=session.get("columns"),
                           rows=session.get("rows"),
                           active_sheet=session.get("active_sheet"))

@research_bp.route("/upload", methods=["POST"])
@login_required
def upload():
    file = request.files.get("file")
    if not file or file.filename == '':
        flash('กรุณาเลือกไฟล์ก่อนอัปโหลด', 'warning')
        return redirect(url_for("research.landing"))

    filename = secure_filename(file.filename)
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)

    try:
        if filename.lower().endswith(('.xlsx', '.xls')):
            xl = pd.ExcelFile(path)
            session["sheets"] = xl.sheet_names
        else:
            session["sheets"] = ["CSV_File"]

        session["excel_path"] = path
        flash('อัปโหลดไฟล์สำเร็จ! กรุณาเลือก Sheet ที่ต้องการ', 'success')
    except Exception as e:
        flash(f'ไฟล์มีปัญหา: {e}', 'danger')

    return redirect(url_for("research.landing"))

@research_bp.route("/preview-sheet", methods=["POST"])
@login_required
def preview_sheet():
    sheet = request.form.get("sheet")
    path = session.get("excel_path")
    if not path:
        return redirect(url_for("research.landing"))

    df = get_smart_df(path, sheet)
    if not df.empty:
        session["columns"] = df.columns.tolist()
        session["rows"] = df.head(15).values.tolist()
        session["active_sheet"] = sheet
        flash(f'โหลดข้อมูลจาก Sheet: {sheet} เรียบร้อย', 'info')
    else:
        flash('ไม่พบข้อมูลใน Sheet ที่เลือก', 'warning')

    return redirect(url_for("research.landing"))

@research_bp.route("/map-columns", methods=["POST"])
@login_required
def map_columns():
    fields = ["project_th", "project_en", "researcher_name", "researcher_email", "affiliation", "funding", "deadline"]
    mapping = {f: request.form.get(f) for f in fields}

    # 🛑 MAPPING VALIDATION PATCH
    if not any(mapping.values()):
        flash("กรุณาเลือกอย่างน้อย 1 field สำหรับ mapping", "warning")
        return redirect(url_for("research.landing"))

    path, sheet = session.get("excel_path"), session.get("active_sheet")
    df = get_smart_df(path, sheet)

    if df.empty:
        return redirect(url_for("research.landing"))

    conn = get_db()
    count = 0

    for _, r in df.iterrows():
        try:
            fund = 0
            f_col = mapping.get("funding")
            if f_col and f_col in r:
                clean_f = re.sub(r'[^\d.]', '', str(r[f_col]))
                fund = float(clean_f) if clean_f else 0

            dl_str = ""
            d_col = mapping.get("deadline")
            if d_col and d_col in r:
                dt = pd.to_datetime(r[d_col], errors="coerce")
                if not pd.isna(dt):
                    dl_str = dt.strftime("%Y-%m-%d")

            email_val = ""
            e_col = mapping.get("researcher_email")
            if e_col and e_col in r:
                email_val = str(r[e_col]).strip()

            conn.execute("""INSERT INTO research_projects
                (project_th, project_en, researcher_name, researcher_email, affiliation, funding, deadline)
                VALUES (?,?,?,?,?,?,?)""",
                (str(r.get(mapping.get("project_th"), "")),
                 str(r.get(mapping.get("project_en"), "")),
                 str(r.get(mapping.get("researcher_name"), "")),
                 email_val,
                 str(r.get(mapping.get("affiliation"), "")),
                 fund, dl_str))

            count += 1
        except Exception as e:
            print("Insert error:", e, r)
            continue

    conn.commit()
    conn.close()

    session.pop("sheets", None)
    session.pop("columns", None)
    session.pop("rows", None)

    flash(f'บันทึกข้อมูลสำเร็จ {count} รายการ!', 'success')
    return redirect(url_for("research.landing"))
