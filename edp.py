import sqlite3
import streamlit as st
from datetime import datetime
import hashlib
import pandas as pd

# Helper function to hash passwords
def hash_password(password):
    return hashlib.sha256(password.encode()).hexdigest()

# Function to format dates
def format_date(date_str):
    return datetime.strptime(date_str, '%Y-%m-%d').strftime('%d-%m-%Y')

def create_database():
    try:
        conn = sqlite3.connect('edp_shifts.db')
        c = conn.cursor()
        # Create shifts table
        c.execute('''CREATE TABLE IF NOT EXISTS shifts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            date TEXT,
            branch TEXT,
            staff_name TEXT,
            staff_number TEXT,
            mobile_phone TEXT,
            shift_timing TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )''')
        
        # Create users table
        c.execute('''CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE,
            password TEXT,
            role TEXT
        )''')
        
        # Add initial users (branches and admin)
        branches = ['RFT', 'DCN', 'TVK', 'LAL', 'MCR', 'TMF', 'CNT', 'MNP', 'TKI', 'PBR', 'JKM', 'ALR', 'UPM', 'TRR', 'KNM']
        for branch in branches:
            try:
                c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                        (branch, hash_password(branch.lower() + '123'), 'user'))
            except sqlite3.IntegrityError:
                pass # Ignore if user already exists
        
        # Add admin user
        try:
            c.execute('INSERT INTO users (username, password, role) VALUES (?, ?, ?)', 
                    ('admin', hash_password('admin123'), 'admin'))
        except sqlite3.IntegrityError:
            pass # Ignore if user already exists

        conn.commit()
    except sqlite3.Error as e:
        st.error(f"Database error: {e}")
    finally:
        conn.close()

# Initialize database
create_database()

# Connect to the database
def get_db_connection():
    try:
        conn = sqlite3.connect('edp_shifts.db')
        conn.row_factory = sqlite3.Row
        return conn
    except sqlite3.Error as e:
        st.error(f"Database connection error: {e}")
        return None

# User authentication
def authenticate_user(username, password):
    conn = get_db_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM users WHERE username = ? AND password = ?', (username, hash_password(password)))
            user = c.fetchone()
            return user
        except sqlite3.Error as e:
            st.error(f"Authentication error: {e}")
            return None
        finally:
            conn.close()

# Insert shift data into the database
def insert_shift(date, branch, staff_name, staff_number, mobile_phone, shift_timing):
    conn = get_db_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute('''
                INSERT INTO shifts (date, branch, staff_name, staff_number, mobile_phone, shift_timing)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (date, branch, staff_name, staff_number, mobile_phone, shift_timing))
            conn.commit()
        except sqlite3.Error as e:
            st.error(f"Insertion error: {e}")
        finally:
            conn.close()

# Fetch all shift data for admin view
def fetch_all_shifts():
    conn = get_db_connection()
    if conn:
        try:
            c = conn.cursor()
            c.execute('SELECT * FROM shifts ORDER BY date, branch')
            shifts = c.fetchall()
            return shifts
        except sqlite3.Error as e:
            st.error(f"Fetching error: {e}")
            return []
        finally:
            conn.close()

# Set the Streamlit app to wide mode
st.set_page_config(layout="wide")

# Define colors and fonts for styling
title_color = '#1f77b4'  # Blue
subtitle_color = '#333333'
table_header_color = '#f5f5f5'
table_header_font = 'Arial, sans-serif'
table_data_font = 'Arial, sans-serif'

# Title and subtitle
st.markdown(
    f'<h1 style="color:{title_color};">Dashboard</h1>',
    unsafe_allow_html=True
)
st.markdown(
    f'<h3 style="color:{subtitle_color}; font-family:{table_data_font};">'
    'Tamil Nadu State Transport Corporation (KUM) Ltd., Trichy Region</h3>',
    unsafe_allow_html=True
)
st.subheader('EDP Shift Management')

# Login form
if 'username' not in st.session_state:
    st.session_state['username'] = None

if st.session_state['username'] is None:
    st.header('Login')
    with st.form('login_form'):
        username = st.text_input('Username')
        password = st.text_input('Password', type='password')
        submitted = st.form_submit_button('Login')
        
        if submitted:
            user = authenticate_user(username, password)
            if user:
                st.session_state['username'] = user['username']
                st.session_state['role'] = user['role']
                st.success(f'Welcome, {user["username"]}!')
                st.experimental_rerun()  # Reload the page to reflect the login status
            else:
                st.error('Invalid username or password.')
else:
    st.sidebar.header(f'Logged in as {st.session_state["username"]}')
    if st.sidebar.button('Logout'):
        st.session_state['username'] = None
        st.session_state['role'] = None
        st.experimental_rerun()

    # Employee form for shift submission
    if st.session_state['role'] == 'user':
        st.header('Submit Your Shift')
        
        if 'staff_name' not in st.session_state:
            st.session_state['staff_name'] = ''
        if 'staff_number' not in st.session_state:
            st.session_state['staff_number'] = ''
        if 'mobile_phone' not in st.session_state:
            st.session_state['mobile_phone'] = ''
        
        with st.form('shift_form'):
            date = st.date_input('Date', value=datetime.now().date(), help="Select the date of your shift")
            branch = st.session_state['username']
            staff_name = st.text_input('Staff Name', value=st.session_state['staff_name'])
            staff_number = st.text_input('Staff Number', value=st.session_state['staff_number'])
            mobile_phone = st.text_input('Mobile Phone', value=st.session_state['mobile_phone'])
            shift_timing = st.selectbox('Shift Timing', ['6-2', '8-5', '10-6', '2-10', '5-9(DAY/NIGHT)', '10-6(NIGHT)'])
            submitted = st.form_submit_button('Submit')

            if submitted:
                if not (staff_name and staff_number and mobile_phone):
                    st.error('Please fill in all the fields.')
                else:
                    insert_shift(date, branch, staff_name, staff_number, mobile_phone, shift_timing)
                    st.success('Shift data submitted successfully!')
                    # Clear the form fields after submission
                    st.session_state['staff_name'] = ''
                    st.session_state['staff_number'] = ''
                    st.session_state['mobile_phone'] = ''
                    st.query_params.clear()  # Clear query parameters to reset form fields

    # Admin view to see all shifts
    if st.session_state['role'] == 'admin':
        st.header('Admin View - All Shifts')

        if st.button('Load All Shifts'):
            shifts = fetch_all_shifts()
            if shifts:
                df = pd.DataFrame(shifts, columns=['ID', 'Date', 'Branch', 'Staff Name', 'Staff Number', 'Mobile Phone', 'Shift Timing', 'Timestamp'])
                df['Date'] = pd.to_datetime(df['Date'], errors='coerce').dt.strftime('%d-%m-%Y')

                # Display the data table with enhanced alignment and design
                st.markdown('<style>div.row-widget.stRadio > div{flex-direction:row;}</style>', unsafe_allow_html=True)
                st.dataframe(df.style.set_table_styles([
                    {'selector': 'th', 'props': [('background-color', table_header_color), ('color', 'black'),
                                                 ('font-family', table_header_font), ('font-weight', 'bold')]},
                    {'selector': 'td', 'props': [('color', 'black'), ('font-family', table_data_font)]},
                    {'selector': 'tr:hover td', 'props': [('background-color', '#e6e6e6')]}
                ]).set_properties(**{'text-align': 'center', 'border-collapse': 'collapse', 'border': '1px solid #cccccc'}))
            else:
                st.write('No shifts found.')
