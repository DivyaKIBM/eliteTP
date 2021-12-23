# app.py
from flask import Flask, render_template, request, json, redirect, session, flash, url_for, Response
# from flask_mongoengine import \
from flask_mongoengine import MongoEngine
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
import configparser
from flask_pymongo import PyMongo
from user import User, Anonymous
from flask_bcrypt import Bcrypt
from flask_talisman import Talisman
from user import Anonymous
import selenium.webdriver

from selenium import webdriver
from bs4 import BeautifulSoup
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
import re
import webbrowser
import pdfkit
import os

app = Flask(__name__)

#wkhtmltopdf exe path
Download_PATH = 'wkhtmltopdf/bin/wkhtmltopdf.exe'
APP_ROOT = os.path.dirname(os.path.abspath(__file__))
Download_FOLDER = os.path.join(APP_ROOT, Download_PATH)
summaryHTMLfile = os.path.join(APP_ROOT,"templates\summary.html")

# Configuration Settings
config = configparser.ConfigParser()
config.read('configuration.ini')
default = config['DEFAULT']
app.secret_key = default['SECRET_KEY']
app.config['MONGO_DBNAME'] = default['DATABASE_NAME']
app.config['MONGO_URI'] = default['MONGO_URI']
app.config['PREFERRED_URL_SCHEME'] = "https"


# app.config['MONGODB_SETTINGS'] = {
#     'db': 'travelplanner',
#     # Local connection string
#     #'host': 'mongodb://localhost:27017/travelplanner'
#     # Deploy connection string
#     #'host': 'mongodb://TP:TP@mongodb:27017/travelplanner?authSource=travelplanner'
#     # Local cluster connection string
#     'host': 'mongodb://TP:TP@localhost:27017/travelplanner?authSource=travelplanner'
#
# }

# db = MongoEngine()
# db.init_app(app)

# Create Pymongo
mongo = PyMongo(app)

# Create Bcrypt
#bc = Bcrypt(app)

#Create Talisman
# csp = {
#     'default-src': [
#         '\'self\'',
#         '*.trusted.com'
#     ]
# }
# talisman = Talisman(app, content_security_policy=csp)


# Create login manager
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.anonymous_user = Anonymous
login_manager.login_view = "login"


# class User(db.Document):
#     name = db.StringField()
#     email = db.StringField()
#     password = db.StringField()
#     reg_date = db.DateTimeField(datetime.now)


@app.route('/')
def main():
    return render_template('home.html', signUpMessage="")

@app.route('/signUp', methods=['POST', 'GET'])
def register():
    today = datetime.today()
    if request.method == 'POST':
        # Trim input data
        _name = request.form['inputName'].strip()
        _email = request.form['inputEmail'].strip()
        _password = request.form['inputPassword'].strip()
        _reg_date = today

        users = mongo.db.user
        # Check if email address already exists
        existing_user = users.find_one(
            {'email': _email})

        if existing_user is None:
            logout_user()
            # Hash password
            _hashed_password = generate_password_hash(_password)
            # Create user object (note password hash not stored in session)
            new_user = User(_name,_email,_reg_date)
            # Create dictionary data to save to database
            user_data_to_save = new_user.dict()
            user_data_to_save['password'] = _hashed_password

            # Insert user record to database
            if users.insert_one(user_data_to_save):
                return render_template("home.html", signUpMessage="User created successfully!!! Please sign in.")
            else:
                # Handle database error
                return redirect(url_for('signup', error=2))

        # Handle duplicate email
        return redirect(url_for('signup', error=1))

    # Return template for registration page if GET request
    return render_template('signup.html', error=request.args.get("error"))



@login_manager.user_loader
def load_user(user_id):
    return User.get(user_id)


# Login
@app.route('/login', methods=['GET', 'POST'])
def login():
    try:
        if request.method == 'GET':
            if current_user.is_authenticated:
                # Redirect to index if already authenticated
                return redirect(url_for('/lta'))
            # Render login page
            return render_template('signin.html', error=request.args.get("error"))

        # Get Form Fields
        _username = request.form['inputEmail']
        _password = request.form['inputPassword']
        # Retrieve user from database
        users = mongo.db.user
        user_data = users.find_one({'email': _username})
        if user_data:
            password = user_data['password']
            # Check password hash
            # Compare Passwords
            if check_password_hash(password, _password):
                # Passed
                session['sessionusername'] = user_data['name']
                #flash('Logged in!', 'success')
                # print(pyautogui.alert("Login Successful!!!"))
                #return redirect('/lta')
                return render_template('lta.html')
            else:
                error = 'Invalid password'
                return render_template('signin.html', error=error)
        else:
            error = 'Username not found'
            return render_template('signin.html', error=error)
    except Exception as ex:
        print("An exception occurred")
        # Redirect to error page on any error
        if hasattr(ex, 'message'):
            error = ex.message
        else:
            error = ex
        return render_template('error.html', error=error)
        #return redirect(url_for('error.html', error=1))


@app.route('/index',methods=['POST'])
def index():
    # print(session.get('sessionusername'))
    if session.get('sessionusername'):
        return render_template('index.html')
    else:
        return render_template('error.html', error='Unauthorized Access')



