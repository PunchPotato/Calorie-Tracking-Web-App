from email.mime.text import MIMEText
import re
import secrets
import smtplib
import string
import time
from flask import Flask, redirect, render_template, request, session, url_for
import pymysql
import os

class Database:
    def __init__(self):
        self.connection = pymysql.connect(host='localhost', user='root', password=os.environ.get('MYSQL_PASSWORD'))
        self.cursor = self.connection.cursor()
        self.create_database()
        self.use_database()

    def create_database(self):
        query = 'CREATE DATABASE IF NOT EXISTS mydatabase'
        self.cursor.execute(query)

    def use_database(self):
        query = 'USE mydatabase'
        self.cursor.execute(query)

    def close(self):
        self.connection.close()

class UserAuthentication:
    def __init__(self):
        self.db = Database()

    def check_credentials(self, username, password):
        query = 'SELECT * FROM user_data WHERE username = %s AND password = %s'
        self.db.cursor.execute(query, (username, password))
        row = self.db.cursor.fetchone()
        return row is not None

    def create_user(self, email, username, password):
        query = 'INSERT INTO user_data (email, username, password) VALUES (%s, %s, %s)'
        self.db.cursor.execute(query, (email, username, password))
        self.db.connection.commit()

app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(16)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username_entered_text = request.form.get('usernametextbox')
        password_entered_text = request.form.get('passwordtextbox')
        
        if username_entered_text == '' or password_entered_text == '':
            error_message = "Field cannot be empty"
            return render_template('login.html', error_message=error_message)
        
        auth = UserAuthentication()
        if auth.check_credentials(username_entered_text, password_entered_text):
            return redirect(url_for('calories'))
        else:
            return render_template('login.html', error_message="Invalid username or password")
    
    return render_template('login.html', entered_text=None)

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username_entered_text = request.form.get('usernametextbox')
        email_entered_text = request.form.get('emailtextbox')
        password_entered_text = request.form.get('passwordtextbox')
        comfirm_password_entered_text = request.form.get('comfirmpasswordtextbox')
        checkbox_value = request.form.get('checkbox_name')

        if email_entered_text == '' or username_entered_text == '' or password_entered_text == '' or\
                comfirm_password_entered_text == '':
            return render_template('signup.html', error_message="Field(s) cannot be empty")
        
        if comfirm_password_entered_text != password_entered_text:
            return render_template('signup.html', error_message="Error, Passwords do not match.")
        
        if checkbox_value != 'checkbox_value':
            return render_template('signup.html', error_message="Accept Terms & Conditions.")
        
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if not re.match(email_pattern, email_entered_text):
            return render_template('signup.html', error_message="Error, Email not valid.")
        
        if len(password_entered_text) <= 5 or not any(char.isupper() for char in password_entered_text):
            return render_template('signup.html', error_message="Error, Password needs to be longer than 5 characters and include a capital letter.")
        
        auth = UserAuthentication()
        try:
            auth.create_user(email_entered_text, username_entered_text, password_entered_text)
            return render_template('login.html')
        except pymysql.Error as e:
            return render_template('signup.html', error_message=f"Error: Failed to connect to the database. Error: {str(e)}")
    
    return render_template('signup.html')

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
        email = request.form.get('emailtextbox')
        session['temp_email'] = email

        if email == '':
            return render_template('forgotpassword.html', error_message="Error, all fields must be filled.")

        con = None
        my_cursor = None
        try:
            con = pymysql.connect(host='localhost', user='root', password=os.environ.get('MYSQL_PASSWORD'),
                                database='mydatabase')
            my_cursor = con.cursor()

            query = 'SELECT * FROM user_data WHERE email = %s'
            my_cursor.execute(query, (email,))
            row = my_cursor.fetchone()

            if row is None:
                return render_template('forgotpassword.html', error_message="Error, Email is not valid")
            else:
                random_code = generate_one_time_code()

                update_query = "UPDATE user_data SET one_time_codes = %s, created_at = %s WHERE email = %s"
                current_timestamp = int(time.time())  # Get the current timestamp
                my_cursor.execute(update_query, (random_code, current_timestamp, email))
                con.commit()

                if send_email(email, random_code):
                    return redirect(url_for('resetpassword'))
                else:
                    return render_template('forgotpassword.html', error_message="Error, Failed to send email")

        except pymysql.Error as e:
            return render_template('forgotpassword.html', error_message="Error, Failed to connect to the database:"  + str(e))

        finally:
            try:
                if my_cursor is not None:
                    my_cursor.close()
                if con is not None:
                    con.close()
            except pymysql.Error:
                pass

    return render_template('forgotpassword.html')

