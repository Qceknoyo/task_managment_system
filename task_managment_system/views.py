import json
import os
from datetime import datetime
from flask import Flask, render_template, request, redirect, url_for, session,flash
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
from task_managment_system import app
import random
import string

db_config = {
    'host': 'localhost',
    'user': 'root',
    'password': '@Somebody228',
    'database': 'task_managment_system'
}

TASK_STATUSES = [
    'Новая',
    'В работе',
    'На проверке',
    'Завершена',
    'Отложена'
]


UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

@app.before_request
def set_current_user():
    if 'user_id' in session:
        conn = get_db_connection()
        with conn.cursor() as cursor:
            initiator_id = int(session['user_id'])
            cursor.execute("SET @current_user_id = %s", (initiator_id,))
        conn.close()


def get_db_connection():
    return mysql.connector.connect(**db_config)

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/")
def index():
    return render_template('index.html')
      

@app.route('/project/<int:project_id>/add_task', methods=['GET', 'POST'])
def add_task(project_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        # Получаем всех участников проекта
        cursor.execute("""
            SELECT upr.user_id, users.login AS username, roles.name AS role_name
            FROM userprojectroles upr
            JOIN users ON upr.user_id = users.id
            JOIN roles ON upr.role_id = roles.id
            WHERE upr.project_id = %s
        """, (project_id,))
        members = cursor.fetchall()


        if request.method == 'POST':
            title = request.form['title']
            description = request.form['description']
            status = int(request.form['status'])
            assigned_to = int(request.form['assigned_to'])  # Преобразуем к int
            creator_user_id = session['user_id']

            start_date = request.form.get('start_date') or None
            deadline = request.form.get('deadline') or None

            # Добавление задачи в базу данных
            cursor.execute("""
                INSERT INTO tasks (project_id, name, description, status, assigned_user_id, created_at, creator_user_id, start_date, deadline)
                VALUES (%s, %s, %s, %s, %s, NOW(), %s, %s, %s)
            """, (project_id, title, description, status, assigned_to, creator_user_id, start_date, deadline))
            conn.commit()
            
            return redirect(url_for('view_project', project_id=project_id))

    finally:
        cursor.close()
        conn.close()

    return render_template('add_task.html', project_id=project_id, members=members)


@app.route('/project/<int:project_id>/task/<int:task_id>/comment/<int:comment_id>/delete', methods=['POST'])
def delete_comment(project_id, task_id, comment_id):
    
    conn = get_db_connection()
    cursor = conn.cursor()
    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        # Удаляем комментарий
        cursor.execute("DELETE FROM task_comments WHERE id = %s", (comment_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()
        flash("Комментарий удалён", "success")

    return redirect(url_for('view_project', project_id=project_id)) 


@app.route('/project/<int:project_id>/delete_task/<int:task_id>', methods=['POST'])
def delete_task(project_id, task_id):
    conn = get_db_connection()
    cursor = conn.cursor()
    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))
    try:
        cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
        conn.commit()
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_project', project_id=project_id))


@app.route('/project/<int:project_id>/toggle_task/<int:task_id>', methods=['POST'])
def toggle_task(project_id, task_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)  # Используем dictionary=True
    
    try:
        # Получаем текущий статус
        cursor.execute("SELECT status FROM tasks WHERE id = %s", (task_id,))
        task = cursor.fetchone()
        
        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('view_project', project_id=project_id))
            
        current_status = task['status']
        
        # Определяем следующий статус по порядку
        if current_status not in TASK_STATUSES:
            new_status = TASK_STATUSES[0]  # Если статус неизвестен, ставим первый
        else:
            current_index = TASK_STATUSES.index(current_status)
            next_index = (current_index + 1) % len(TASK_STATUSES)
            new_status = TASK_STATUSES[next_index]
        
        # Обновляем статус
        cursor.execute("UPDATE tasks SET status = %s WHERE id = %s", 
                      (new_status, task_id))
        conn.commit()
        
        flash(f'Статус изменен на: {new_status}', 'success')
        
    except Exception as e:
        conn.rollback()
        flash(f'Ошибка при изменении статуса: {str(e)}', 'danger')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_project', project_id=project_id))




@app.route('/project/<int:project_id>/update_status/<int:task_id>', methods=['POST'])
def update_task_status(project_id, task_id):
    new_status = request.form['new_status']
    
    conn = get_db_connection()
    cursor = conn.cursor()
    
    try:
        initiator_id = int(session['user_id'])
        cursor.execute("SET @current_user_id = %s", (initiator_id,))

        cursor.execute("UPDATE tasks SET status = %s WHERE id = %s", 
                      (new_status, task_id))
        conn.commit()
        flash('Статус задачи обновлен', 'success')
    except:
        conn.rollback()
        flash('Ошибка при обновлении статуса', 'danger')
    finally:
        cursor.close()
        conn.close()
    
    return redirect(url_for('view_project', project_id=project_id))




