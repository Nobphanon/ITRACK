"""
Researcher Routes - Progress Tracking
Researcher-specific functionality for updating project progress
"""

from flask import Blueprint, render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from models import get_db
from permissions import researcher_required, can_update_progress
from datetime import datetime
import json

researcher_bp = Blueprint('researcher', __name__, url_prefix='/researcher')


@researcher_bp.route('/dashboard')
@login_required
@researcher_required
def dashboard():
    """Researcher dashboard showing assigned projects"""
    conn = get_db()
    
    # Get projects assigned to this researcher
    if current_user.role == 'researcher':
        projects = conn.execute("""
            SELECT * FROM research_projects
            WHERE assigned_researcher_id = ?
            ORDER BY deadline ASC
        """, (current_user.id,)).fetchall()
    else:
        # Admin and Manager can see all projects
        projects = conn.execute("""
            SELECT * FROM research_projects
            ORDER BY deadline ASC
        """).fetchall()
    
    # Calculate stats
    total = len(projects)
    not_started = len([p for p in projects if p['current_status'] == 'not_started'])
    in_progress = len([p for p in projects if p['current_status'] == 'in_progress'])
    completed = len([p for p in projects if p['current_status'] == 'completed'])
    delayed = len([p for p in projects if p['current_status'] == 'delayed'])
    
    # Average progress
    avg_progress = sum([p['progress_percent'] for p in projects]) / total if total > 0 else 0
    
    return render_template('researcher/dashboard.html',
                         projects=projects,
                         total=total,
                         not_started=not_started,
                         in_progress=in_progress,
                         completed=completed,
                         delayed=delayed,
                         avg_progress=avg_progress)


@researcher_bp.route('/project/<int:project_id>')
@login_required
@researcher_required
def project_detail(project_id):
    """View project details and update history"""
    conn = get_db()
    
    project = conn.execute("""
        SELECT * FROM research_projects WHERE id = ?
    """, (project_id,)).fetchone()
    
    if not project:
        flash('ไม่พบโครงการ', 'danger')
        return redirect(url_for('researcher.dashboard'))
    
    # Check permission
    if current_user.role == 'researcher' and project['assigned_researcher_id'] != current_user.id:
        flash('⛔ คุณไม่มีสิทธิ์เข้าถึงโครงการนี้', 'danger')
        return redirect(url_for('researcher.dashboard'))
    
    # Get update history
    updates = conn.execute("""
        SELECT u.*, users.username
        FROM project_updates u
        LEFT JOIN users ON u.updated_by = users.id
        WHERE u.project_id = ?
        ORDER BY u.updated_at DESC
    """, (project_id,)).fetchall()
    
    return render_template('researcher/project_detail.html',
                         project=project,
                         updates=updates)


@researcher_bp.route('/project/<int:project_id>/update', methods=['POST'])
@login_required
@researcher_required
def update_progress(project_id):
    """Update project progress"""
    conn = get_db()
    
    project = conn.execute("""
        SELECT * FROM research_projects WHERE id = ?
    """, (project_id,)).fetchone()
    
    if not project:
        flash('ไม่พบโครงการ', 'danger')
        return redirect(url_for('researcher.dashboard'))
    
    # Check permission
    if not can_update_progress(project):
        flash('⛔ คุณไม่มีสิทธิ์แก้ไขโครงการนี้', 'danger')
        return redirect(url_for('researcher.dashboard'))
    
    # Get form data
    progress_percent = int(request.form.get('progress_percent', 0))
    status = request.form.get('status', 'not_started')
    remarks = request.form.get('remarks', '').strip()
    delay_reason = request.form.get('delay_reason', '').strip()
    
    # Validation
    if not (0 <= progress_percent <= 100):
        flash('ความคืบหน้าต้องอยู่ระหว่าง 0-100%', 'danger')
        return redirect(url_for('researcher.project_detail', project_id=project_id))
    
    if status not in ['not_started', 'in_progress', 'completed', 'on_hold', 'delayed']:
        flash('สถานะไม่ถูกต้อง', 'danger')
        return redirect(url_for('researcher.project_detail', project_id=project_id))
    
    # If delayed, must provide reason
    if status == 'delayed' and not delay_reason:
        flash('⚠️ กรุณาระบุเหตุผลความล่าช้า', 'warning')
        return redirect(url_for('researcher.project_detail', project_id=project_id))
    
    # Get current time
    now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
    
    try:
        # Update project
        conn.execute("""
            UPDATE research_projects
            SET progress_percent = ?,
                current_status = ?,
                last_updated_at = ?,
                last_updated_by = ?
            WHERE id = ?
        """, (progress_percent, status, now, current_user.id, project_id))
        
        # Insert update history
        conn.execute("""
            INSERT INTO project_updates 
            (project_id, updated_by, updated_at, progress_percent, status, remarks, delay_reason)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (project_id, current_user.id, now, progress_percent, status, remarks, delay_reason))
        
        conn.commit()
        
        flash(f'✅ อัปเดตความคืบหน้าเป็น {progress_percent}% สำเร็จ', 'success')
    except Exception as e:
        flash(f'เกิดข้อผิดพลาด: {str(e)}', 'danger')
    
    return redirect(url_for('researcher.project_detail', project_id=project_id))


@researcher_bp.route('/api/projects')
@login_required
@researcher_required  
def api_my_projects():
    """API endpoint for researcher's projects (for charts/widgets)"""
    conn = get_db()
    
    if current_user.role == 'researcher':
        projects = conn.execute("""
            SELECT id, project_th, progress_percent, current_status, deadline
            FROM research_projects
            WHERE assigned_researcher_id = ?
        """, (current_user.id,)).fetchall()
    else:
        projects = conn.execute("""
            SELECT id, project_th, progress_percent, current_status, deadline
            FROM research_projects
        """).fetchall()
    
    return jsonify([dict(p) for p in projects])