def change_date_format(dt):
        return re.sub(r'(\d{4})-(\d{1,2})-(\d{1,2})', '\\3/\\2/\\1', dt)

@app.route('/itinerary', methods=['GET', 'POST'])
def itinerary():
    if request.method == "POST":
        checktriptype = request.form.get("trip type")
        # checktriptype= request.form['trip type']
        if not checktriptype:
            return render_template("index.html", indexValidationMessage="Please select trip type.")

        fromlocation = request.form['fromloc']
        if not fromlocation:
            # return render_template("index.html", indexValidationMessage="Please select from location.")
            return redirect(url_for('/index'))

        tolocation = request.form['toloc']
        if not tolocation:
            return render_template("index.html", indexValidationMessage="Please select to location.")

        departureDate = request.form['depDate']
        if not departureDate:
            return render_template("index.html", indexValidationMessage="Please select departure date.")

        returnDate = request.form['retDate']
        if (checktriptype == 'Round Trip') and (not returnDate):
            return render_template("index.html", indexValidationMessage="Please select return date.")

        Adults = request.form['drpAdults']
        if not Adults:
            return render_template("index.html", indexValidationMessage="Please select no. of passengers")

        # sourcelocation = "HYD"  # Origin airport code
        # destination = "BLR"  # Destination airport code
        # trDate = "23/12/2021"
        # Adults = str(1)
        # Children = str(0)
        # Infants = str(0)
        # session['trdate'] = trDate
        # rdoption = request.form['trip type']
        rdoption = request.form['trip type']
        if rdoption == "One Way":
            sourcelocation = request.form['fromloc']
            sourcelocationCode = sourcelocation[0:3]
            destination = request.form['toloc']
            destinationlocationCode = destination[0:3]
            trDate = request.form['depDate']
            trFomattedDate = change_date_format(trDate)
            Adults = request.form['drpAdults']
            Children = request.form['drpChildren']
            Infants = request.form['drpInfants']

        listflightNames = []
        listDepTime = []
        listFromLocation = []
        listflightDuration = []
        listflightLayerInfo = []
        listArrivalTime = []
        listToLocation = []
        listflightPrice = []

        basedataURL = "https://www.makemytrip.com/flight/search?itinerary=" + sourcelocationCode + "-" + destinationlocationCode + "-" + trFomattedDate + "&tripType=O&paxType=" + "A-" + Adults + "_C-" + Children + "_I-" + Infants + "&intl=false&cabinClass=E&ccde=IN&lang=eng"

        browser = request.user_agent.browser
        version = request.user_agent.version and int(request.user_agent.version.split('.')[0])
        platform = request.user_agent.platform
        uas = request.user_agent.string

        if browser.strip() == 'firefox':
            from selenium.webdriver.firefox.options import Options
            # options = Options()
            # options.headless = True
            options = Options()
            options.add_argument('--headless')
            # options.add_argument('--disable-gpu')
            # driver = selenium.webdriver.Firefox(options=options)
            driver = selenium.webdriver.Firefox(executable_path=APP_ROOT + "\\geckodriver.exe", options=options)
        elif browser.strip() == 'edge':
            # from selenium.webdriver.edge.options import Options
            # options = Options()
            # options.add_argument('--headless')
            # options.add_argument('--disable-gpu')
            # driver = selenium.webdriver.Edge(options=options)
            # driver = selenium.webdriver.Edge(executable_path=APP_ROOT + "\\msedgedriver.exe")
            driver = selenium.webdriver.Edge(executable_path=os.path.abspath("msedgedriver.exe"))
        elif browser.strip() == 'chrome':
            #from selenium.webdriver.chrome.options import Options
            # options = Options()
            # options.add_argument('--headless')
            # options.add_argument('--disable-gpu')
            # driver = selenium.webdriver.Chrome(options=options)
            driver = selenium.webdriver.Chrome(executable_path=APP_ROOT + "\\chromedriver.exe")

        driver.get(basedataURL)
        element_xpath = '//*[@id="left-side--wrapper"]/div[2]'  # First box with relevant flight data.
        # Wait until the first box with relevant flight data appears on Screen
        element = WebDriverWait(driver, 50).until(EC.visibility_of_element_located((By.XPATH, element_xpath)))
        # time.sleep(30)

        # Find the document body and get its inner HTML for processing in BeautifulSoup parser.
        body = driver.find_element_by_tag_name("body").get_attribute("innerHTML")

        driver.quit()  # Browser Closed.

        print("Getting data from DOM ...")
        soupBody = BeautifulSoup(body)  # Parse the inner HTML using BeautifulSoup

        # Get Flight Names
        spanFlightName = soupBody.findAll("span", {"class": "boldFont blackText airlineName"})
        for i in range(0, len(spanFlightName)):
            listflightNames.append(spanFlightName[i].text)

        # Get From Location and Departure Time
        flightTimeInfoLeft = soupBody.findAll('div', {"class": "flightTimeSection flexOne timeInfoLeft"})
        for flightTimeInfoLeftFromLocationDepTime in flightTimeInfoLeft:
            # ab = a1.find('span').text
            DepTime = flightTimeInfoLeftFromLocationDepTime.select_one('span').text
            listDepTime.append(DepTime)
            FromLocation = flightTimeInfoLeftFromLocationDepTime.find("p", {"class": "darkText"}).text
            listFromLocation.append(FromLocation)
        # Get  Flight Duration and (Non stop or Via info)
        flightStopInfo = soupBody.findAll('div', {"class": "stop-info flexOne"})
        for flightStopInfoDurationLayover in flightStopInfo:
            flightDuration = flightStopInfoDurationLayover.select_one('p').text
            listflightDuration.append(flightDuration)
            flightLayerInfo = flightStopInfoDurationLayover.find("p", {"class": "flightsLayoverInfo"}).text
            listflightLayerInfo.append(flightLayerInfo)
        # Get To Location and Arrival Time
        flightTimeInfoRight = soupBody.findAll('div', {"class": "flightTimeSection flexOne timeInfoRight"})
        for flightTimeInfoRightToLocationArrivalTime in flightTimeInfoRight:
            ArrivalTime = flightTimeInfoRightToLocationArrivalTime.select_one('span').text
            listArrivalTime.append(ArrivalTime)
            ToLocation = flightTimeInfoRightToLocationArrivalTime.find("p", {"class": "darkText"}).text
            listToLocation.append(ToLocation)
        # Get  Flight Price
        flightPriceSection = soupBody.findAll('div', {"class": "priceSection"})
        for flightPriceInfo in flightPriceSection:
            flightPrice = flightPriceInfo.find("p",
                                               {"class": "blackText fontSize18 blackFont white-space-no-wrap"}).text
            listflightPrice.append(flightPrice)

        return render_template("itinerary.html", listflightNames=listflightNames, listDepTime=listDepTime,
                               listFromLocation=listFromLocation,
                               listflightDuration=listflightDuration, listflightLayerInfo=listflightLayerInfo,
                               listArrivalTime=listArrivalTime, listToLocation=listToLocation,
                               listflightPrice=listflightPrice)