@app.route('/project/<int:project_id>')
def view_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    conn = get_db_connection()
    if conn is None:
        return "Ошибка базы данных", 500  # Или редирект на страницу ошибки

    cursor = conn.cursor(dictionary=True)

    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        #для фильтра по задачам
        filters = []
        params = []

        name = request.args.get('name', '').strip()
        status = request.args.get('status')
        deadline_from = request.args.get('deadline_from')
        deadline_to = request.args.get('deadline_to')
        assigned_user_id = request.args.get('assigned_user_id')

        if name:
            filters.append("tasks.name LIKE %s")
            params.append(f"%{name}%")

        if status and status.isdigit():
            filters.append("tasks.status = %s")
            params.append(int(status))

        if deadline_from:
            filters.append("tasks.deadline >= %s")
            params.append(deadline_from)

        if deadline_to:
            filters.append("tasks.deadline <= %s")
            params.append(deadline_to)

        if assigned_user_id and assigned_user_id.isdigit():
            filters.append("tasks.assigned_user_id = %s")
            params.append(int(assigned_user_id))

        filter_clause = " AND " + " AND ".join(filters) if filters else ""

        
        #для фильтра по аудиту
        audit_filters = []
        audit_params = [project_id]

        event_type = request.args.get('event_type')
        initiator_id = request.args.get('initiator_id')

        if event_type:
            audit_filters.append("e.name = %s")
            audit_params.append(event_type)

        if initiator_id:
            audit_filters.append("u.id = %s")
            audit_params.append(initiator_id)

        audit_filter_clause = " AND " + " AND ".join(audit_filters) if audit_filters else ""


        cursor.execute(f"""
            SELECT 
                a.id, a.event_time, e.name AS event_name, e.description,
                u.login AS initiator_login, u.full_name AS initiator_name,
                a.object_type, a.affected_object_id,
                a.previous_data, a.new_data,
                affected_user.full_name AS affected_user_name
            FROM auditlog a
            JOIN eventtypes e ON a.event_type_id = e.id
            JOIN users u ON a.initiator_id = u.id
            LEFT JOIN users affected_user 
                ON a.object_type = 'user' AND a.affected_object_id = affected_user.id
            WHERE a.project_id = %s {audit_filter_clause}
            ORDER BY a.event_time DESC
        """, audit_params)
        logs = cursor.fetchall()


        


        # Получаем проект с ролью пользователя в проекте
        cursor.execute("""
            SELECT p.id, p.name, p.description, p.invite_code, r.name AS role_name
            FROM projects p
            JOIN userprojectroles upr ON p.id = upr.project_id
            JOIN roles r ON upr.role_id = r.id
            WHERE p.id = %s AND upr.user_id = %s
        """, (project_id, session['user_id']))
        project = cursor.fetchone()  # Убираем projectx, используем project

        # Получаем задачи проекта
        cursor.execute(f"""
            SELECT 
                tasks.id, tasks.name, tasks.description, tasks.status,
                tasks.start_date, tasks.deadline, tasks.proposed_status,
                tasks.assigned_user_id, tasks.creator_user_id,
                u1.full_name AS assigned_user_name,
                u2.full_name AS creator_user_name
            FROM tasks
            LEFT JOIN users u1 ON tasks.assigned_user_id = u1.id
            LEFT JOIN users u2 ON tasks.creator_user_id = u2.id
            WHERE tasks.project_id = %s {filter_clause}
        """, (project_id, *params))
        tasks = cursor.fetchall()


         # Получаем участников проекта с ролями
        cursor.execute("""
            SELECT upr.user_id, users.login AS username, roles.name AS role_name
            FROM userprojectroles upr
            JOIN users ON upr.user_id = users.id
            JOIN roles ON upr.role_id = roles.id
            WHERE upr.project_id = %s
        """, (project_id,))
        members = cursor.fetchall() 

        # Получаем все доступные роли для назначения
        cursor.execute("SELECT id, name FROM roles")
        all_roles = cursor.fetchall()
        
        

        # Проверка прав на редактирование задач
        for task in tasks:
            task['is_editable'] = False
            if project['role_name'] in ['master', 'submaster', 'creator'] or task['assigned_user_id'] == session['user_id']:
                task['is_editable'] = True

            # Загружаем комментарии к задаче
            cursor.execute("""
                SELECT 
                    tc.id AS comment_id,
                    tc.comment_text, 
                    tc.created_at, 
                    u.login AS user_name
                FROM task_comments tc
                JOIN users u ON tc.user_id = u.id
                WHERE tc.task_id = %s
                ORDER BY tc.created_at ASC
            """, (task['id'],))
            task['comments'] = cursor.fetchall()

            # Добавляем флаг can_comment
            task['can_comment'] = (
                project['role_name'] in ['creator', 'master', 'submaster'] or
                task['assigned_user_id'] == session['user_id']
            )

    

    finally:
        conn.close()

    def format_audit_event(log):
        role_map = {
            '1': 'unknown',
            '2': 'master',
            '3': 'submaster',
            '4': 'worker',
            '5': 'creator'
        }

        status_map = {
            '0': 'Новая',
            '1': 'В процессе',
            '2': 'Готова к проверке',
            '3': 'Завершена',
            '10': 'Отложена'
        }



        initiator = log.get('initiator_name', 'Неизвестный пользователь')
        object_type = log.get('object_type')
        event_name = log.get('event_name', '')
        target_id = log.get('affected_object_id')
        target_user = log.get("affected_user_name") or f"user_id={target_id}"

        # Преобразуем строки JSON в словари
        try:
            prev_data = json.loads(log.get('previous_data') or '{}')
        except json.JSONDecodeError:
            prev_data = {}
        try:
            new_data = json.loads(log.get('new_data') or '{}')
        except json.JSONDecodeError:
            new_data = {}

        # Изменение роли пользователя
        if object_type == 'user' and event_name == 'user_role_changed':
            old = role_map.get(str(prev_data.get("role_id")), str(prev_data.get("role_id")))
            new = role_map.get(str(new_data.get("role_id")), str(new_data.get("role_id")))
            return f"{initiator} изменил(а) роль пользователя <b>{target_user}</b> с <b>{old}</b> на <b>{new}</b>"


        elif object_type == 'task':
            if event_name == 'task_status_changed':
                return f"{initiator} изменил(а) статус задачи #{target_id} с <b>{prev_data.get('status')}</b> на <b>{new_data.get('status')}</b>"
            elif event_name == 'task_created':
                return f"{initiator} создал(а) задачу #{target_id}: <b>{new_data.get('name')}</b>"
            elif event_name == 'task_deleted':
                return f"{initiator} удалил(а) задачу #{target_id}: <b>{prev_data.get('name')}</b>"
            else:
                changed_fields = []
                for key in new_data:
                    old_val = prev_data.get(key)
                    new_val = new_data[key]
                    if old_val != new_val:
                        if key == 'status':
                            old_val = status_map.get(str(old_val), old_val)
                            new_val = status_map.get(str(new_val), new_val)
                        changed_fields.append(f"<span class='field-name'>{key}:</span> <del>{old_val}</del> → <b>{new_val}</b>")

                if changed_fields:
                    changes_html = " ".join(changed_fields)
                else:
                    changes_html = "<i>Без изменений</i>"

                return f"{initiator} обновил(а) задачу #{target_id}: {changes_html}"

        elif object_type == 'project' and event_name == 'project_updated':
            changes = []
            for key in set(prev_data.keys()).union(new_data.keys()):
                old = prev_data.get(key)
                new = new_data.get(key)
                if old != new:
                    changes.append(f"<span class='field-name'>{key}:</span> <del>{old}</del> → <b>{new}</b>")
    
            changes_html = " ".join(changes) if changes else "<i>Без изменений</i>"
            return f"{initiator} обновил(а) проект #{target_id}: {changes_html}"

        elif object_type == 'user' and event_name == 'user_added':
            role_id = new_data.get('role_id')
            role = role_map.get(str(role_id), f"role_id={role_id}")
            return f"{initiator} добавил(а) пользователя <b>{target_user}</b> в проект с ролью <b>{role}</b>"
        
        elif object_type == 'user' and event_name == 'user_removed':
            return f"{initiator} удалил(а) пользователя <b>{target_user}</b> из проекта"

        elif object_type == 'comment':
            if event_name == 'comment_added':
                task_id = new_data.get('task_id')
                text = new_data.get('text', '').strip()
                return f"{initiator} оставил(а) комментарий «<i>{text}</i>» к задаче #{task_id}"
            elif event_name == 'comment_updated':
                old_text = prev_data.get('text', '').strip()
                new_text = new_data.get('text', '').strip()
                task_id = new_data.get('task_id') or prev_data.get('task_id')
                return (f"{initiator} обновил(а) комментарий к задаче #{task_id}<br>"
                        f"<b>До:</b> <i>{old_text}</i><br><b>После:</b> <i>{new_text}</i>")
            elif event_name == 'comment_deleted':
                task_id = prev_data.get('task_id')
                text = prev_data.get('text', '').strip()
                return f"{initiator} удалил(а) комментарий «<i>{text}</i>» к задаче #{task_id}"


        return f"{initiator} выполнил(а) действие: <b>{event_name}</b> на объекте {object_type} #{target_id}"

    return render_template("view_project.html", project=project, tasks=tasks,members=members,all_roles=all_roles,logs=logs,format_audit_event=format_audit_event)



