from email.mime.text import MIMEText
import json
import re
import secrets
import smtplib
import string
import time
from flask import Flask, redirect, render_template, request, session, url_for
import pymysql
import os

import requests

foods = []
app = Flask(__name__, static_folder='static')
app.secret_key = secrets.token_hex(16)

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

@app.route('/')
def index():
    return render_template('index.html')

def get_user_by_username(username):
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password=os.environ.get('MYSQL_PASSWORD'),
        database='mydatabase'
    )

    with connection:
        with connection.cursor() as cursor:
            query = 'SELECT id, username, email, password FROM user_data WHERE username = %s'
            cursor.execute(query, (username,))
            result = cursor.fetchone()

            if result:
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, result))
                
                # Add an 'authenticated' key to indicate successful authentication
                user_dict['authenticated'] = True
                
                return user_dict
            else:
                return None
            
def get_user_id_by_username(username):
    user = get_user_by_username(username)
    return user['id'] if user else None

def get_user_by_id(user_id):
    connection = pymysql.connect(
        host='localhost',
        user='root',
        password=os.environ.get('MYSQL_PASSWORD'),
        database='mydatabase'
    )

    with connection:
        with connection.cursor() as cursor:
            query = 'SELECT id, username, email FROM user_data WHERE id = %s'
            cursor.execute(query, (user_id,))
            result = cursor.fetchone()

            if result:
                columns = [desc[0] for desc in cursor.description]
                user_dict = dict(zip(columns, result))
                return user_dict
            else:
                return None

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
            user_id = get_user_id_by_username(username_entered_text)
            session['user_id'] = user_id
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

class FoodManager:
    def __init__(self):
        self.foods = []
        self.total_calories = 0
        self.food_data = ""

    def update_food(self, name, calories, serving_size_g, fat_total_g, fat_saturated_g,
                    protein_g, sodium_mg, potassium_mg, cholesterol_mg,
                    carbohydrates_total_g, fiber_g, sugar_g):
        food_item = {
            "name": name,
            "calories": calories,
            "serving_size_g": serving_size_g,
            "fat_total_g": fat_total_g,
            "fat_saturated_g": fat_saturated_g,
            "protein_g": protein_g,
            "sodium_mg": sodium_mg,
            "potassium_mg": potassium_mg,
            "cholesterol_mg": cholesterol_mg,
            "carbohydrates_total_g": carbohydrates_total_g,
            "fiber_g": fiber_g,
            "sugar_g": sugar_g
        }
        self.foods.append(food_item)
        self.total_calories += calories

    def remove_food(self, name):
        for food in self.foods:
            if food["name"] == name:
                self.total_calories -= food["calories"]
                try:
                    self.foods.remove(food)
                except ValueError:
                    app.logger.info(food)
                break

food_manager = FoodManager()

@app.route('/delete_food/<food_name>', methods=['POST'])
def delete_food(food_name):
    if request.method == 'POST':
        food_manager.remove_food(food_name)
    return redirect(url_for('calories'))

@app.route('/calories', methods=['GET', 'POST'])
def calories():
    data = session.get('data', [])

    if request.method == 'POST' and 'FoodButton' in request.form:
        query = request.form.get('foodtextbox')
        api_key = os.environ.get('MY_API_KEY')
        api_url = f'https://api.api-ninjas.com/v1/nutrition?query={query}'
        headers = {'X-Api-Key': api_key}
        response = requests.get(api_url, headers=headers)

        if response.status_code == requests.codes.ok:
            json_data = response.text
            new_data = json.loads(json_data)

            if new_data:
                name = new_data[0]["name"]
                calories = new_data[0]["calories"]
                serving_size_g = new_data[0]["serving_size_g"]
                fat_total_g = new_data[0]["fat_total_g"]
                fat_saturated_g = new_data[0]["fat_saturated_g"]
                protein_g = new_data[0]["protein_g"]
                sodium_mg = new_data[0]["sodium_mg"]
                potassium_mg = new_data[0]["potassium_mg"]
                cholesterol_mg = new_data[0]["cholesterol_mg"]
                carbohydrates_total_g = new_data[0]["carbohydrates_total_g"]
                fiber_g = new_data[0]["fiber_g"]
                sugar_g = new_data[0]["sugar_g"]

                # Call the update_food method to add the food item
                food_manager.update_food(name, calories, serving_size_g, fat_total_g, fat_saturated_g,
                                         protein_g, sodium_mg, potassium_mg, cholesterol_mg,
                                         carbohydrates_total_g, fiber_g, sugar_g)
                
                # Append the new data to the existing data
                data.append(new_data[0])
                session['data'] = data  # Update the session with the combined data
            else:
                food_manager.food_data = "No data available for the given query."

    return render_template('calories.html', nutrition_data=data, food_data=food_manager.food_data, total_calories=food_manager.total_calories)

