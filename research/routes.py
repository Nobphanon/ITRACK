from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_login import login_required, current_user
import pandas as pd
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models import get_db
from services.excel_service import get_smart_df

# ✅ Import ฟังก์ชันส่งเมล
from notifications.email_service import send_alert_email
import re
from audit.service import log_project_action, log_action

research_bp = Blueprint("research", __name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------
# 🚀 Routes
# ---------------------------------------------------------

@research_bp.route("/")
@login_required
def landing():
    conn = get_db()
    
    # Fetch all projects for display and analytics
    try:
        projects = conn.execute("""
            SELECT id, project_th, researcher_name, researcher_email, 
                   affiliation, funding, deadline, start_date, end_date, status
            FROM research_projects
            ORDER BY deadline ASC
        """).fetchall()
    except:
        projects = []
    
    today = datetime.today().date()
    on_track = near_deadline = overdue = 0
    next_deadline = None
    
    # Status counts for chart
    status_counts = {'draft': 0, 'in_progress': 0, 'under_review': 0, 'completed': 0}
    
    # Funding by affiliation for chart
    funding_by_affiliation = {}
    total_funding = 0
    
    project_list = []
    
    for row in projects:
        # Calculate deadline status
        deadline_status = 'no_deadline'
        days_left = None
        
        if row['deadline']:
            dt = pd.to_datetime(row['deadline'], errors="coerce")
            if not pd.isna(dt):
                days_left = (dt.date() - today).days
                
                if days_left < 0:
                    overdue += 1
                    deadline_status = 'overdue'
                elif days_left <= 7:
                    near_deadline += 1
                    deadline_status = 'near_deadline'
                else:
                    on_track += 1
                    deadline_status = 'on_track'
                
                if days_left >= 0:
                    next_deadline = days_left if next_deadline is None else min(next_deadline, days_left)
        
        # Count by status
        status = row['status'] or 'draft'
        if status in status_counts:
            status_counts[status] += 1
        else:
            status_counts['draft'] += 1
        
        # Sum funding by affiliation
        affiliation = row['affiliation'] or 'ไม่ระบุ'
        funding = row['funding'] or 0
        funding_by_affiliation[affiliation] = funding_by_affiliation.get(affiliation, 0) + funding
        total_funding += funding
        
        # Build project list for display
        project_list.append({
            'id': row['id'],
            'project_th': row['project_th'] or '-',
            'researcher_name': row['researcher_name'] or '-',
            'affiliation': affiliation,
            'funding': funding,
            'deadline': row['deadline'],
            'days_left': days_left,
            'deadline_status': deadline_status,
            'status': status
        })
    
    return render_template("research/index.html",
                           total=len(projects),
                           on_track=on_track,
                           near_deadline=near_deadline,
                           overdue=overdue,
                           next_deadline=next_deadline,
                           total_funding=total_funding,
                           status_counts=status_counts,
                           funding_by_affiliation=funding_by_affiliation,
                           project_list=project_list,
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
        if filename.lower().endswith('.xls'):
            xl = pd.ExcelFile(path, engine='xlrd')
        elif filename.lower().endswith('.xlsx'):
            xl = pd.ExcelFile(path, engine='openpyxl')
        else:
            xl = None
            session["sheets"] = ["CSV_File"]
            session["excel_path"] = path  # ✅ FIX: Save path for CSV files too

        if xl:
            session["sheets"] = xl.sheet_names
            session["excel_path"] = path  # ✅ FIX: Save path after successful Excel read
            
    except Exception as e:
        print(f"⚠️ Error reading sheets: {e}")
        # 🔧 Attempt Auto-Repair
        from services.excel_service import repair_excel
        repaired_path = repair_excel(path)
        
        if repaired_path:
             try:
                 xl = pd.ExcelFile(repaired_path, engine='openpyxl')
                 session["sheets"] = xl.sheet_names
                 session["excel_path"] = repaired_path # Update to use repaired file
                 flash('ระบบได้ทำการซ่อมแซมไฟล์และอ่านข้อมูลสำเร็จ', 'success')
                 return redirect(url_for("research.landing"))
             except Exception as e2:
                 flash(f'ไม่สามารถอ่านไฟล์ได้แม้จะซ่อมแซมแล้ว: {e2}', 'danger')
        else:
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

def parse_date(val):
    """
    Robust date parser handling Thai years, various separators, and formats.
    Returns: YYYY-MM-DD string or empty string.
    """
    if not val or pd.isna(val) or str(val).strip() == "":
        return ""
        
    s = str(val).strip()
    
    # Try pandas parsing first (handles standard formats)
    try:
        dt = pd.to_datetime(s, dayfirst=True, errors='coerce')
        if not pd.isna(dt):
            # Check for Thai year (e.g., 2567 -> 2024)
            if dt.year > 2400:
                dt = dt.replace(year=dt.year - 543)
            return dt.strftime("%Y-%m-%d")
    except:
        pass

    return ""

@research_bp.route("/map-columns", methods=["POST"])
@login_required
def map_columns():
    fields = ["project_th", "project_en", "researcher_name", "researcher_email", "affiliation", "funding", "deadline", "start_date", "end_date"]
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
                # import re moved to top
                clean_f = re.sub(r'[^\d.]', '', str(r[f_col]))
                fund = float(clean_f) if clean_f else 0

            # Date Fields
            deadline_str = ""
            if mapping.get("deadline") in r:
                deadline_str = parse_date(r[mapping.get("deadline")])
                
            start_str = ""
            if mapping.get("start_date") in r:
                start_str = parse_date(r[mapping.get("start_date")])

            end_str = ""
            if mapping.get("end_date") in r:
                end_str = parse_date(r[mapping.get("end_date")])

            email_val = ""
            e_col = mapping.get("researcher_email")
            if e_col and e_col in r:
                email_val = str(r[e_col]).strip()

            conn.execute("""INSERT INTO research_projects
                (project_th, project_en, researcher_name, researcher_email, affiliation, funding, deadline, start_date, end_date)
                VALUES (?,?,?,?,?,?,?,?,?)""",
                (str(r.get(mapping.get("project_th"), "")),
                 str(r.get(mapping.get("project_en"), "")),
                 str(r.get(mapping.get("researcher_name"), "")),
                 email_val,
                 str(r.get(mapping.get("affiliation"), "")),
                 fund, deadline_str, start_str, end_str))

            count += 1
        except Exception as e:
            print("Insert error:", e, r)
            continue

    conn.commit()
    # conn.close()

    session.pop("sheets", None)
    session.pop("columns", None)
    session.pop("rows", None)

    log_project_action("PROJECTS_IMPORTED", details=f"Imported {count} projects")
    flash(f'บันทึกข้อมูลสำเร็จ {count} รายการ!', 'success')
    return redirect(url_for("research.landing"))

# ---------------------------------------------------------
# 📊 Dashboard & Management Routes
# ---------------------------------------------------------

@research_bp.route("/dashboard")
@login_required
def dashboard():
    conn = get_db()
    
    # Filters
    q = request.args.get("q", "").strip()
    aff = request.args.get("aff", "").strip()
    status = request.args.get("status", "").strip()

    # Base Query
    sql = "SELECT * FROM research_projects WHERE 1=1"
    params = []

    if q:
        sql += " AND (project_th LIKE ? OR researcher_name LIKE ? OR affiliation LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    
    if aff:
        sql += " AND affiliation = ?"
        params.append(aff)

    rows = conn.execute(sql, params).fetchall()
    
    # Get distinct affiliations for filter
    aff_rows = conn.execute("SELECT DISTINCT affiliation FROM research_projects WHERE affiliation != '' ORDER BY affiliation").fetchall()
    aff_list = [r['affiliation'] for r in aff_rows]
    
    today = datetime.today().date()
    projects = []
    
    for r in rows:
        p = dict(r)
        
        # Calculate Status
        dt = pd.to_datetime(p['deadline'], errors="coerce")
        days_left = None
        status_text = "Unknown"
        
        if not pd.isna(dt):
            days_left = (dt.date() - today).days
            if days_left < 0:
                status_text = "Overdue"
            elif days_left <= 7:
                status_text = "Near Deadline"
            else:
                status_text = "On Track"
        
        # Status Filter
        if status and status != status_text:
            continue
            
        p['status_text'] = status_text
        projects.append(p)

    return render_template("research/dashboard.html",
                           projects=projects,
                           total=len(projects),
                           q=q,
                           aff=aff,
                           status_filter=status,
                           aff_list=aff_list)

@research_bp.route("/delete/<int:pid>", methods=["POST"])
@login_required
def delete_project(pid):
    conn = get_db()
    # Get project name before deleting for audit log
    project = conn.execute("SELECT project_th FROM research_projects WHERE id = ?", (pid,)).fetchone()
    project_name = project['project_th'] if project else 'Unknown'
    
    conn.execute("DELETE FROM research_projects WHERE id = ?", (pid,))
    conn.commit()
    log_project_action("PROJECT_DELETED", project_id=pid, details=f"Deleted: {project_name}")
    flash("ลบโครงการเรียบร้อยแล้ว", "success")
    return redirect(url_for("research.dashboard"))

@research_bp.route("/clear-all", methods=["POST"])
@login_required
def clear_all():
    # Admin only check
    if current_user.role != 'admin':
        flash("คุณไม่มีสิทธิ์ในการดำเนินการนี้", "danger")
        return redirect(url_for("research.dashboard"))
    
    conn = get_db()
    # Get count before clearing for audit
    count = conn.execute("SELECT COUNT(*) as cnt FROM research_projects").fetchone()['cnt']
    conn.execute("DELETE FROM research_projects")
    conn.commit()
    log_action("DATA_CLEARED", target_type="project", details=f"Cleared {count} projects")
    flash("ล้างข้อมูลทั้งหมดเรียบร้อยแล้ว", "warning")
    return redirect(url_for("research.dashboard"))

@research_bp.route("/alert/<int:pid>", methods=["POST"])
@login_required
def send_project_alert(pid):
    conn = get_db()
    row = conn.execute("SELECT * FROM research_projects WHERE id = ?", (pid,)).fetchone()
    
    if row and row['researcher_email']:
        # Mock calculation of days left
        days_left = 0
        dt = pd.to_datetime(row['deadline'], errors="coerce")
        if not pd.isna(dt):
             days_left = (dt.date() - datetime.today().date()).days
        
        success, msg = send_alert_email(row['researcher_email'], row['project_th'], days_left)
        if success:
            flash(f"ส่งเมลแจ้งเตือนไปยัง {row['researcher_email']} แล้ว", "success")
        else:
            flash(f"ส่งเมลไม่สำเร็จ: {msg}", "danger")
    else:
        flash("ไม่พบข้อมูลอีเมลหรือโครงการ", "warning")
        
    return redirect(url_for("research.dashboard"))

# ---------------------------------------------------------
# 📝 Edit Project
# ---------------------------------------------------------

@research_bp.route("/edit/<int:pid>", methods=["GET", "POST"])
@login_required
def edit_project(pid):
    conn = get_db()
    
    if request.method == "POST":
        # Update project data
        conn.execute("""
            UPDATE research_projects SET
                project_th = ?,
                project_en = ?,
                researcher_name = ?,
                researcher_email = ?,
                affiliation = ?,
                funding = ?,
                start_date = ?,
                end_date = ?,
                deadline = ?,
                status = ?
            WHERE id = ?
        """, (
            request.form.get('project_th', ''),
            request.form.get('project_en', ''),
            request.form.get('researcher_name', ''),
            request.form.get('researcher_email', ''),
            request.form.get('affiliation', ''),
            float(request.form.get('funding') or 0),
            request.form.get('start_date', ''),
            request.form.get('end_date', ''),
            request.form.get('deadline', ''),
            request.form.get('status', 'draft'),
            pid
        ))
        conn.commit()
        log_project_action("PROJECT_UPDATED", project_id=pid, details=f"Updated: {request.form.get('project_th', '')}")
        flash("บันทึกการแก้ไขเรียบร้อยแล้ว", "success")
        return redirect(url_for("research.dashboard"))
    
    # GET - Show edit form
    project = conn.execute("SELECT * FROM research_projects WHERE id = ?", (pid,)).fetchone()
    if not project:
        flash("ไม่พบโครงการที่ต้องการแก้ไข", "warning")
        return redirect(url_for("research.dashboard"))
    
    return render_template("research/edit.html", project=project)

