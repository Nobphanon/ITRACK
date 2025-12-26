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
# 🛠️ Helper: Smart Reader (ตัวอ่านไฟล์อัจฉริยะ)
# ---------------------------------------------------------
def get_smart_df(path, sheet=None):
    raw_df = None
    try:
        if path.lower().endswith('.csv'):
            for enc in ['utf-8-sig', 'tis-620', 'cp874', 'utf-8']:
                try:
                    raw_df = pd.read_csv(path, header=None, encoding=enc, skip_blank_lines=True)
                    break
                except: continue
        else:
            raw_df = pd.read_excel(path, sheet_name=sheet, header=None)

        if raw_df is None or raw_df.empty: return pd.DataFrame()

        sample = raw_df.head(20)
        header_idx = sample.count(axis=1).idxmax()
        
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
        df = df.applymap(lambda x: str(x).strip() if x is not None else "")
        return df
    except Exception as e:
        print(f"Smart Reader Error: {e}")
        return pd.DataFrame()

# ---------------------------------------------------------
# 🚀 Routes (เส้นทางระบบ)
# ---------------------------------------------------------

@research_bp.route("/")
@login_required 
def landing():
    conn = get_db()
    deadlines = conn.execute("SELECT deadline FROM research_projects").fetchall()
    conn.close()

    today = datetime.today().date()
    on_track = near_deadline = overdue = 0
    next_deadline = None

    for row in deadlines:
        dt = pd.to_datetime(row['deadline'], errors="coerce")
        if pd.isna(dt): continue
        days_left = (dt.date() - today).days
        
        if days_left < 0: overdue += 1
        elif days_left <= 7: near_deadline += 1
        else: on_track += 1
        
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
    if not path: return redirect(url_for("research.landing"))
    
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
    # ✅ 1. เพิ่ม researcher_email กลับเข้ามาในรายการ Fields
    fields = ["project_th","project_en","researcher_name","researcher_email","affiliation","funding","deadline"]
    mapping = {f: request.form.get(f) for f in fields}
    
    path, sheet = session.get("excel_path"), session.get("active_sheet")
    df = get_smart_df(path, sheet)
    
    if df.empty: return redirect(url_for("research.landing"))
    
    conn = get_db()
    count = 0
    for _, r in df.iterrows():
        try:
            # Clean Funding
            fund = 0
            f_col = mapping.get("funding")
            if f_col and f_col in r:
                clean_f = re.sub(r'[^\d.]', '', str(r[f_col]))
                fund = float(clean_f) if clean_f else 0

            # Clean Deadline
            dl_str = ""
            d_col = mapping.get("deadline")
            if d_col and d_col in r:
                dt = pd.to_datetime(r[d_col], errors="coerce")
                if not pd.isna(dt): dl_str = dt.strftime("%Y-%m-%d")

            # ✅ 2. ดึงอีเมลจากคอลัมน์ Excel
            email_val = ""
            e_col = mapping.get("researcher_email")
            if e_col and e_col in r:
                email_val = str(r[e_col]).strip()

            # Insert
            conn.execute("""INSERT INTO research_projects 
                (project_th, project_en, researcher_name, researcher_email, affiliation, funding, deadline) 
                VALUES (?,?,?,?,?,?,?)""", 
                (str(r.get(mapping.get("project_th"), "")), 
                 str(r.get(mapping.get("project_en"), "")),
                 str(r.get(mapping.get("researcher_name"), "")), 
                 email_val, # บันทึกอีเมลที่อ่านจาก Excel
                 str(r.get(mapping.get("affiliation"), "")), 
                 fund, dl_str))
            count += 1
        except Exception as e:
            print(f"Skip row: {e}")
            continue

    conn.commit()
    conn.close()
    
    session.pop("sheets", None)
    session.pop("columns", None)
    session.pop("rows", None)
    
    flash(f'บันทึกข้อมูลสำเร็จ {count} รายการ!', 'success')
    return redirect(url_for("research.landing"))

