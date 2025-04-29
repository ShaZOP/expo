import streamlit as st
import mysql.connector
from mysql.connector import Error
from datetime import datetime
import os
from PIL import Image
import io

# Create uploads directory if it doesn't exist
if not os.path.exists('uploads'):
    os.makedirs('uploads')

# Initialize connection
def init_connection():
    return mysql.connector.connect(
        host='localhost',
        user='root',
        password='root',
        database='sbms',
        pool_name='mypool',
        pool_size=5,
        connect_timeout=30,
        autocommit=True
    )

# Get connection from pool
def get_connection():
    try:
        return mysql.connector.connect(
            pool_name='mypool',
            pool_size=5
        )
    except mysql.connector.Error as err:
        if err.errno == mysql.connector.errorcode.ER_ACCESS_DENIED_ERROR:
            st.error("Something is wrong with your user name or password")
        elif err.errno == mysql.connector.errorcode.ER_BAD_DB_ERROR:
            st.error("Database does not exist")
        else:
            st.error(err)
        return None

def init_db():
    conn = init_connection()
    try:
        cursor = conn.cursor()
        
        # Drop existing tables if they exist
        cursor.execute("DROP TABLE IF EXISTS lost_items")
        cursor.execute("DROP TABLE IF EXISTS complaints")
        cursor.execute("DROP TABLE IF EXISTS users")
        st.success("✅ Old tables dropped successfully!")
        
        # Create users table with points
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                id INT AUTO_INCREMENT PRIMARY KEY,
                username VARCHAR(80) UNIQUE NOT NULL,
                password VARCHAR(120) NOT NULL,
                role VARCHAR(20) NOT NULL,
                department VARCHAR(50),
                points INT DEFAULT 0
            )
        """)
        st.success("✅ Users table created successfully!")
        
        # Create complaints table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS complaints (
                id INT AUTO_INCREMENT PRIMARY KEY,
                title VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                category VARCHAR(50) NOT NULL,
                priority VARCHAR(20) NOT NULL,
                status VARCHAR(20) DEFAULT 'Pending Admin Review',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INT NOT NULL,
                assigned_to INT,
                admin_notes TEXT,
                officer_notes TEXT,
                image_path VARCHAR(255),
                points_awarded BOOLEAN DEFAULT FALSE,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (assigned_to) REFERENCES users(id)
            )
        """)
        st.success("✅ Complaints table created successfully!")
        
        # Create lost items table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS lost_items (
                id INT AUTO_INCREMENT PRIMARY KEY,
                item_name VARCHAR(100) NOT NULL,
                description TEXT NOT NULL,
                lost_time DATETIME NOT NULL,
                lost_place VARCHAR(100) NOT NULL,
                status VARCHAR(20) DEFAULT 'Lost',
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                user_id INT NOT NULL,
                admin_notes TEXT,
                image_path VARCHAR(255),
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        """)
        st.success("✅ Lost items table created successfully!")
        
        # Insert default users if they don't exist
        default_users = [
            ('admin', 'admin', 'admin', 'Administration', 0),
            ('electrician', 'electrician', 'officer', 'Electrical', 0),
            ('plumber', 'plumber', 'officer', 'Plumbing', 0),
            ('maintenance', 'maintenance', 'officer', 'Maintenance', 0),
            ('it', 'it', 'officer', 'IT', 0),
            ('security', 'security', 'officer', 'Security', 0),
            ('student', 'student', 'student', 'Student', 0)
        ]
        
        for username, password, role, department, points in default_users:
            cursor.execute("""
                INSERT IGNORE INTO users (username, password, role, department, points)
                VALUES (%s, %s, %s, %s, %s)
            """, (username, password, role, department, points))
        
        conn.commit()
        st.success("✅ Default users created successfully!")
        st.success("🎉 Database initialized successfully!")
    except Error as e:
        st.error(f'Error: {e}')
    finally:
        cursor.close()
        conn.close()

def award_points(user_id, points):
    conn = get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE users 
            SET points = points + %s
            WHERE id = %s
        """, (points, user_id))
    except Error as e:
        st.error(f'Error awarding points: {e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def get_leaderboard():
    conn = get_connection()
    if not conn:
        return []
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("""
            SELECT username, points, role
            FROM users
            WHERE role = 'student'
            ORDER BY points DESC
            LIMIT 10
        """)
        leaderboard = cursor.fetchall()
        return leaderboard if leaderboard else []
    except Error as e:
        st.error(f'Error getting leaderboard: {e}')
        return []
    finally:
        cursor.close()
        conn.close()

def login(username, password):
    conn = init_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM users WHERE username = %s AND password = %s", (username, password))
        user = cursor.fetchone()
        if user:
            st.success("✅ Login successful!")
        return user
    except Error as e:
        st.error(f'Error: {e}')
        return None
    finally:
        cursor.close()
        conn.close()

def get_user_complaints(user_id, role):
    conn = init_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute("""
                SELECT c.*, u1.username as reporter, u2.username as assigned_to_name
                FROM complaints c
                LEFT JOIN users u1 ON c.user_id = u1.id
                LEFT JOIN users u2 ON c.assigned_to = u2.id
                ORDER BY c.created_at DESC
            """)
        elif role == 'officer':
            cursor.execute("""
                SELECT c.*, u1.username as reporter, u2.username as assigned_to_name
                FROM complaints c
                LEFT JOIN users u1 ON c.user_id = u1.id
                LEFT JOIN users u2 ON c.assigned_to = u2.id
                WHERE c.assigned_to = %s
                ORDER BY c.created_at DESC
            """, (user_id,))
        else:  # student
            cursor.execute("""
                SELECT c.*, u1.username as reporter, u2.username as assigned_to_name
                FROM complaints c
                LEFT JOIN users u1 ON c.user_id = u1.id
                LEFT JOIN users u2 ON c.assigned_to = u2.id
                WHERE c.user_id = %s
                ORDER BY c.created_at DESC
            """, (user_id,))
        return cursor.fetchall()
    except Error as e:
        st.error(f'Error: {e}')
        return []
    finally:
        cursor.close()
        conn.close()

def get_officers():
    conn = init_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, username, department FROM users WHERE role = 'officer'")
        return cursor.fetchall()
    except Error as e:
        st.error(f'Error: {e}')
        return []
    finally:
        cursor.close()
        conn.close()

def get_officer_by_department(department):
    conn = init_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id FROM users WHERE role = 'officer' AND department = %s", (department,))
        officer = cursor.fetchone()
        return officer['id'] if officer else None
    except Error as e:
        st.error(f'Error: {e}')
        return None
    finally:
        cursor.close()
        conn.close()

def save_uploaded_file(uploaded_file):
    try:
        # Create a unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        file_extension = os.path.splitext(uploaded_file.name)[1]
        filename = f"{timestamp}{file_extension}"
        file_path = os.path.join('uploads', filename)
        
        # Save the file
        with open(file_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        return file_path
    except Exception as e:
        st.error(f"Error saving file: {e}")
        return None

def submit_new_complaint(title, description, category, priority, user_id, image_file=None):
    conn = get_connection()
    if not conn:
        return
    try:
        cursor = conn.cursor()
        
        # Map category to department
        category_to_department = {
            'Electrical Issues': 'Electrical',
            'Water & Sanitation': 'Plumbing',
            'Faulty Infrastructure': 'Maintenance',
            'Internet & Network': 'IT',
            'Security Concerns': 'Security'
        }
        
        department = category_to_department.get(category)
        assigned_to = get_officer_by_department(department) if department else None
        
        # Save image if provided
        image_path = None
        if image_file is not None:
            image_path = save_uploaded_file(image_file)
            st.success("✅ Image uploaded successfully!")
        
        cursor.execute("""
            INSERT INTO complaints (title, description, category, priority, user_id, status, assigned_to, image_path)
            VALUES (%s, %s, %s, %s, %s, 'Pending Admin Review', %s, %s)
        """, (title, description, category, priority, user_id, assigned_to, image_path))
        
        # Award 1 point for submitting a complaint
        award_points(user_id, 1)
        
        if assigned_to:
            st.success("✅ Complaint submitted successfully!")
            st.success("🎉 You earned 1 point for submitting the complaint!")
            st.success("📝 Your complaint will be reviewed by the admin and automatically assigned to the appropriate department.")
        else:
            st.success("✅ Complaint submitted successfully!")
            st.success("🎉 You earned 1 point for submitting the complaint!")
            st.success("📝 Your complaint will be reviewed by the admin.")
    except Error as e:
        st.error(f'Error: {e}')
        conn.rollback()
    finally:
        cursor.close()
        conn.close()

def update_complaint_status(complaint_id, status, notes=None, assigned_to=None, is_admin=False):
    conn = init_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        
        # Get the current complaint status and user_id
        cursor.execute("SELECT status, user_id, points_awarded FROM complaints WHERE id = %s", (complaint_id,))
        complaint = cursor.fetchone()
        
        if complaint:
            # If status is changing to Resolved and points haven't been awarded yet
            if status == 'Resolved' and not complaint['points_awarded']:
                # Award 3 points for resolution
                award_points(complaint['user_id'], 3)
                cursor.execute("""
                    UPDATE complaints 
                    SET status = %s, assigned_to = %s, admin_notes = %s, points_awarded = TRUE
                    WHERE id = %s
                """, (status, assigned_to, notes, complaint_id))
                st.success("✅ Complaint marked as resolved!")
                st.success("🎉 Student awarded 3 points for resolution!")
            else:
                cursor.execute("""
                    UPDATE complaints 
                    SET status = %s, assigned_to = %s, admin_notes = %s
                    WHERE id = %s
                """, (status, assigned_to, notes, complaint_id))
                st.success(f"✅ Status updated to {status}!")
        
        conn.commit()
    except Error as e:
        st.error(f'Error: {e}')
    finally:
        cursor.close()
        conn.close()

def submit_lost_item(item_name, description, lost_time, lost_place, user_id, image_file=None):
    conn = init_connection()
    try:
        cursor = conn.cursor()
        
        # Save image if provided
        image_path = None
        if image_file is not None:
            image_path = save_uploaded_file(image_file)
            st.success("✅ Image uploaded successfully!")
        
        cursor.execute("""
            INSERT INTO lost_items (item_name, description, lost_time, lost_place, user_id, image_path)
            VALUES (%s, %s, %s, %s, %s, %s)
        """, (item_name, description, lost_time, lost_place, user_id, image_path))
        
        conn.commit()
        st.success("✅ Lost item reported successfully!")
        st.success("📝 The admin will review your report.")
    except Error as e:
        st.error(f'Error: {e}')
    finally:
        cursor.close()
        conn.close()

def get_lost_items(user_id, role):
    conn = init_connection()
    try:
        cursor = conn.cursor(dictionary=True)
        if role == 'admin':
            cursor.execute("""
                SELECT l.*, u.username as reporter
                FROM lost_items l
                LEFT JOIN users u ON l.user_id = u.id
                ORDER BY l.created_at DESC
            """)
        else:  # student
            cursor.execute("""
                SELECT l.*, u.username as reporter
                FROM lost_items l
                LEFT JOIN users u ON l.user_id = u.id
                WHERE l.user_id = %s
                ORDER BY l.created_at DESC
            """, (user_id,))
        return cursor.fetchall()
    except Error as e:
        st.error(f'Error: {e}')
        return []
    finally:
        cursor.close()
        conn.close()

def update_lost_item_status(item_id, status, notes=None):
    conn = init_connection()
    try:
        cursor = conn.cursor()
        cursor.execute("""
            UPDATE lost_items 
            SET status = %s, admin_notes = %s
            WHERE id = %s
        """, (status, notes, item_id))
        conn.commit()
        st.success(f"✅ Item status updated to {status}!")
        if notes:
            st.success("📝 Notes added successfully!")
    except Error as e:
        st.error(f'Error: {e}')
    finally:
        cursor.close()
        conn.close()

# Initialize session state
if 'user' not in st.session_state:
    st.session_state.user = None

# Sidebar for login/logout
with st.sidebar:
    if st.session_state.user is None:
        st.title('Login')
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        if st.button('Login'):
            user = login(username, password)
            if user:
                st.session_state.user = user
                st.rerun()
            else:
                st.error('Invalid username or password')
    else:
        st.write(f'Welcome, {st.session_state.user["username"]}!')
        st.write(f'Role: {st.session_state.user["role"]}')
        if st.session_state.user['role'] == 'officer':
            st.write(f'Department: {st.session_state.user["department"]}')
        if st.button('Logout'):
            st.session_state.user = None
            st.rerun()

# Main content
if st.session_state.user is None:
    st.title('Smart Building Management System')
    st.write('Please login to continue')
    
    # Initialize database button (only visible when not logged in)
    if st.button('Initialize Database'):
        init_db()
else:
    st.title('Smart Building Management System')
    
    # Show points and leaderboard for students
    if st.session_state.user['role'] == 'student':
        st.sidebar.markdown("### 🏆 Your Points")
        st.sidebar.markdown(f"### {st.session_state.user['points']} points")
        
        st.sidebar.markdown("### 🏅 Leaderboard")
        leaderboard = get_leaderboard()
        for i, student in enumerate(leaderboard, 1):
            medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
            st.sidebar.markdown(f"{medal} {student['username']}: {student['points']} points")
        
        if leaderboard and leaderboard[0]['username'] == st.session_state.user['username']:
            st.sidebar.success("🎉 Congratulations! You're the top scorer!")
    
    # Create tabs for different features
    if st.session_state.user['role'] == 'student':
        tab1, tab2, tab3 = st.tabs(["Complaints", "Lost & Found", "Leaderboard"])
    else:
        tab1, tab2, tab3 = st.tabs(["Complaints", "Lost & Found", "Leaderboard"])
    
    with tab1:
        # Existing complaint submission and display code
        complaint_submitted = False
        with st.expander('Submit New Complaint', expanded=not complaint_submitted):
            title = st.text_input('Title', key='complaint_title')
            description = st.text_area('Description', key='complaint_description')
            category = st.selectbox('Category', [
                'Electrical Issues',
                'Water & Sanitation',
                'Faulty Infrastructure',
                'Internet & Network',
                'Security Concerns'
            ], key='complaint_category')
            priority = st.selectbox('Priority', ['Urgent', 'High', 'Medium', 'Low'], key='complaint_priority')
            
            # Add image upload for students
            if st.session_state.user['role'] == 'student':
                image_file = st.file_uploader("Upload Image (optional)", type=['jpg', 'jpeg', 'png'], key='complaint_image')
            else:
                image_file = None
            
            if st.button('Submit Complaint', key='submit_complaint'):
                if title and description:
                    submit_new_complaint(title, description, category, priority, st.session_state.user['id'], image_file)
                    complaint_submitted = True
                    st.rerun()
                else:
                    st.error('Please fill in all required fields')
        
        # Existing complaint display code
        st.header('Complaints')
        complaints = get_user_complaints(st.session_state.user['id'], st.session_state.user['role'])
        
        if complaints:
            # For students, show a summary of their complaints
            if st.session_state.user['role'] == 'student':
                # Create tabs for different statuses
                tab1, tab2, tab3, tab4 = st.tabs(["All Complaints", "Pending", "In Progress", "Resolved/Closed"])
                
                with tab1:
                    st.subheader("All Your Complaints")
                    for complaint in complaints:
                        with st.container():
                            st.markdown(f"### {complaint['title']}")
                            col1, col2 = st.columns([2,1])
                            with col1:
                                st.write(complaint['description'])
                                if complaint['image_path'] and os.path.exists(complaint['image_path']):
                                    try:
                                        image = Image.open(complaint['image_path'])
                                        st.image(image, caption='Complaint Image', use_container_width=True)
                                    except Exception as e:
                                        st.error(f"Error displaying image: {e}")
                            with col2:
                                st.write(f"**Category:** {complaint['category']}")
                                st.write(f"**Priority:** {complaint['priority']}")
                                st.write(f"**Status:** {complaint['status']}")
                                if complaint['assigned_to_name']:
                                    st.write(f"**Assigned to:** {complaint['assigned_to_name']}")
                                if complaint['admin_notes']:
                                    st.write(f"**Admin Notes:** {complaint['admin_notes']}")
                                if complaint['officer_notes']:
                                    st.write(f"**Officer Notes:** {complaint['officer_notes']}")
                                st.write(f"**Created:** {complaint['created_at']}")
                            st.divider()
                
                with tab2:
                    pending = [c for c in complaints if c['status'] == 'Pending Admin Review']
                    if pending:
                        for complaint in pending:
                            with st.container():
                                st.markdown(f"### {complaint['title']}")
                                col1, col2 = st.columns([2,1])
                                with col1:
                                    st.write(complaint['description'])
                                    if complaint['image_path'] and os.path.exists(complaint['image_path']):
                                        try:
                                            image = Image.open(complaint['image_path'])
                                            st.image(image, caption='Complaint Image', use_container_width=True)
                                        except Exception as e:
                                            st.error(f"Error displaying image: {e}")
                                with col2:
                                    st.write(f"**Category:** {complaint['category']}")
                                    st.write(f"**Priority:** {complaint['priority']}")
                                    st.write(f"**Created:** {complaint['created_at']}")
                                st.divider()
                    else:
                        st.info("No pending complaints")
                
                with tab3:
                    in_progress = [c for c in complaints if c['status'] == 'In Progress']
                    if in_progress:
                        for complaint in in_progress:
                            with st.container():
                                st.markdown(f"### {complaint['title']}")
                                col1, col2 = st.columns([2,1])
                                with col1:
                                    st.write(complaint['description'])
                                    if complaint['image_path'] and os.path.exists(complaint['image_path']):
                                        try:
                                            image = Image.open(complaint['image_path'])
                                            st.image(image, caption='Complaint Image', use_container_width=True)
                                        except Exception as e:
                                            st.error(f"Error displaying image: {e}")
                                with col2:
                                    st.write(f"**Category:** {complaint['category']}")
                                    st.write(f"**Priority:** {complaint['priority']}")
                                    st.write(f"**Assigned to:** {complaint['assigned_to_name']}")
                                    if complaint['officer_notes']:
                                        st.write(f"**Officer Notes:** {complaint['officer_notes']}")
                                    st.write(f"**Created:** {complaint['created_at']}")
                                st.divider()
                    else:
                        st.info("No complaints in progress")
                
                with tab4:
                    resolved = [c for c in complaints if c['status'] in ['Resolved', 'Closed']]
                    if resolved:
                        for complaint in resolved:
                            with st.container():
                                st.markdown(f"### {complaint['title']}")
                                col1, col2 = st.columns([2,1])
                                with col1:
                                    st.write(complaint['description'])
                                    if complaint['image_path'] and os.path.exists(complaint['image_path']):
                                        try:
                                            image = Image.open(complaint['image_path'])
                                            st.image(image, caption='Complaint Image', use_container_width=True)
                                        except Exception as e:
                                            st.error(f"Error displaying image: {e}")
                                with col2:
                                    st.write(f"**Category:** {complaint['category']}")
                                    st.write(f"**Priority:** {complaint['priority']}")
                                    st.write(f"**Status:** {complaint['status']}")
                                    st.write(f"**Assigned to:** {complaint['assigned_to_name']}")
                                    if complaint['admin_notes']:
                                        st.write(f"**Admin Notes:** {complaint['admin_notes']}")
                                    if complaint['officer_notes']:
                                        st.write(f"**Officer Notes:** {complaint['officer_notes']}")
                                    st.write(f"**Created:** {complaint['created_at']}")
                                st.divider()
                    else:
                        st.info("No resolved or closed complaints")
            else:
                # Existing display for admin and officers
                for complaint in complaints:
                    with st.container():
                        col1, col2, col3 = st.columns([2,1,1])
                        with col1:
                            st.subheader(complaint['title'])
                            st.write(complaint['description'])
                            st.write(f"Reported by: {complaint['reporter']}")
                            
                            if complaint['image_path'] and os.path.exists(complaint['image_path']):
                                try:
                                    image = Image.open(complaint['image_path'])
                                    st.image(image, caption='Complaint Image', use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error displaying image: {e}")
                            
                            if complaint['admin_notes']:
                                st.write(f"Admin Notes: {complaint['admin_notes']}")
                            if complaint['officer_notes']:
                                st.write(f"Officer Notes: {complaint['officer_notes']}")
                        with col2:
                            st.write(f"Category: {complaint['category']}")
                            st.write(f"Priority: {complaint['priority']}")
                            if complaint['assigned_to_name']:
                                st.write(f"Assigned to: {complaint['assigned_to_name']}")
                        with col3:
                            if st.session_state.user['role'] in ['admin', 'officer']:
                                status = st.selectbox(
                                    'Status',
                                    ['Pending Admin Review', 'In Progress', 'Resolved', 'Closed'],
                                    index=['Pending Admin Review', 'In Progress', 'Resolved', 'Closed'].index(complaint['status']),
                                    key=f'status_{complaint["id"]}'
                                )
                                notes = st.text_area('Notes', key=f'notes_{complaint["id"]}')
                                
                                if status != complaint['status'] or notes:
                                    if st.session_state.user['role'] == 'admin':
                                        if st.button('Update', key=f'update_{complaint["id"]}'):
                                            update_complaint_status(complaint['id'], status, notes, is_admin=True)
                                            st.rerun()
                                    else:  # officer
                                        if st.button('Update', key=f'update_{complaint["id"]}'):
                                            update_complaint_status(complaint['id'], status, notes)
                                            st.rerun()
                            else:
                                st.write(f"Status: {complaint['status']}")
                            st.write(f"Created: {complaint['created_at']}")
                        st.divider()
        else:
            st.info('No complaints found')
    
    with tab2:
        if st.session_state.user['role'] == 'student':
            # Student view for lost items
            with st.expander('Report Lost Item'):
                item_name = st.text_input('Item Name', key='lost_item_name')
                description = st.text_area('Description', key='lost_item_description')
                
                # Date and time inputs
                col1, col2 = st.columns(2)
                with col1:
                    date = st.date_input('Date Lost', key='lost_item_date')
                with col2:
                    time = st.time_input('Time Lost', key='lost_item_time')
                
                lost_time = datetime.combine(date, time)
                lost_place = st.text_input('Where did you lose it?', key='lost_item_place')
                image_file = st.file_uploader("Upload Image of the Item (optional)", type=['jpg', 'jpeg', 'png'], key='lost_item_image')
                
                if st.button('Submit Lost Item', key='submit_lost_item'):
                    if item_name and description and lost_place:
                        submit_lost_item(item_name, description, lost_time, lost_place, st.session_state.user['id'], image_file)
                    else:
                        st.error('Please fill in all required fields')
            
            # Display student's lost items
            st.header('Your Lost Items')
            lost_items = get_lost_items(st.session_state.user['id'], st.session_state.user['role'])
            if lost_items:
                for item in lost_items:
                    with st.container():
                        st.markdown(f"### {item['item_name']}")
                        col1, col2 = st.columns([2,1])
                        with col1:
                            st.write(item['description'])
                            if item['image_path'] and os.path.exists(item['image_path']):
                                try:
                                    image = Image.open(item['image_path'])
                                    st.image(image, caption='Item Image', use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error displaying image: {e}")
                        with col2:
                            st.write(f"**Status:** {item['status']}")
                            st.write(f"**Lost Time:** {item['lost_time']}")
                            st.write(f"**Lost Place:** {item['lost_place']}")
                            if item['admin_notes']:
                                st.write(f"**Admin Notes:** {item['admin_notes']}")
                            st.write(f"**Reported:** {item['created_at']}")
                        st.divider()
            else:
                st.info('No lost items reported')
        else:
            # Admin view for lost items
            st.header('Lost & Found Management')
            lost_items = get_lost_items(None, 'admin')
            if lost_items:
                for item in lost_items:
                    with st.container():
                        st.markdown(f"### {item['item_name']}")
                        col1, col2 = st.columns([2,1])
                        with col1:
                            st.write(item['description'])
                            if item['image_path'] and os.path.exists(item['image_path']):
                                try:
                                    image = Image.open(item['image_path'])
                                    st.image(image, caption='Item Image', use_container_width=True)
                                except Exception as e:
                                    st.error(f"Error displaying image: {e}")
                        with col2:
                            # Create a form for each item to handle status updates
                            with st.form(key=f'form_{item["id"]}'):
                                status = st.selectbox(
                                    'Status',
                                    ['Lost', 'Found', 'Collected'],
                                    index=['Lost', 'Found', 'Collected'].index(item['status']),
                                    key=f'status_{item["id"]}'
                                )
                                notes = st.text_area('Notes', value=item['admin_notes'] if item['admin_notes'] else '', key=f'notes_{item["id"]}')
                                
                                submit_button = st.form_submit_button('Update Status')
                                if submit_button:
                                    update_lost_item_status(item['id'], status, notes)
                                    st.rerun()
                            
                            st.write(f"**Reported by:** {item['reporter']}")
                            st.write(f"**Lost Time:** {item['lost_time']}")
                            st.write(f"**Lost Place:** {item['lost_place']}")
                            st.write(f"**Reported:** {item['created_at']}")
                        st.divider()
            else:
                st.info('No lost items reported')
    
    with tab3:
        st.header("🏆 Leaderboard")
        leaderboard = get_leaderboard()
        if leaderboard:
            for i, student in enumerate(leaderboard, 1):
                medal = "🥇" if i == 1 else "🥈" if i == 2 else "🥉" if i == 3 else f"{i}."
                st.markdown(f"### {medal} {student['username']}")
                st.markdown(f"**Points:** {student['points']}")
                if i == 1:
                    st.success("🌟 Top scorer! Eligible for monthly prize!")
                st.divider()
        else:
            st.info("No students have earned points yet.") 