import re
from tkinter import IntVar
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
            return render_template('signup.html', error_message="Field cannot be empty")
        elif re.match(email_pattern, email_entered_text):
            pass
        else:
            return render_template('signup.html', error_message="Error, Email not valid.")
        if comfirm_password_entered_text != password_entered_text:
            return render_template('signup.html', error_message="Error, Passwords do not match.")
        elif checkbox_value != 'checkbox_value':
            return render_template('signup.html', error_message="Accept Terms & Conditions.")
        elif len(password_entered_text) > 5 and any(char.isupper() for char in password_entered_text):
            render_template('login.html')
        else:
            return render_template('signup.html', error_message="Error, Password needs to be longer than 5 characters and include a capital letter.")
    return render_template('signup.html')

@app.route('/forgotpassword')
def forgotpassword():
    return "this is a forgot password page"

@app.route('/success')
def success():
    return "You have successfully logged in!"

if __name__ == '__main__':
    app.run(debug=True)