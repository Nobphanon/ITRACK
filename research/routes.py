from flask import Blueprint, render_template, request, redirect, url_for, session, flash, current_app
from flask_login import login_required, current_user
import pandas as pd
import os
from datetime import datetime
from werkzeug.utils import secure_filename
from models import get_db
from database import IS_POSTGRES
from services.excel_service import get_smart_df

# ✅ Import ฟังก์ชันส่งเมล
from notifications.email_service import send_alert_email
import re
from audit.service import log_project_action, log_action

# ✅ Import permissions
from permissions import manager_required, can_manage_projects

research_bp = Blueprint("research", __name__)
UPLOAD_FOLDER = "uploads"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


# ---------------------------------------------------------
# 🚀 Routes
# ---------------------------------------------------------

@research_bp.route("/")
@login_required
def landing():
    # Redirect Researcher to their own dashboard
    if current_user.role == 'researcher':
        return redirect(url_for('researcher.dashboard'))
    
    conn = get_db()
    
    # Get year filter from request
    selected_year = request.args.get('year', 'all')
    
    # Get list of available years - use different SQL for PostgreSQL
    try:
        if IS_POSTGRES:
            # PostgreSQL uses EXTRACT function
            years_result = conn.execute("""
                SELECT DISTINCT EXTRACT(YEAR FROM start_date::DATE)::TEXT as year 
                FROM research_projects 
                WHERE start_date IS NOT NULL AND start_date != ''
                UNION
                SELECT DISTINCT EXTRACT(YEAR FROM deadline::DATE)::TEXT as year 
                FROM research_projects 
                WHERE deadline IS NOT NULL AND deadline != ''
                ORDER BY year DESC
            """).fetchall()
        else:
            # SQLite uses strftime
            years_result = conn.execute("""
                SELECT DISTINCT strftime('%Y', start_date) as year 
                FROM research_projects 
                WHERE start_date IS NOT NULL AND start_date != ''
                UNION
                SELECT DISTINCT strftime('%Y', deadline) as year 
                FROM research_projects 
                WHERE deadline IS NOT NULL AND deadline != ''
                ORDER BY year DESC
            """).fetchall()
        years_list = [r['year'] for r in years_result if r['year']]
    except:
        years_list = []
    
    # Fetch projects with optional year filter
    try:
        if selected_year != 'all' and selected_year:
            if IS_POSTGRES:
                projects = conn.execute("""
                    SELECT id, project_th, researcher_name, researcher_email, 
                           affiliation, funding, deadline, start_date, end_date, status
                    FROM research_projects
                    WHERE EXTRACT(YEAR FROM start_date::DATE)::TEXT = ? 
                       OR EXTRACT(YEAR FROM deadline::DATE)::TEXT = ?
                    ORDER BY deadline ASC
                """, (selected_year, selected_year)).fetchall()
            else:
                projects = conn.execute("""
                    SELECT id, project_th, researcher_name, researcher_email, 
                           affiliation, funding, deadline, start_date, end_date, status
                    FROM research_projects
                    WHERE strftime('%Y', start_date) = ? OR strftime('%Y', deadline) = ?
                    ORDER BY deadline ASC
                """, (selected_year, selected_year)).fetchall()
        else:
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
                           years_list=years_list,
                           selected_year=selected_year,
                           sheets=session.get("sheets"),
                           columns=session.get("columns"),
                           rows=session.get("rows"),
                           active_sheet=session.get("active_sheet"))