@app.route('/nutrition', methods=['GET', 'POST'])
def nutrition():
    calories_info = request.form.get('caloriesinfo')

    if calories_info:
        ndata = session.get('data', [])
        app.logger.info(ndata)
        selected_data = next((item for item in ndata if item["name"] == calories_info), None)
        if selected_data:
            return render_template('nutrition.html', nutrition_data=selected_data, message=None)
        else:
            return render_template('nutrition.html', nutrition_data=None, message="No data available for the selected food.")
    else:
        return render_template('nutrition.html', nutrition_data=None, message="No food selected.")

class ExerciseManager:
    def __init__(self):
        self.exercises = []
        self.exercise_data = ""
        
    def update_exercise(self, name, name1, name2, name3, name4, name5):
        exercise_item = {
            "name": name,
            "name1": name1,
            "name2": name2,
            "name3": name3,
            "name4": name4,
            "name5": name5,
        }

        self.exercises.append(exercise_item)

    def remove_exercise(self, name):
        for exercise in self.exercises:
            if exercise["name"] == name:
                self.exercises.remove(exercise)
                break

@app.route('/delete_exercise/<exercise_name>', methods=['POST'])
def delete_exercise(exercise_name):
    exercise_manager.remove_exercise(exercise_name)
    return redirect(url_for('exercise'))

exercise_manager = ExerciseManager()

@app.route('/exercise', methods=['GET', 'POST'])
def exercise():
    
    edata = []  
    
    if request.method == 'POST':
        query = request.form.get('exercisetextbox')
        api_key = os.environ.get('MY_API_KEY')
        api_url = f'https://api.api-ninjas.com/v1/exercises?muscle={query}'
        headers = {'X-Api-Key': api_key}

        response = requests.get(api_url, headers=headers)

        if response.status_code == requests.codes.ok:
            json_data = response.text
            edata = json.loads(json_data)

            if edata:
                name = edata[0]["name"]
                name1 = edata[1]["name"]
                name2 = edata[2]["name"]
                name3 = edata[3]["name"]
                name4 = edata[4]["name"]
                name5 = edata[5]["name"]

                exercise_manager.update_exercise(name, name1, name2, name3, name4, name5)
                
                session['edata'] = edata
            else:
                exercise_manager.exercise_data = "No data available for the given query."

    return render_template('exercise.html', exercises_data=exercise_manager.exercises, message=exercise_manager.exercise_data)

@app.route('/exerciseinfo', methods=['GET', 'POST'])
def exerciseinfo():
    selected_exercise = request.form.get('selected_exercise')

    if selected_exercise:
        exdata = session.get('edata', [])
        selected_data = next((item for item in exdata if item["name"] == selected_exercise), None)
        if selected_data:
            return render_template('exerciseinfo.html', exercise_data=selected_data, message=None)
        else:
            return render_template('exerciseinfo.html', exercise_data=None, message="No data available for the selected exercise.")
    else:
        return render_template('exerciseinfo.html', exercise_data=None, message="No exercise selected.")
    
@app.route('/profile', methods=['GET', 'POST'])
def profile():
    user_id = session.get('user_id')

    # Check if the user is logged in
    if user_id:
        # Retrieve user details based on the user ID
        user = get_user_by_id(user_id)

        # Check if the user exists
        if user:
            # Pass the user details to the profile template
            return render_template('profile.html', username=user['username'], email=user['email'])
        else:
            return render_template('profile.html', error_message="User not found")
    else:
        return render_template('profile.html', error_message="User not logged in")

if __name__ == '__main__':
    app.run(debug=True)