@app.route('/user/<int:user_id>')
def view_profile(user_id):
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    try:
        cursor.execute("""
            SELECT id, login, email, phone, profile_photo, registration_date
            FROM users
            WHERE id = %s
        """, (user_id,))
        user = cursor.fetchone()
    finally:
        cursor.close()
        conn.close()

    if not user:
        return "Пользователь не найден", 404

    return render_template('profile.html', user=user)



@app.route('/base')
def base():
    return render_template('base.html')




@app.route('/join_project', methods=['GET', 'POST'])
def join_project():
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))  # Перенаправляем на логин, если не залогинен

    if request.method == 'POST':
        invite_code = request.form['code']  # Получаем код из формы

        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)

            initiator_id = int(session['user_id'])
            cursor.execute("SET @current_user_id = %s", (initiator_id,))

            # Проверка, существует ли проект с таким кодом
            cursor.execute("SELECT id FROM projects WHERE invite_code = %s", (invite_code,))
            project = cursor.fetchone()

            if project:
                project_id = project['id']

                # Проверка, не является ли пользователь уже участником проекта
                cursor.execute("""
                    SELECT 1 FROM userprojectroles WHERE user_id = %s AND project_id = %s
                """, (session['user_id'], project_id))
                if cursor.fetchone():
                    flash("Вы уже являетесь участником этого проекта.")
                else:
                    # Добавление пользователя в проект с ролью "worker"
                    cursor.execute("""
                        INSERT INTO userprojectroles (user_id, project_id, role_id)
                        VALUES (%s, %s, (SELECT id FROM roles WHERE name = 'worker'))
                    """, (session['user_id'], project_id))
                    conn.commit()
                    flash("Вы успешно присоединились к проекту.")
                    return redirect(url_for('myprojects'))  # Редирект после успешного добавления

            else:
                flash("Проект с таким кодом не найден.")

        except Exception as e:
            conn.rollback()
            flash(f"Ошибка: {str(e)}")

        finally:
            cursor.close()
            conn.close()

    return render_template('join_project.html')