@research_bp.route("/upload", methods=["POST"])
@login_required
@manager_required
def upload():
    print("📁 Upload route called!")
    file = request.files.get("file")
    if not file or file.filename == '':
        print("❌ No file provided")
        flash('กรุณาเลือกไฟล์ก่อนอัปโหลด', 'warning')
        return redirect(url_for("research.landing"))

    filename = secure_filename(file.filename)
    print(f"📄 File received: {filename}")
    path = os.path.join(UPLOAD_FOLDER, filename)
    file.save(path)
    print(f"💾 File saved to: {path}")
    
    sheets = []
    error_msg = None

    try:
        if filename.lower().endswith('.csv'):
            sheets = ["CSV_File"]
            session["excel_path"] = path
        elif filename.lower().endswith('.xls'):
            # Old Excel format
            try:
                xl = pd.ExcelFile(path, engine='xlrd')
                sheets = xl.sheet_names
            except Exception as e1:
                error_msg = f"xlrd error: {e1}"
        else:
            # .xlsx format - try multiple methods
            try:
                xl = pd.ExcelFile(path, engine='openpyxl')
                sheets = xl.sheet_names
            except Exception as e1:
                error_msg = f"openpyxl error: {e1}"
                # Fallback: try without specifying engine
                try:
                    xl = pd.ExcelFile(path)
                    sheets = xl.sheet_names
                    error_msg = None
                except Exception as e2:
                    error_msg = f"Fallback error: {e2}"

        if sheets:
            session["sheets"] = sheets
            session["excel_path"] = path
            flash(f'อัปโหลดสำเร็จ! พบ {len(sheets)} sheet(s): {", ".join(sheets[:5])}', 'success')
        else:
            # Try repair
            from services.excel_service import repair_excel
            repaired_path = repair_excel(path)
            
            if repaired_path:
                try:
                    xl = pd.ExcelFile(repaired_path, engine='openpyxl')
                    session["sheets"] = xl.sheet_names
                    session["excel_path"] = repaired_path
                    flash(f'ซ่อมแซมไฟล์สำเร็จ! พบ {len(xl.sheet_names)} sheet(s)', 'success')
                except Exception as e:
                    flash(f'ไม่สามารถอ่านได้แม้ซ่อมแซมแล้ว: {e}', 'danger')
            else:
                flash(f'ไม่สามารถอ่านไฟล์ได้: {error_msg}', 'danger')
                
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')

    return redirect(url_for("research.landing"))

@research_bp.route("/preview-sheet", methods=["POST"])
@login_required
@manager_required
def preview_sheet():
    import sys
    import json
    print("=" * 50, flush=True)
    print("📊 Preview sheet route called!", flush=True)
    sheet = request.form.get("sheet")
    path = session.get("excel_path")
    print(f"📄 Sheet: {sheet}", flush=True)
    print(f"📄 Path: {path}", flush=True)
    
    if not path:
        print("❌ No path in session", flush=True)
        flash('กรุณาอัปโหลดไฟล์ก่อน', 'warning')
        return redirect(url_for("research.landing"))

    try:
        print(f"🔍 Reading sheet...", flush=True)
        df = get_smart_df(path, sheet)
        print(f"📊 DataFrame shape: {df.shape if not df.empty else 'EMPTY'}", flush=True)
        
        if not df.empty:
            cols = df.columns.tolist()
            # Only store first 5 rows to keep session small!
            rows = df.head(5).values.tolist()
            
            session["columns"] = cols
            session["active_sheet"] = sheet
            
            # Save full preview data to temp file instead of session
            preview_data = {
                "columns": cols,
                "rows": df.head(15).values.tolist()
            }
            preview_path = os.path.join(UPLOAD_FOLDER, "preview_data.json")
            with open(preview_path, 'w', encoding='utf-8') as f:
                json.dump(preview_data, f, ensure_ascii=False, default=str)
            session["preview_path"] = preview_path
            
            # Store minimal rows in session for quick display
            session["rows"] = rows
            
            print(f"✅ Loaded {len(df)} rows, {len(cols)} columns", flush=True)
            flash(f'โหลดข้อมูลจาก Sheet: {sheet} สำเร็จ! ({len(df)} แถว, {len(cols)} คอลัมน์)', 'success')
        else:
            print("⚠️ DataFrame is empty", flush=True)
            flash('ไม่พบข้อมูลใน Sheet ที่เลือก', 'warning')
    except Exception as e:
        print(f"❌ Error reading sheet: {e}", flush=True)
        import traceback
        traceback.print_exc()
        flash(f'เกิดข้อผิดพลาดในการอ่าน Sheet: {str(e)}', 'danger')

    print("=" * 50, flush=True)
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
@manager_required
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
@manager_required
def dashboard():
    conn = get_db()
    
    # Filters
    q = request.args.get("q", "").strip()
    aff = request.args.get("aff", "").strip()
    status = request.args.get("status", "").strip()

    # Base Query - join with users to get assigned researcher info
    sql = """SELECT rp.*, u.username as assigned_researcher_name 
             FROM research_projects rp 
             LEFT JOIN users u ON rp.assigned_researcher_id = u.id 
             WHERE 1=1"""
    params = []

    if q:
        sql += " AND (rp.project_th LIKE ? OR rp.researcher_name LIKE ? OR rp.affiliation LIKE ?)"
        params.extend([f"%{q}%", f"%{q}%", f"%{q}%"])
    
    if aff:
        sql += " AND rp.affiliation = ?"
        params.append(aff)

    rows = conn.execute(sql, params).fetchall()
    
    # Get distinct affiliations for filter
    aff_rows = conn.execute("SELECT DISTINCT affiliation FROM research_projects WHERE affiliation != '' ORDER BY affiliation").fetchall()
    aff_list = [r['affiliation'] for r in aff_rows]
    
    # Get all researchers for assignment dropdown
    researchers = conn.execute(
        "SELECT id, username, email FROM users WHERE role = 'researcher' ORDER BY username"
    ).fetchall()
    
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
                           aff_list=aff_list,
                           researchers=researchers)

