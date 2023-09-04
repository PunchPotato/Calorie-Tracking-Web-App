from email.mime.text import MIMEText
import re
import secrets
import smtplib
import string
import time
from flask import Flask, redirect, render_template, request, url_for
import pymysql
import os

app = Flask(__name__, static_folder='static')

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
        
        try:
            con = pymysql.connect(host='localhost', user='root', password=os.environ.get('MYSQL_PASSWORD'))
            my_cursor = con.cursor()
            query = 'use mydatabase'
            my_cursor.execute(query)
            query = 'select * from user_data where username = %s and password = %s'
            my_cursor.execute(query, (username_entered_text, password_entered_text))
            row = my_cursor.fetchone()
            if row is None:
                return render_template('login.html', error_message="Invalid username or password")
            else:
                return redirect(url_for('success'))
        except:
            return render_template('login.html', error_message="Database connection error")
        finally:
            if con:
                con.close()
                my_cursor.close()

    else:
        return render_template('login.html', entered_text=None)
        

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    checkbox_value = request.form.get('checkbox_name')
    if request.method == 'POST':
        username_entered_text = request.form.get('usernametextbox')
        email_entered_text = request.form.get('emailtextbox')
        password_entered_text = request.form.get('passwordtextbox')
        comfirm_password_entered_text = request.form.get('comfirmpasswordtextbox')
        email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,7}\b'
        if email_entered_text == '' or username_entered_text == '' or password_entered_text == '' or\
                comfirm_password_entered_text == '':
            return render_template('signup.html', error_message="Field(s) cannot be empty")
        elif re.match(email_pattern, email_entered_text):
            pass
        else:
            return render_template('signup.html', error_message="Error, Email not valid.")
        if comfirm_password_entered_text != password_entered_text:
            return render_template('signup.html', error_message="Error, Passwords do not match.")
        elif checkbox_value != 'checkbox_value':
            return render_template('signup.html', error_message="Accept Terms & Conditions.")
        elif len(password_entered_text) > 5 and any(char.isupper() for char in password_entered_text):
            try:
                con = pymysql.connect(host='localhost', user='root', password=os.environ.get('MYSQL_PASSWORD'))
                my_cursor = con.cursor()
                query = 'create database if not exists mydatabase'
                my_cursor.execute(query)
                query = 'use mydatabase'
                my_cursor.execute(query)
                query = 'create table if not exists user_data(id int auto_increment primary key not null, ' \
                        'email varchar(50), username varchar(100), password varchar(20))'
                my_cursor.execute(query)
                con.commit()

                query = 'SELECT * FROM user_data WHERE username = %s OR email = %s'
                my_cursor.execute(query, (username_entered_text, email_entered_text))

                row = my_cursor.fetchone()
                if row != None:
                    return render_template('signup.html', error_message="Error, Username or email already exists.")
                else:
                    query = 'insert into user_data (email, username, password) values(%s, %s, %s)'
                    my_cursor.execute(query, (email_entered_text, username_entered_text, password_entered_text))

                    con.commit()
                    con.close()

                    return render_template('login.html')
                
            except pymysql.Error as e:
                return render_template('signup.html', error_message=f"Error: Failed to connect to the database. Error: {str(e)}")
            
        else:
            return render_template('signup.html', error_message="Error, Password needs to be longer than 5 characters and include a capital letter.")
    return render_template('signup.html')

@app.route('/forgotpassword', methods=['GET', 'POST'])
def forgotpassword():
    if request.method == 'POST':
                    pass
    return render_template('forgotpassword.html')

@app.route('/success')
def success():
    return "You have successfully logged in!"


def generate_one_time_code(self, length=6):
            characters = string.ascii_letters + string.digits
            one_time_code = ''.join(secrets.choice(characters) for _ in range(length))
            return one_time_code

def send_email(self, to_address, one_time_code):
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
        return False

def connect_to_email(self):
    email = self.email_entry.get().strip()

    if email == '':
        return render_template('forgotpassword.html', error_message="Error, all fields must be filled.")
        return
    
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
            random_code = self.generate_one_time_code()  # Generate the one-time code

            # Update the existing row with the new one-time code and timestamp
            update_query = "UPDATE user_data SET one_time_codes = %s, created_at = %s WHERE email = %s"
            current_timestamp = int(time.time())  # Get the current timestamp
            my_cursor.execute(update_query, (random_code, current_timestamp, email))
            con.commit()

            if self.send_email(email, random_code):
                return redirect(url_for('success'))
            else:
                return render_template('forgotpassword.html', error_message="Error, Failed to send email")
        

    except pymysql.Error as e:
        return render_template('forgotpassword.html', error_message="Error, Failed to connect to the database:"  + str(e))

    finally:
        try:
            if my_cursor is not None:
                my_cursor.close()
        except pymysql.Error:
            pass

def delete_expired_codes(self):
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
if __name__ == '__main__':
    app.run(debug=True)