@app.route('/summary',methods=['GET','POST'])
def summary():
        #getFlightName = request.form.get('tdFlightName')
        session['getFlightName']= request.form["tdFlightName"]
        session['getDepTime']= request.form["tdDepTime"]
        session['getFromLocation']= request.form["tdFromLocation"]
        session['getFlightDuration'] = request.form["tdFlightDuration"]
        session['getFlightLayerInfo'] = request.form["tdFlightLayerInfo"]
        session['getArrivalTime']= request.form["tdArrivalTime"]
        session['getToLocation'] = request.form["tdToLocation"]
        session['getFlightPrice']= request.form["tdFlightPrice"]

        #getFlightPrice = request.form["tdFlightPrice"]
        return render_template('summary.html')


@app.route("/wkhtmltopdf_template",methods=['POST'])
def wkhtmltopdf_template():

    filename = 'outputTP.pdf'
    config = pdfkit.configuration(wkhtmltopdf=Download_FOLDER)
    body = '''
    <p style="text-align:center;font-size:large;">Hello</p>
    <hr>
    <p style="margin-top: 15px;margin-bottom: 15px;margin-left: 150px; font-size:large;">Hi:  {} </p>
    <p style="margin-top: 15px;margin-bottom: 15px;margin-left: 150px; font-size:large;">hello:  {}  </p>
    <p style="margin-top: 15px;margin-bottom: 15px;margin-left: 150px; font-size:large;">hello :  {}  </p>
    <hr>
    <p style="margin-top: 15px;margin-bottom: 15px;margin-left: 150px; font-size:large;">hello  {}  </p>
    <p style="margin-top: 15px;margin-bottom: 15px;margin-left: 150px; font-size:large;"> hi:  {} </p>
    <img style="position: fixed;bottom: 50px;right: 0; height:50%; width:auto;" src="http://i.imgur.com/uLhrB27.jpg" alt="hi" title="Hello">
            '''.format(
        "123456789",
        "hi",
        "Mohan",
        "Red Hackathon",
        "A000000000"
    )
    options = {
        'encoding': 'UTF-8'
    }

    User_FOLDER = os.path.join('users', session['sessionusername'])
    User_FOLDER_Path = os.path.join(APP_ROOT, User_FOLDER)
    if not (os.path.isdir(User_FOLDER_Path)):
        os.mkdir(User_FOLDER_Path)

    pdfFile_PATH= os.path.join(User_FOLDER_Path,filename)
    pdfkit.from_string(body,pdfFile_PATH, configuration=config, options=options)
    pdfDownload = open(pdfFile_PATH, 'rb').read()
    #pdfDownload = open(filename, 'rb').read()
    #os.remove(filename)
    return Response(
        pdfDownload,
        mimetype="application/pdf",
        headers={
            "Content-disposition": "attachment; filename=" + pdfFile_PATH,
            "Content-type": "application/force-download"
        }
    )


@app.route('/logout')
def logout():
    session.pop('sessionusername', None)
    return redirect('/')


if __name__ == '__main__':
    app.run(debug=True)