@research_bp.route("/delete/<int:pid>", methods=["POST"])
@login_required
@manager_required
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
@manager_required
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


# ---------------------------------------------------------
# 👥 Assign Researcher (Manager/Admin Only)
# ---------------------------------------------------------
@research_bp.route("/assign/<int:pid>", methods=["POST"])
@login_required
@manager_required
def assign_researcher(pid):
    """Assign a researcher to a project"""
    researcher_id = request.form.get('researcher_id')
    
    if not researcher_id:
        flash('กรุณาเลือก Researcher', 'warning')
        return redirect(url_for('research.dashboard'))
    
    conn = get_db()
    
    # Verify researcher exists and has researcher role
    researcher = conn.execute(
        "SELECT id, username FROM users WHERE id = ? AND role = 'researcher'",
        (researcher_id,)
    ).fetchone()
    
    if not researcher:
        flash('ไม่พบ Researcher ที่เลือก', 'danger')
        return redirect(url_for('research.dashboard'))
    
    # Get project info
    project = conn.execute(
        "SELECT project_th FROM research_projects WHERE id = ?",
        (pid,)
    ).fetchone()
    
    if not project:
        flash('ไม่พบโครงการ', 'danger')
        return redirect(url_for('research.dashboard'))
    
    try:
        # Assign researcher to project
        conn.execute(
            "UPDATE research_projects SET assigned_researcher_id = ? WHERE id = ?",
            (researcher_id, pid)
        )
        conn.commit()
        
        log_project_action(
            "RESEARCHER_ASSIGNED",
            project_id=pid,
            details=f"Assigned {researcher['username']} to project: {project['project_th']}"
        )
        
        # Send assignment notification email
        email_sent = False
        try:
            from notifications.scheduler import send_assignment_notification
            email_sent = send_assignment_notification(researcher_id, pid)
        except Exception as notify_err:
            print(f"⚠️ Notification error (non-critical): {notify_err}")
        
        if email_sent:
            flash(f'✅ มอบหมายโครงการให้ {researcher["username"]} สำเร็จ และส่ง Email แจ้งเตือนแล้ว', 'success')
        else:
            flash(f'✅ มอบหมายโครงการให้ {researcher["username"]} สำเร็จ (ไม่มี Email หรือส่ง Email ไม่สำเร็จ)', 'warning')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('research.dashboard'))


# ---------------------------------------------------------
# 📥 Download Template
# ---------------------------------------------------------
@research_bp.route("/download-template")
@login_required
@manager_required
def download_template():
    """Generate and download Excel template for quick import"""
    from flask import Response
    import io
    
    # Create template DataFrame
    template_data = {
        'ชื่อโครงการ (TH)': ['ตัวอย่าง: โครงการวิจัย ABC'],
        'ชื่อโครงการ (EN)': ['Example: Research Project ABC'],
        'ผู้รับผิดชอบ': ['ชื่อ นามสกุล'],
        'อีเมล': ['email@example.com'],
        'สังกัด': ['หน่วยงาน/คณะ'],
        'งบประมาณ': [100000],
        'Deadline': ['2024-12-31'],
        'วันเริ่มโครงการ': ['2024-01-01'],
        'วันสิ้นสุดโครงการ': ['2024-12-31']
    }
    
    df = pd.DataFrame(template_data)
    
    # Write to Excel in memory
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
    output.seek(0)
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': 'attachment;filename=ITRACK_Template.xlsx'}
    )