def generate_one_time_code(length=6):
            characters = string.ascii_letters + string.digits
            one_time_code = ''.join(secrets.choice(characters) for _ in range(length))
            return one_time_code

def send_email(to_address, one_time_code):
    smtp_server = os.environ.get('SMPT_SERVER')
    smtp_port = int(os.environ.get('SMPT_PORT'))
    sender_email = os.environ.get('MY_EMAIL')
    sender_password = os.environ.get('MY_PASSWORD')
    
    random_code = one_time_code
    subject = 'Reset your password'
    message = str(random_code)

    msg = MIMEText(message)
    msg['Subject'] = subject
    msg['From'] = sender_email
    msg['To'] = to_address

    try:
        # Connect to the SMTP server and start TLS encryption
        server = smtplib.SMTP(smtp_server, smtp_port)
        server.starttls()

        # Login to the SMTP server using your email and password
        server.login(sender_email, sender_password)

        # Send the email
        server.sendmail(sender_email, to_address, msg.as_string())

        # Close the connection to the SMTP server
        server.quit()

        return True
    except smtplib.SMTPException as e:
        return render_template('forgotpassword.html', error_message=f"Failed to connect. Error: {str(e)}")
        

def delete_expired_codes():
    con = None
    my_cursor = None
    try:
        con = pymysql.connect(host='localhost', user='root', password=os.environ.get('MYSQL_PASSWORD'),
                            database='mydatabase')
        my_cursor = con.cursor()

        # Calculate the timestamp for 5 minutes ago
        five_minutes_ago = int(time.time()) - (5 * 60)

        # Delete the expired codes from the database
        delete_query = "DELETE FROM one_time_codes WHERE created_at <= %s"
        my_cursor.execute(delete_query, (five_minutes_ago,))
        con.commit()

    except pymysql.Error as e:
        print("Failed to connect to the database:", str(e))

    finally:
        try:
            if my_cursor is not None:
                my_cursor.close()
            if con is not None:
                con.close()
        except pymysql.Error:
            pass


@app.route('/resetpassword', methods=['GET', 'POST'])
def resetpassword():
    if request.method == 'POST':
        entered_code = request.form.get('codetextbox')
        entered_password = request.form.get('passwordtextbox')
        entered_comfirm_password = request.form.get('comfirmpasswordtextbox')
        email = session.get('temp_email', None)
        print("Entered code:", entered_code)

        if entered_code == '' or entered_password == '' or entered_comfirm_password == '':
            return render_template('resetpassword.html', error_message="Error, All fields must be filled.")
        
        elif entered_password != entered_comfirm_password:
            return render_template('resetpassword.html', error_message="Error, Password must match.")

        elif len(entered_password) < 5 or not any(char.isupper() for char in entered_password) or len(entered_comfirm_password) < 5 or not any(char.isupper() for char in entered_comfirm_password):
           return render_template('resetpassword.html', error_message="Error, Password needs to be longer than 5 characters and include a capital letter.")

        
        try:
            con = pymysql.connect(host='localhost', user='root', password=os.environ.get('MYSQL_PASSWORD'),
                                database='mydatabase')
            with con:
                my_cursor = con.cursor()

                query = "SELECT email FROM user_data WHERE email = %s AND one_time_codes = %s"
                my_cursor.execute(query, (email, entered_code))
                row = my_cursor.fetchone()

                if row:
                    query = "UPDATE user_data SET password = %s WHERE email = %s"
                    my_cursor.execute(query, (entered_password, email))
                    con.commit()

                    return render_template('login.html')
                else:
                    return render_template('resetpassword.html', error_message='Error, Invalid code or email. Please try again.')

        except pymysql.Error as e:
            return render_template('resetpassword.html', error_message="Error, Failed to connect to the database: " + str(e))
        
        except Exception as e:
            return render_template('resetpassword.html', error_message="Error, An error occurred. Please try again.")


        finally:
            try:
                if my_cursor:
                    my_cursor.close()
                if con:
                    con.close()
            except pymysql.Error:
                pass
    return render_template('resetpassword.html')

@app.route('/calories')
def calories():
    return render_template('calories.html')

if __name__ == '__main__':
    app.run(debug=True)