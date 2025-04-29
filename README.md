# Smart Building Management System (SBMS)

A Flask-based web application for managing infrastructure grievances in educational institutions.

## Features

- User roles: Admin, Student, and Workers (e.g., Plumber)
- Grievance reporting portal
- Fault categorization and prioritization
- Live status tracking
- Automated ticket system

## Setup

1. **Install Dependencies**

   ```bash
   pip install -r requirements.txt
   ```

2. **Database Setup**

   - Ensure MySQL is running with user `root` and password `root`.
   - Create a database named `sbms`:

     ```sql
     CREATE DATABASE sbms;
     ```

3. **Initialize the Database**

   - Run the Flask app and visit `http://localhost:5000/init_db` to create tables and default users.

4. **Run the Application**

   ```bash
   python app.py
   ```

   The app will be available at `http://localhost:5000`.

## Default Users

- **Admin**: username: `admin`, password: `admin`
- **Student**: username: `student`, password: `student`
- **Plumber**: username: `plumber`, password: `plumber`

## Usage

1. **Login**: Use the default credentials to log in.
2. **Dashboard**: View and manage complaints.
3. **Submit Complaint**: Report new infrastructure issues.

## License

MIT 