# ---------------------------------------------------------
# ⚡ Quick Import (Template-Based with Upsert)
# ---------------------------------------------------------
@research_bp.route("/quick-import", methods=["POST"])
@login_required
@manager_required
def quick_import():
    """Quick import from template with upsert logic"""
    if 'file' not in request.files:
        flash("กรุณาเลือกไฟล์", "warning")
        return redirect(url_for("research.landing"))
    
    file = request.files['file']
    if file.filename == '':
        flash("กรุณาเลือกไฟล์", "warning")
        return redirect(url_for("research.landing"))
    
    try:
        # Read Excel file
        df = pd.read_excel(file, engine='openpyxl')
        
        # Column mapping (Thai headers to database fields)
        column_map = {
            'ชื่อโครงการ (TH)': 'project_th',
            'ชื่อโครงการ (EN)': 'project_en',
            'ผู้รับผิดชอบ': 'researcher_name',
            'อีเมล': 'researcher_email',
            'สังกัด': 'affiliation',
            'งบประมาณ': 'funding',
            'Deadline': 'deadline',
            'วันเริ่มโครงการ': 'start_date',
            'วันสิ้นสุดโครงการ': 'end_date'
        }
        
        # Rename columns
        df = df.rename(columns=column_map)
        
        conn = get_db()
        inserted = 0
        updated = 0
        skipped = 0
        errors = []
        
        for idx, row in df.iterrows():
            try:
                project_th = str(row.get('project_th', '')).strip() if pd.notna(row.get('project_th')) else ''
                project_en = str(row.get('project_en', '')).strip() if pd.notna(row.get('project_en')) else ''
                
                # Skip if no project name
                if not project_th and not project_en:
                    skipped += 1
                    continue
                
                researcher_name = str(row.get('researcher_name', '')).strip() if pd.notna(row.get('researcher_name')) else ''
                researcher_email = str(row.get('researcher_email', '')).strip() if pd.notna(row.get('researcher_email')) else ''
                affiliation = str(row.get('affiliation', '')).strip() if pd.notna(row.get('affiliation')) else ''
                
                # Handle funding
                funding = 0
                if pd.notna(row.get('funding')):
                    try:
                        funding = float(row.get('funding', 0))
                    except:
                        funding = 0
                
                # Handle dates
                deadline = ''
                if pd.notna(row.get('deadline')):
                    dt = pd.to_datetime(row.get('deadline'), errors='coerce')
                    if not pd.isna(dt):
                        deadline = dt.strftime('%Y-%m-%d')
                
                start_date = ''
                if pd.notna(row.get('start_date')):
                    dt = pd.to_datetime(row.get('start_date'), errors='coerce')
                    if not pd.isna(dt):
                        start_date = dt.strftime('%Y-%m-%d')
                
                end_date = ''
                if pd.notna(row.get('end_date')):
                    dt = pd.to_datetime(row.get('end_date'), errors='coerce')
                    if not pd.isna(dt):
                        end_date = dt.strftime('%Y-%m-%d')
                
                # Check if project exists (by project_th)
                existing = None
                if project_th:
                    existing = conn.execute(
                        "SELECT id FROM research_projects WHERE project_th = ?",
                        (project_th,)
                    ).fetchone()
                
                if existing:
                    # UPDATE existing project
                    conn.execute("""
                        UPDATE research_projects SET
                            project_en = ?, researcher_name = ?, researcher_email = ?,
                            affiliation = ?, funding = ?, deadline = ?,
                            start_date = ?, end_date = ?
                        WHERE id = ?
                    """, (project_en, researcher_name, researcher_email, 
                          affiliation, funding, deadline, start_date, end_date,
                          existing['id']))
                    updated += 1
                else:
                    # INSERT new project
                    conn.execute("""
                        INSERT INTO research_projects 
                        (project_th, project_en, researcher_name, researcher_email, 
                         affiliation, funding, deadline, start_date, end_date, status)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'draft')
                    """, (project_th, project_en, researcher_name, researcher_email,
                          affiliation, funding, deadline, start_date, end_date))
                    inserted += 1
                    
            except Exception as e:
                errors.append(f"บรรทัด {idx + 2}: {str(e)}")
                skipped += 1
        
        conn.commit()
        
        # Log action
        log_action("QUICK_IMPORT", details=f"Inserted: {inserted}, Updated: {updated}, Skipped: {skipped}")
        
        # Flash result
        flash(f"นำเข้าเสร็จสิ้น: เพิ่มใหม่ {inserted} รายการ, อัพเดท {updated} รายการ, ข้าม {skipped} รายการ", "success")
        
        if errors:
            flash(f"พบข้อผิดพลาด: {', '.join(errors[:3])}", "warning")
        
    except Exception as e:
        flash(f"เกิดข้อผิดพลาด: {str(e)}", "danger")
    
    return redirect(url_for("research.landing"))