@app.route('/project/<int:project_id>/edit_role', methods=['POST'])
def edit_role(project_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    project_id = int(project_id)
    user_id = int(request.form['user_id'])
    new_role_id = int(request.form['role_id'])

    conn = get_db_connection()
    cursor = conn.cursor()

    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        initiator_id = int(session['user_id'])
        cursor.execute("SET @current_user_id = %s", (initiator_id,))
        # Устанавливаем переменную @current_user_id в рамках того же соединения
        cursor.execute("SET @current_user_id = %s", (session['user_id'],))

        # Теперь делаем UPDATE — триггер получит @current_user_id
        cursor.execute("""
            UPDATE userprojectroles
            SET role_id = %s
            WHERE project_id = %s AND user_id = %s
        """, (new_role_id, project_id, user_id))

        conn.commit()
        flash('Роль пользователя успешно обновлена!', 'success')

    except Exception as e:
        flash(f'Ошибка при изменении роли: {str(e)}', 'danger')
        conn.rollback()

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_project', project_id=project_id))




@app.route('/create_project', methods=['GET', 'POST'])
def create_project():
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    if request.method == 'POST':
        name = request.form['name']
        description = request.form['description']
        user_id = session['user_id']

        try:
            conn = get_db_connection()
            cursor = conn.cursor()
            
            invite_code = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

            # 1. Создание проекта
            cursor.execute("""
                INSERT INTO projects (name, description, creator_id, creation_date,invite_code) 
                VALUES (%s, %s, %s, NOW(),%s)
            """, (name, description, user_id,invite_code))

            # 2. Получение id только что созданного проекта
            cursor.execute("SELECT LAST_INSERT_ID()")
            project_id = cursor.fetchone()[0]  # fetchone() возвращает кортеж

            # 3. Получение id роли 'master' (или замени на свою стартовую роль)
            cursor.execute("SELECT id FROM roles WHERE name = 'master'")
            role_result = cursor.fetchone()
            if role_result:
                role_id = role_result[0]
            else:
                role_id = 1  # fallback, если вдруг нет такой роли — подставь свою

            # 4. Добавление создателя в userprojectroles
            cursor.execute("""
                INSERT INTO userprojectroles (user_id, project_id, role_id)
                VALUES (%s, %s, %s)
            """, (user_id, project_id, role_id))

            conn.commit()
        finally:
            cursor.close()
            conn.close()

        return redirect(url_for('myprojects'))

    return render_template("create_project.html")




@app.route("/Login", methods=['GET', 'POST'])
def LogIn():
    form_data = {}
    if request.method ==  'POST':
        username = request.form['login']
        password = request.form['password']
        try:
            conn = get_db_connection()
            cursor = conn.cursor(dictionary=True)
            
            # Ищем пользователя в базе
            cursor.execute("SELECT * FROM users WHERE login = %s", (username,))
            user = cursor.fetchone()
            
            if user and check_password_hash(user['password_hash'], password):
                # Успешный вход
                session['user_id'] = user['id']  # Сохраняем в сессии
                session['username'] = user['login']
                return redirect(url_for('HomePage'))
            else:
                # Неверные данные
                error = "Неверный логин или пароль"
                return render_template('login.html', error=error)
                
        except Exception as e:
            error = f"Ошибка сервера: {str(e)}"
            return render_template('login.html', error=error)
        finally:
            if 'conn' in locals() and conn.is_connected():
                cursor.close()
                conn.close()
    
    # GET-запрос - показать форму
    return render_template('login.html')

    
    #return render_template('login.html')


@app.route('/project/<int:project_id>/edit_project', methods=['GET', 'POST'])
def edit_project(project_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        
        # Получаем проект с ролью пользователя в проекте
        cursor.execute("""
            SELECT p.id, p.name, p.description, p.invite_code, r.name AS role_name
            FROM projects p
            JOIN userprojectroles upr ON p.id = upr.project_id
            JOIN roles r ON upr.role_id = r.id
            WHERE p.id = %s AND upr.user_id = %s
        """, (project_id, session['user_id']))
        project = cursor.fetchone()

        if not project:
            flash('Проект не найден', 'danger')
            return redirect(url_for('view_project', project_id=project_id))

        user_id = session['user_id']
        user_role = project['role_name']

        # Загружаем задачи проекта
        cursor.execute("""
            SELECT t.*, u1.login AS assigned_user_name, u2.login AS creator_user_name
            FROM tasks t
            LEFT JOIN users u1 ON t.assigned_user_id = u1.id
            LEFT JOIN users u2 ON t.creator_user_id = u2.id
            WHERE t.project_id = %s
        """, (project_id,))
        tasks = cursor.fetchall()

        for task in tasks:
            # Загружаем комментарии к задаче
            cursor.execute("""
                SELECT tc.comment_text, tc.created_at, u.login AS user_name
                FROM task_comments tc
                JOIN users u ON tc.user_id = u.id
                WHERE tc.task_id = %s
                ORDER BY tc.created_at ASC
            """, (task['id'],))
            task['comments'] = cursor.fetchall()

            # Определяем, может ли текущий пользователь комментировать эту задачу
            task['can_comment'] = (
                user_role in ['master', 'submaster', 'creator'] or
                task['assigned_user_id'] == user_id
            )

        if request.method == 'POST':
            name = request.form['name']
            description = request.form['description']
            invite_code = request.form['invite_code']

            cursor.execute("""
                UPDATE projects
                SET name = %s, description = %s, invite_code = %s
                WHERE id = %s
            """, (name, description, invite_code, project_id))
            conn.commit()

            flash('Проект успешно обновлён!', 'success')
            return redirect(url_for('view_project', project_id=project_id))

    finally:
        cursor.close()
        conn.close()

    return render_template("edit_project.html", project=project, tasks=tasks)


@app.route('/project/<int:project_id>/task/<int:task_id>/comment', methods=['POST'])
def add_comment(project_id, task_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    user_id = session['user_id']
    comment_text = request.form.get('comment', '').strip()

    if not comment_text:
        flash('Комментарий не может быть пустым', 'warning')
        return redirect(url_for('view_project', project_id=project_id))

    conn = get_db_connection()
    cursor = conn.cursor()

    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        cursor.execute("""
            SELECT upr.role_id, r.name AS role_name, t.assigned_user_id
            FROM userprojectroles upr
            JOIN roles r ON upr.role_id = r.id
            JOIN tasks t ON t.project_id = upr.project_id AND t.id = %s
            WHERE upr.project_id = %s AND upr.user_id = %s
        """, (task_id, project_id, user_id))
        result = cursor.fetchone()

        if not result:
            flash('Вы не участник проекта или задача не найдена', 'danger')
            return redirect(url_for('view_project', project_id=project_id))

        role_name = result[1]
        assigned_user_id = result[2]

        if role_name not in ['creator', 'master', 'submaster'] and assigned_user_id != user_id:
            flash('У вас нет прав оставлять комментарии к этой задаче', 'danger')
            return redirect(url_for('view_project', project_id=project_id))

        cursor.execute("""
            INSERT INTO task_comments (task_id, user_id, comment_text)
            VALUES (%s, %s, %s)
        """, (task_id, user_id, comment_text))
        conn.commit()

        flash('Комментарий добавлен', 'success')
    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_project', project_id=project_id) + f"#task-{task_id}")






@app.route('/project/<int:project_id>/task/<int:task_id>/confirm_status', methods=['POST'])
def confirm_status(project_id, task_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    try:
        # Получаем роль
        cursor.execute("""
            SELECT r.name AS role_name
            FROM userprojectroles upr
            JOIN roles r ON upr.role_id = r.id
            WHERE upr.project_id = %s AND upr.user_id = %s
        """, (project_id, session['user_id']))
        role = cursor.fetchone()

        if not role or role['role_name'] not in ['master', 'submaster', 'creator']:
            flash('У вас нет прав подтверждать статусы', 'danger')
            return redirect(url_for('view_project', project_id=project_id))

        # Обновляем статус
        confirmed_status = request.form.get('confirmed_status')
        cursor.execute("""
            UPDATE tasks SET status = %s, proposed_status = NULL
            WHERE id = %s AND project_id = %s
        """, (confirmed_status, task_id, project_id))

        conn.commit()
        flash('Статус успешно подтверждён', 'success')

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_project', project_id=project_id))


@app.route('/project/<int:project_id>')
def project_details(project_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Получаем роль пользователя в проекте
    cursor.execute("""
        SELECT r.name AS role_name FROM userprojectroles upr
        JOIN roles r ON upr.role_id = r.id
        WHERE upr.project_id = %s AND upr.user_id = %s
    """, (project_id, user_id))
    role_info = cursor.fetchone()
    user_role = role_info['role_name'] if role_info else 'unknown'

    # Загружаем задачи (включаем start_date и deadline явно, если нужно)
    cursor.execute("""
        SELECT 
            t.*, 
            u1.login AS assigned_user_name, 
            u2.login AS creator_user_name
        FROM tasks t
        LEFT JOIN users u1 ON t.assigned_user_id = u1.id
        LEFT JOIN users u2 ON t.creator_user_id = u2.id
        WHERE t.project_id = %s
    """, (project_id,))
    tasks = cursor.fetchall()

    for task in tasks:
        # Загружаем комментарии для каждой задачи
        cursor.execute("""
            SELECT tc.comment_text, tc.created_at, u.login AS user_name
            FROM task_comments tc
            JOIN users u ON tc.user_id = u.id
            WHERE tc.task_id = %s
            ORDER BY tc.created_at ASC
        """, (task['id'],))
        task['comments'] = cursor.fetchall()

        # Добавляем can_comment для шаблона
        task['can_comment'] = (
            user_role in ['master', 'submaster', 'creator'] or
            task['assigned_user_id'] == user_id
        )

    # Получаем проект
    cursor.execute("SELECT * FROM projects WHERE id = %s", (project_id,))
    project = cursor.fetchone()
    project['role_name'] = user_role

    cursor.close()
    conn.close()

    return render_template("project_tasks.html", project=project, tasks=tasks)




@app.route('/project/<int:project_id>/task/<int:task_id>', methods=['GET', 'POST'])
def edit_task(project_id, task_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))

    try:
        # Получаем проект и роль пользователя
        cursor.execute("""
            SELECT p.id, p.name, p.description, p.invite_code, r.name AS role_name
            FROM projects p
            JOIN userprojectroles upr ON p.id = upr.project_id
            JOIN roles r ON upr.role_id = r.id
            WHERE p.id = %s AND upr.user_id = %s
        """, (project_id, session['user_id']))
        project = cursor.fetchone()

        if not project:
            flash('Проект не найден или у вас нет доступа', 'danger')
            return redirect(url_for('view_all_projects'))

        user_role = project['role_name']

        # Получаем задачу
        cursor.execute("""
            SELECT t.id, t.name, t.description, t.status, t.proposed_status, t.assigned_user_id, t.creator_user_id, t.start_date, t.deadline
            FROM tasks t
            WHERE t.id = %s AND t.project_id = %s
        """, (task_id, project_id))
        task = cursor.fetchone()

        if not task:
            flash('Задача не найдена', 'danger')
            return redirect(url_for('view_project', project_id=project_id))

        # Проверка прав пользователя
        is_master = user_role in ['master', 'submaster']
        is_creator = task['creator_user_id'] == session['user_id']
        is_assigned = task['assigned_user_id'] == session['user_id']

        if not (is_master or is_creator or is_assigned):
            flash('У вас нет прав на редактирование этой задачи', 'danger')
            return redirect(url_for('view_project', project_id=project_id))

        # Обработка POST-запроса
        if request.method == 'POST':
            action = request.form.get('action')

            # Подтверждение или отклонение предложенного статуса (только мастер/сабмастер)
            if is_master and task['proposed_status'] and task['proposed_status'] != task['status']:
                if action == 'approve':
                    cursor.execute("""
                        UPDATE tasks
                        SET status = %s, proposed_status = NULL
                        WHERE id = %s
                    """, (task['proposed_status'], task_id))
                    conn.commit()
                    flash('Статус задачи обновлён и утверждён.', 'success')
                    return redirect(url_for('view_project', project_id=project_id))

                elif action == 'reject':
                    cursor.execute("""
                        UPDATE tasks
                        SET proposed_status = NULL
                        WHERE id = %s
                    """, (task_id,))
                    conn.commit()
                    flash('Предложенный статус отклонён.', 'info')
                    return redirect(url_for('view_project', project_id=project_id))

            # Обработка изменения задачи
            if is_master or is_creator:
                # Мастер и создатель могут менять название, описание и статус
                title = request.form.get('title')
                description = request.form.get('description')
                status = request.form.get('status')

                cursor.execute("""
                    UPDATE tasks
                    SET name = %s, description = %s, status = %s
                    WHERE id = %s
                """, (title, description, status, task_id))

            elif is_assigned:
                # Назначенный пользователь может предложить статус
                status = request.form.get('status')

                cursor.execute("""
                    UPDATE tasks
                    SET proposed_status = %s
                    WHERE id = %s
                """, (status, task_id))

                flash('Вы предложили новый статус. Он будет отображаться, пока не подтверждён мастером.', 'info')

            else:
                flash('Недостаточно прав для редактирования задачи', 'danger')
                return redirect(url_for('view_project', project_id=project_id))

            conn.commit()
            flash('Задача успешно обновлена!', 'success')
            return redirect(url_for('view_project', project_id=project_id))

        # Помечаем, можно ли редактировать полностью (для шаблона)
        task['is_editable'] = is_master or is_creator

        # Загрузка комментариев
        cursor.execute("""
            SELECT c.comment_text, c.created_at, u.login AS user_name
            FROM task_comments c
            JOIN users u ON c.user_id = u.id
            WHERE c.task_id = %s
            ORDER BY c.created_at ASC
        """, (task_id,))
        comments = cursor.fetchall()

        task['comments'] = comments

        # Проверка возможности комментирования
        task['can_comment'] = (
            is_master or
            is_creator or
            is_assigned
        )

    finally:
        cursor.close()
        conn.close()




    return render_template('view_project.html', project=project, tasks=[task])







@app.route('/audit')
def audit():
    return render_template('audit.html')


from werkzeug.security import check_password_hash, generate_password_hash

@app.route('/myprofile', methods=['GET', 'POST'])
def myprofile():
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    user_id = session['user_id']
    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)

    # Получаем текущие данные
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    if request.method == 'POST':
        # Проверка: это смена пароля?
        if request.form.get('change_password') == '1':
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')

            #  Проверка старого пароля по полю password_hash
            if not check_password_hash(user['password_hash'], current_password):
                flash('Старый пароль неверный', 'danger')
            elif new_password != confirm_password:
                flash('Новый пароль и его подтверждение не совпадают', 'danger')
            else:
                new_hashed = generate_password_hash(new_password)
                cursor.execute("UPDATE users SET password_hash = %s WHERE id = %s", (new_hashed, user_id))
                conn.commit()
                flash('Пароль успешно обновлён', 'success')

        # Обработка фото и обновление данных
        if 'avatar' in request.files:
            file = request.files['avatar']
            if file and file.filename:
                filename = secure_filename(file.filename)
                file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
                user['profile_photo'] = filename

        cursor.execute("""
            UPDATE users SET
                full_name = %s,
                email = %s,
                phone = %s,
                profile_photo = %s
            WHERE id = %s
        """, (
            request.form.get('full_name', user['full_name']),
            request.form.get('email', user['email']),
            request.form.get('phone', user['phone']),
            user['profile_photo'],
            user_id
        ))
        conn.commit()

    # Перезагрузка данных после изменений
    cursor.execute("SELECT * FROM users WHERE id = %s", (user_id,))
    user = cursor.fetchone()

    cursor.close()
    conn.close()
    return render_template('myprofile.html', user=user)


@app.route('/myprojects')
def myprojects():
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    user_id = session['user_id']
    projects = []
    error = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("""
            SELECT 
                p.id, 
                p.name, 
                p.description, 
                r.name AS role_name
            FROM 
                projects p
            JOIN 
                userprojectroles upr ON p.id = upr.project_id
            JOIN 
                roles r ON upr.role_id = r.id
            WHERE 
                upr.user_id = %s
        """, (user_id,))
        projects = cursor.fetchall()

    except Exception as e:
        error = f"Ошибка при загрузке проектов: {str(e)}"

    finally:
        if 'conn' in locals() and conn.is_connected():
            cursor.close()
            conn.close()

    return render_template('myprojects.html', projects=projects, error=error)



@app.route('/project/<int:project_id>/leave', methods=['POST'])
def leave_project(project_id):
    user_id = session.get('user_id')
    if not user_id:
        return redirect(url_for('login'))

    conn = get_db_connection()
    cursor = conn.cursor()

    # Удаляем пользователя из проекта
    cursor.execute("""
        DELETE FROM userprojectroles
        WHERE project_id = %s AND user_id = %s
    """, (project_id, user_id))

    # Добавляем запись в auditlog (если нужно)
    cursor.execute("""
        INSERT INTO auditlog (event_type_id, initiator_id, object_type, affected_object_id, event_time, new_data)
        VALUES ((SELECT id FROM eventtypes WHERE name = 'user_removed'), %s, 'user', %s, NOW(), %s)
    """, (user_id, user_id, json.dumps({'project_id': project_id})))

    conn.commit()
    cursor.close()
    conn.close()

    return redirect(url_for('myprojects'))  # или другой маршрут, куда надо перенаправить



@app.route('/project/<int:project_id>/remove_user/<int:user_id>', methods=['POST'])
def remove_user_from_project(project_id, user_id):
    if 'user_id' not in session:
        return redirect(url_for('LogIn'))

    current_user_id = session['user_id']

    conn = get_db_connection()
    cursor = conn.cursor(dictionary=True)
    initiator_id = int(session['user_id'])
    cursor.execute("SET @current_user_id = %s", (initiator_id,))
    try:
        # Проверим роль текущего пользователя в проекте
        cursor.execute("""
            SELECT r.name FROM userprojectroles upr
            JOIN roles r ON upr.role_id = r.id
            WHERE upr.user_id = %s AND upr.project_id = %s
        """, (current_user_id, project_id))
        role = cursor.fetchone()

        if not role or role['name'] not in ['master', 'submaster']:
            flash("У вас нет прав для удаления участников.")
            return redirect(url_for('view_project', project_id=project_id))

        # Защита: нельзя удалять самого себя
        if current_user_id == user_id:
            flash("Вы не можете удалить самого себя.")
            return redirect(url_for('view_project', project_id=project_id))

        # Удаляем пользователя из проекта
        cursor.execute("""
            DELETE FROM userprojectroles
            WHERE user_id = %s AND project_id = %s
        """, (user_id, project_id))
        conn.commit()
        flash("Пользователь успешно удалён из проекта.")

    except Exception as e:
        conn.rollback()
        flash(f"Ошибка при удалении пользователя: {str(e)}")

    finally:
        cursor.close()
        conn.close()

    return redirect(url_for('view_project', project_id=project_id))


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route("/home")
def HomePage():
    return render_template('homepage.html')

@app.route("/SignUp", methods=['GET', 'POST'])
def Signup():
    error = None
    form_data = {}
    
    if request.method == 'POST':
        # Сохраняем все введённые данные
        form_data = {
            'login': request.form['login'],
            'full_name': request.form['full_name'],
            'email': request.form['Email'],
            'phone': request.form['phone']
        }
        
        password = request.form['password']
        password_repeat = request.form['password_repeat']

        # Проверки
        if password != password_repeat:
            error = "Пароли не совпадают!"
        elif len(password) < 6:
            error = "Пароль должен быть не менее 6 символов"
        else:
            try:
                conn = get_db_connection()
                cursor = conn.cursor(dictionary=True)
                
                # Проверка существующего пользователя
                cursor.execute("""
                    SELECT * FROM users 
                    WHERE login = %s OR email = %s OR phone = %s
                """, (form_data['login'], form_data['email'], form_data['phone']))
                
                if cursor.fetchone():
                    error = "Пользователь с такими данными уже существует"
                else:
                    # Хэширование пароля
                    hashed_password = generate_password_hash(password)
                    
                    # Полная регистрация со всеми полями
                    cursor.execute("""
                        INSERT INTO users (
                            login, 
                            password_hash, 
                            full_name, 
                            email, 
                            phone, 
                            registration_date
                        ) VALUES (%s, %s, %s, %s, %s, %s)
                    """, (
                        form_data['login'],
                        hashed_password,
                        form_data['full_name'],
                        form_data['email'],
                        form_data['phone'],
                        datetime.now().strftime('%Y-%m-%d %H:%M:%S')
                    ))
                    conn.commit()
                    return redirect(url_for('LogIn'))
                    
            except Exception as e:
                error = f"Ошибка сервера: {str(e)}"
            finally:
                if 'conn' in locals() and conn.is_connected():
                    cursor.close()
                    conn.close()
    
    return render_template('create_account.html', error=error, form_data=form_data)
