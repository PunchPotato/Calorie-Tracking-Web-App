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

    return render_template('login.html', entered_text=None)
        

    # return redirect(url_for('success'))

@app.route('/success')
def success():
    return "You have successfully logged in!"

if __name__ == '__main__':
    app.run(debug=True)