# ---------------------------------------------------------
# 📊 Export Data
# ---------------------------------------------------------
@research_bp.route("/export")
@login_required
@manager_required
def export_data():
    """Export project data to Excel with full details"""
    from flask import Response
    import io
    
    conn = get_db()
    selected_year = request.args.get('year', 'all')
    
    try:
        base_sql = """
            SELECT rp.*, u.username as assigned_researcher_name
            FROM research_projects rp
            LEFT JOIN users u ON rp.assigned_researcher_id = u.id
        """
        
        if selected_year != 'all' and selected_year:
            projects = conn.execute(base_sql + """
                WHERE strftime('%Y', rp.start_date) = ? OR strftime('%Y', rp.deadline) = ?
                ORDER BY rp.deadline ASC
            """, (selected_year, selected_year)).fetchall()
        else:
            projects = conn.execute(base_sql + " ORDER BY rp.deadline ASC").fetchall()
    except:
        projects = []
    
    # Calculate deadline status
    today = datetime.today().date()
    data = []
    
    for p in projects:
        # Calculate deadline status
        deadline_status = "ไม่มีกำหนด"
        days_left = None
        if p['deadline']:
            dt = pd.to_datetime(p['deadline'], errors='coerce')
            if not pd.isna(dt):
                days_left = (dt.date() - today).days
                if days_left < 0:
                    deadline_status = "เลยกำหนด"
                elif days_left <= 7:
                    deadline_status = "ใกล้กำหนด"
                else:
                    deadline_status = "ปกติ"
        
        # Map current_status to Thai
        status_map = {
            'not_started': 'ยังไม่เริ่ม',
            'in_progress': 'กำลังดำเนินการ',
            'completed': 'เสร็จสมบูรณ์',
            'on_hold': 'หยุดชั่วคราว',
            'delayed': 'ล่าช้า'
        }
        current_status_th = status_map.get(p['current_status'], 'ยังไม่เริ่ม')
        
        data.append({
            'ชื่อโครงการ (TH)': p['project_th'] or '',
            'ชื่อโครงการ (EN)': p['project_en'] or '',
            'ผู้รับผิดชอบหลัก': p['researcher_name'] or '',
            'อีเมล': p['researcher_email'] or '',
            'สังกัด': p['affiliation'] or '',
            'Researcher ที่มอบหมาย': p['assigned_researcher_name'] if 'assigned_researcher_name' in p.keys() else 'ยังไม่มอบหมาย',
            'ความคืบหน้า (%)': p['progress_percent'] if 'progress_percent' in p.keys() else 0,
            'สถานะงาน': current_status_th,
            'เหตุผลล่าช้า': p['delay_reason'] if 'delay_reason' in p.keys() and p['delay_reason'] else '',
            'งบประมาณ': p['funding'] or 0,
            'วันเริ่มโครงการ': p['start_date'] or '',
            'วันสิ้นสุดโครงการ': p['end_date'] or '',
            'Deadline': p['deadline'] or '',
            'สถานะ Deadline': deadline_status,
            'เหลือวัน': days_left if days_left is not None else ''
        })
    
    df = pd.DataFrame(data)
    
    # Write to Excel with formatting
    output = io.BytesIO()
    with pd.ExcelWriter(output, engine='openpyxl') as writer:
        df.to_excel(writer, index=False, sheet_name='Projects')
        
        # Auto-adjust column widths
        try:
            from openpyxl.utils import get_column_letter
            worksheet = writer.sheets['Projects']
            for idx, col in enumerate(df.columns):
                max_length = max(df[col].astype(str).map(len).max(), len(str(col))) + 2
                col_letter = get_column_letter(idx + 1)  # 1-indexed
                worksheet.column_dimensions[col_letter].width = min(max_length, 50)
        except Exception as e:
            print(f"Warning: Could not auto-adjust columns: {e}")
    
    output.seek(0)
    
    # Filename with date
    filename = f"ITRACK_Report_{datetime.today().strftime('%Y%m%d')}.xlsx"
    
    log_action("EXPORT_DATA", details=f"Exported {len(projects)} projects, year={selected_year}")
    
    return Response(
        output.getvalue(),
        mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
        headers={'Content-Disposition': f'attachment;filename={filename}'}
    )