@research_bp.route("/dashboard")
@login_required
def dashboard():
    q = request.args.get("q", "")
    aff_filter = request.args.get("aff", "")
    status_filter = request.args.get("status", "")
    
    conn = get_db()
    sql = "SELECT * FROM research_projects WHERE 1=1"
    params = []
    
    if q:
        sql += " AND (project_th LIKE ? OR project_en LIKE ? OR researcher_name LIKE ?)"
        wildcard = f"%{q}%"
        params.extend([wildcard, wildcard, wildcard])
        
    if aff_filter:
        sql += " AND affiliation = ?"
        params.append(aff_filter)
        
    rows = conn.execute(sql, params).fetchall()
    
    aff_list = [row[0] for row in conn.execute("SELECT DISTINCT affiliation FROM research_projects WHERE affiliation != ''").fetchall()]
    conn.close()
    
    today = datetime.today().date()
    processed_projects = []
    
    for row in rows:
        p = dict(row)
        p['status_text'] = 'On Track'
        
        if p['deadline']:
            try:
                dt = pd.to_datetime(p['deadline'], errors='coerce')
                if not pd.isna(dt):
                    days_left = (dt.date() - today).days
                    if days_left < 0:
                        p['status_text'] = 'Overdue'
                    elif days_left <= 7:
                        p['status_text'] = 'Near Deadline'
            except: pass
        
        if status_filter and p['status_text'] != status_filter:
            continue
            
        processed_projects.append(p)
    
    return render_template("research/dashboard.html", 
                           projects=processed_projects, 
                           total=len(processed_projects), 
                           aff_list=aff_list, 
                           q=q, 
                           aff_filter=aff_filter, 
                           status_filter=status_filter)

@research_bp.route("/clear-all", methods=["POST"])
@login_required
def clear_all():
    if current_user.role != "admin":
        flash("สิทธิ์ของคุณไม่เพียงพอ", "danger")
        return redirect(url_for("research.dashboard"))

    conn = get_db()
    conn.execute("DELETE FROM research_projects")
    conn.commit()
    conn.close()
    flash("ล้างข้อมูลทั้งหมดเรียบร้อยแล้ว", "success")
    return redirect(url_for("research.dashboard"))

@research_bp.route("/delete/<int:pid>", methods=["POST"])
@login_required
def delete_project(pid):
    try:
        conn = get_db()
        conn.execute("DELETE FROM research_projects WHERE id = ?", (pid,))
        conn.commit()
        conn.close()
        flash('ลบโครงการเรียบร้อยแล้ว', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาดในการลบ: {e}', 'danger')
        
    return redirect(url_for("research.dashboard"))

# ✅ เพิ่ม Route ส่งแจ้งเตือน (ที่หายไป) กลับเข้ามา
@research_bp.route("/send-alert/<int:pid>", methods=["POST"])
@login_required
def send_project_alert(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM research_projects WHERE id = ?", (pid,)).fetchone()
    conn.close()

    if not row:
        flash("ไม่พบข้อมูลโครงการ", "danger")
        return redirect(url_for("research.dashboard"))

    # คำนวณวันเหลืออีกรอบ
    today = datetime.today().date()
    days_left = "ไม่ระบุ"
    if row['deadline']:
        try:
            dt = pd.to_datetime(row['deadline'])
            days_left = (dt.date() - today).days
        except: pass

    # เรียกใช้ฟังก์ชันส่งเมล
    if row['researcher_email']:
        # ส่งเมลหาเจ้าของโครงการนั้นๆ
        send_alert_email(row['researcher_email'], row['project_th'], days_left)
        flash(f"กำลังส่งอีเมลแจ้งเตือนไปยัง {row['researcher_email']}...", "success")
    else:
        flash("โครงการนี้ไม่มีข้อมูลอีเมล (กรุณาตรวจสอบไฟล์ Excel)", "warning")

    return redirect(url_for("research.dashboard"))