# ---------------------------------------------------------
# 📋 Executive Report (Print-Friendly)
# ---------------------------------------------------------
@research_bp.route("/report")
@login_required
@manager_required
def executive_report():
    """Generate executive summary report (print-friendly for PDF)"""
    conn = get_db()
    today = datetime.today().date()
    
    # Get filter parameters
    selected_affiliation = request.args.get('affiliation', 'all')
    
    # Get list of all affiliations
    aff_rows = conn.execute("""
        SELECT DISTINCT affiliation FROM research_projects 
        WHERE affiliation IS NOT NULL AND affiliation != '' 
        ORDER BY affiliation
    """).fetchall()
    affiliations_list = [r['affiliation'] for r in aff_rows]
    
    # Fetch projects with optional affiliation filter
    base_sql = """
        SELECT rp.*, u.username as assigned_researcher_name
        FROM research_projects rp
        LEFT JOIN users u ON rp.assigned_researcher_id = u.id
    """
    
    if selected_affiliation != 'all' and selected_affiliation:
        projects = conn.execute(base_sql + " WHERE rp.affiliation = ? ORDER BY rp.deadline ASC", 
                               (selected_affiliation,)).fetchall()
    else:
        projects = conn.execute(base_sql + " ORDER BY rp.deadline ASC").fetchall()
    
    # Statistics
    total = len(projects)
    on_track = near_deadline = overdue = completed = in_progress = 0
    total_funding = 0
    funding_by_affiliation = {}
    progress_by_status = {'not_started': 0, 'in_progress': 0, 'completed': 0, 'on_hold': 0, 'delayed': 0}
    project_list = []
    
    for p in projects:
        # Funding
        funding = p['funding'] or 0
        total_funding += funding
        
        aff = p['affiliation'] or 'ไม่ระบุ'
        funding_by_affiliation[aff] = funding_by_affiliation.get(aff, 0) + funding
        
        # Status counters
        status = p['current_status'] or 'not_started'
        if status in progress_by_status:
            progress_by_status[status] += 1
        
        if status == 'completed':
            completed += 1
        elif status == 'in_progress':
            in_progress += 1
        
        # Deadline status
        deadline_status = 'no_deadline'
        days_left = None
        if p['deadline']:
            dt = pd.to_datetime(p['deadline'], errors='coerce')
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
        
        project_list.append({
            'id': p['id'],
            'project_th': p['project_th'] or '-',
            'researcher_name': p['researcher_name'] or '-',
            'assigned_researcher': p['assigned_researcher_name'] or 'ยังไม่มอบหมาย',
            'affiliation': aff,
            'progress_percent': p['progress_percent'] or 0,
            'current_status': status,
            'deadline': p['deadline'] or '-',
            'days_left': days_left,
            'deadline_status': deadline_status,
            'funding': funding
        })
    
    # Sort funding by affiliation
    top_affiliations = sorted(funding_by_affiliation.items(), key=lambda x: x[1], reverse=True)[:5]
    
    # Calculate average progress
    avg_progress = sum(p['progress_percent'] for p in project_list) / total if total > 0 else 0
    
    log_action("VIEW_REPORT", details=f"Viewed executive report, affiliation={selected_affiliation}")
    
    return render_template("research/report.html",
                           total=total,
                           on_track=on_track,
                           near_deadline=near_deadline,
                           overdue=overdue,
                           completed=completed,
                           in_progress=in_progress,
                           avg_progress=avg_progress,
                           total_funding=total_funding,
                           top_affiliations=top_affiliations,
                           progress_by_status=progress_by_status,
                           project_list=project_list,
                           report_date=today.strftime('%d/%m/%Y'),
                           affiliations_list=affiliations_list,
                           selected_affiliation=selected_affiliation)

