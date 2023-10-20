from flask import Flask, render_template, request, redirect, url_for, flash
from pymongo import MongoClient
from flask import session
from datetime import date
from flask_bcrypt import Bcrypt
from bokeh.plotting import figure, show
from bokeh.embed import components
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import datetime
from functools import wraps
import logging

app = Flask(__name__)
bcrypt = Bcrypt()
app.secret_key = "secretkey"
app.config["secret_key"] = "secretkey"
app.config['SECURITY_PASSWORD_SALT'] = '$2b$12$wqKlYjmOfXPghx3FuC3Pu.'

logging.basicConfig(filename="logInfo.log")
logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)
log = logging.getLogger('werkzeug')
log.setLevel(logging.WARNING)
handler = logging.FileHandler('app.log')
handler.setLevel(logging.DEBUG)
formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
handler.setFormatter(formatter)
logger.addHandler(handler)


client = MongoClient("mongodb://localhost:27017")
dataBase = client["AppraisalDB"]
employeeCo = dataBase["Employee"]
ManagerCo = dataBase["Manager"]
superAdmin = dataBase["SuperAdmin"]
targetCo = dataBase["Targets"]
personalTargets = dataBase["personalTargets"]
AppraisalManager = dataBase["AppraisalManager"]
AppraisalEmployee  = dataBase["AppraisalEmployee"]
AppraisalGoals = dataBase["AppraisalGoals"]
Notifications = dataBase["Notifications"]

# smtp = smtplib.SMTP("smtp-mail.outlook.com", 587)
# smtp.starttls()
# smtp.login(from_email, emailPassword)

def login_required(f):
    @wraps(f)
    def allow_only_valid(*args, **kwargs):
        if 'userName' not in session:
            return redirect(url_for('Login'))
        return f(*args, **kwargs)
    return allow_only_valid

@app.route("/", methods=["GET", "POST", "PUT"])
def Login():
    try:
        if request.method == "POST":
            value = request.form["formId"]
            if value == "login":
                userName = request.form["username"]
                password = request.form["password"]
                session["userName"] = userName
                rec = employeeCo.find_one({"userName": userName})
                rec1 = superAdmin.find_one({"userName": userName})
                if rec:
                    session["empId"] = rec["empId"]
                    if bcrypt.check_password_hash(rec["password"], password) and rec["isManager"] == 0:
                        app.logger.info("Login successful for employee %s", userName)
                        return redirect(url_for("employee"))
                    elif rec["isManager"] == 1:
                        app.logger.info("Login successful for manager %s", userName)
                        return redirect(url_for("manager"))
                    else:
                        app.logger.warning("Invalid password for user %s", userName)
                        return render_template("login.html", data="Invalid Password", userLoggedOut = False)
                elif rec1:
                    if bcrypt.check_password_hash(rec1["password"], password):
                        EmpDocs = []
                        cursor = employeeCo.find()
                        for doc in cursor:
                            if doc["isManager"] == 0:
                                EmpDocs.append(doc)
                        ManDocs = []
                        cursor = ManagerCo.find()
                        for doc in cursor:
                            ManDocs.append(doc)
                        app.logger.info("Login successful for superadmin %s", userName)
                        if len(EmpDocs) == 0:
                            EmpDocs = None
                        return render_template(
                            "superAdmin.html", EmpDocs=EmpDocs, ManDocs=ManDocs
                        )
                    else:
                        app.logger.warning("Invalid password for user %s", userName)
                        return render_template("login.html", data="Invalid Password", userLoggedOut = False)
                else:
                    app.logger.warning("User %s not found", userName)
                    return render_template("login.html", data="User not found", userLoggedOut = False)
            else:
                empName = request.form["name"]
                empEmail = request.form["email"]
                empId = request.form["empId"]
                userName = request.form["Uname"]
                password = request.form["pwd"]
                # msg = MIMEText("Logged in successfully")
                # msg["From"] = from_email
                # msg["To"] = empEmail
                # msg["Subject"] = "Website Registration"
                # msg.set_payload("Created an Account Successfully")
                # smtp.sendmail(from_email, empEmail, msg.as_string())
                hashedPassword = bcrypt.generate_password_hash(password, 10)
                rec = employeeCo.find_one(
                    {
                        "$or": [
                            {"empId": empId},
                            {"empEmail": empEmail},
                            {"userName": userName},
                        ]
                    }
                )
                if rec:
                    app.logger.warning("User already exists with empID %s, email %s, or username %s", empId, empEmail, userName)
                    return render_template("login.html", data1="User already Present", userLoggedOut = False)
                else:
                    employeeCo.insert_one(
                    {
                        "empName": empName,
                        "empEmail": empEmail,
                        "empId": empId,
                        "userName": userName,
                        "password": hashedPassword,
                        "isManager": 0,
                    }
                    )
                    app.logger.info("New user %s added", userName)
                    return render_template(
                        "login.html", data1="Added Successfully, Login Now"
                    )
        return render_template("login.html", userLoggedOut = False)
    except Exception as e:
        app.logger.error("Unexpected error occurred: %s", str(e))
        return render_template("error.html", error=str(e))


@app.route("/grantAccess", methods=["POST"])
@login_required
def grantAccess():
    try:
        for i in request.form:
            if i != "formName":
                query = {"empId": i}
                value = {"$set": {"isManager": 1}}
                rec = employeeCo.find_one(query)
                # msg = MIMEText("You are assigned Manager Privileges")
                # msg["From"] = from_email
                # msg["To"] = rec["empEmail"]
                # msg["Subject"] = "Role Privileges"
                # msg.set_payload("You are assigned Manager Privileges")
                # smtp.sendmail(from_email, rec["empEmail"], msg.as_string())
                if rec["isManager"] != 1:
                    employeeCo.update_one(query, value)
                    ManagerCo.insert_one(
                        {"manId": rec["empId"], "manEmail": rec["empEmail"], "manName" : rec["empName"]}
                    )
                app.logger.info("Manager Access granted to employee with empID %s", i)
        EmpDocs = []
        cursor = employeeCo.find()
        for doc in cursor:
            if doc["isManager"] == 0:
                EmpDocs.append(doc)
        ManDocs = []
        cursor = ManagerCo.find()
        for doc in cursor:
            ManDocs.append(doc)
        app.logger.info("Access granted successfully")
        return render_template(
            "superAdmin.html", data="Updated successfully", EmpDocs=EmpDocs, ManDocs=ManDocs
        )
    except Exception as e:
        app.logger.error("Unexpected error occurred: %s", str(e))
        return render_template("error.html", error=str(e))


@app.route("/assignEmployees", methods=["POST", "GET"])
@login_required
def assignEmployees():
    try:
        form = request.form
        for manId, empIds in form.items():
            employeeIds = empIds.split(",")
            if employeeIds[0] == "":
                continue
            empIds = []
            for empId in employeeIds:
                rec = employeeCo.find_one({"empId": empId})
                empIds.append(empId)
                if not rec:
                    EmpDocs = []
                    cursor = employeeCo.find()
                    for doc in cursor:
                        if doc["isManager"] == 0:
                            EmpDocs.append(doc)
                    ManDocs = []
                    cursor = ManagerCo.find()
                    for doc in cursor:
                        ManDocs.append(doc)
                    logger.error("Employee Id %s not found", str(empId))
                    return render_template("superAdmin.html", data1= "Employee Id " + str(empId) + " not found", EmpDocs = EmpDocs, ManDocs = ManDocs)
            for empId in empIds:
                # msg = MIMEText("Your manager is Employee Id: " + str(session["empId"])+" Employee Name: " + str(session["empName"]))
                # msg = MIMEText("Hi")
                # msg["From"] = from_email
                rec = employeeCo.find_one({"empId" : empId})
                print(rec)
                # msg["To"] = rec["empEmail"]
                # # print(session["empId"])
                # msg["Subject"] = "You are assigned a manager"
                # msg.set_payload("You are assigned a manager")
                # smtp.sendmail(from_email, rec["empEmail"], msg.as_string())
                employeeCo.update_one({"empId" : empId}, {"$set" : {"manId" : manId}})
            ManagerCo.update_one({"manId": manId}, {"$set": {"empId": empIds}})
            EmpDocs = []
            cursor = employeeCo.find()
            for doc in cursor:
                if doc["isManager"] == 0:
                    EmpDocs.append(doc)
            ManDocs = []
            cursor = ManagerCo.find()
            for doc in cursor:
                ManDocs.append(doc)
            logger.info("Employees assigned successfully")
        return render_template(
            "superAdmin.html", data="Updated successfully", EmpDocs=EmpDocs, ManDocs=ManDocs
        )
    except Exception as e:
        logger.exception("Exception occurred" + str(e))
        return render_template("superAdmin.html", data1="Error occurred while assigning employees")


@app.route("/targets", methods=["POST"])
@login_required
def Targets():
    try:
        if request.method == "POST":
            value = request.form["val"]
            if "assignTarget" in value:
                tarId = request.form["tarId"]
                empId = request.form["empId"]
                desc = request.form["desc"]
                startDate = request.form["startDate"]
                endDate = request.form["expectedEndDate"]
                empName = employeeCo.find_one({"empId" : empId})["empName"]
                targetCo.insert_one(
                    {
                        "tarId": tarId,
                        "manId": session["empId"],
                        "empId": empId,
                        "empName" : empName,
                        "desc": desc,
                        "startDate": startDate,
                        "expectedEndDate": endDate,
                    }
                )
                logger.info("Target with ID %s assigned to employee ID %s", str(tarId), str(empId))
                return redirect(url_for("manager"))
            elif "completedTarget" in value:
                empId = session["empId"]
                tarId = request.form["targetId"]
                current_date = str(date.today())
                document = request.files["file"]
                document = document.read()
                targetCo.update_one({"tarId": tarId}, {"$set": {"endDate": current_date, "docData" : str(document)}})
                logger.info("Employee ID %s completed target with ID %s", str(empId), str(tarId))
                return redirect(url_for("employee"))
            else:
                feedback = request.form["feedback"]
                tarId = value
                targetCo.update_one({"tarId": tarId}, {"$set": {"feedback": feedback}})
                logger.info("Feedback updated for target with ID %s", str(tarId))
                return redirect(url_for("manager"))
    except Exception as e:
        logger.exception("An Exception occurred: " + str(e))
        return render_template("error.html", message="Internal Server Error")

@app.route("/dashboard")
@login_required
def dashboard():
    try:
        role = "employee"
        if employeeCo.find_one({"empId" : session["empId"]})["isManager"] == 1:
            role = "manager" 
        if role == "employee":
            tasks = targetCo.find({"empId": session["empId"]})
            tasksAssigned = 0
            tasksCompleted = 0
            tasksPending = 0
            for doc in tasks:
                if "endDate" in doc:
                    tasksCompleted += 1
                else:
                    tasksPending += 1
            tasksAssigned = tasksCompleted + tasksPending
            x = [tasksAssigned, tasksCompleted, tasksPending]
            rec = personalTargets.find({"empId" : session["empId"]})
            dataPersonal = [0,0,0]
            for doc in rec:
                if "endDate" in doc:
                    dataPersonal[1]+=1
                else:
                    dataPersonal[2]+=1
            dataPersonal[0] = dataPersonal[1] + dataPersonal[2]
            return render_template(
                "dashboard.html",
                name = session["userName"],
                role = role,
                x = x,
                dataPersonal = dataPersonal
            )
        else:
            rec = targetCo.find({"manId" : session["empId"]})
            records = []
            empIds = []
            for doc in rec:
                pre = False
                for di in empIds:
                    if di["empId"] == doc["empId"]:
                        pre = True
                        break
                if not pre:
                    empIds.append({"empId": doc["empId"], "empName": doc["empName"], "total": 0, "complete": 0, "inComplete": 0, "dueDates": 0,"onTime": 0, "startDate" : doc["startDate"], "endDate" : 0, "expectedEndDate" : doc["expectedEndDate"], "beComplete" : 0})
                records.append(doc)
            for doc in records:
                if "endDate" in doc:
                    for eachRecord in empIds:
                        if eachRecord["empId"] == doc["empId"]:
                            eachRecord["endDate"] = doc["endDate"]
                            dif = datetime.datetime.strptime(doc["expectedEndDate"], "%Y-%m-%d") - datetime.datetime.strptime(doc["endDate"], "%Y-%m-%d")
                            if dif.days < 0:
                                eachRecord["dueDates"] += 1
                            elif dif.days == 0:
                                eachRecord["onTime"] += 1 
                            else:
                                eachRecord["beComplete"] += 1
                            eachRecord["complete"] += 1
                            break
                else:
                    for eachRecord in empIds:
                        if eachRecord["empId"] == doc["empId"]:
                            dif = datetime.datetime.strptime(doc["expectedEndDate"], "%Y-%m-%d") - datetime.datetime.strptime(doc["startDate"], "%Y-%m-%d")
                            if dif.days < 0:
                                eachRecord["dueDates"] += 1
                            elif dif.days == 0:
                                eachRecord["onTime"] += 1 
                            else:
                                eachRecord["beComplete"] += 1
                            eachRecord["inComplete"]+=1
                            break
            for rec in empIds:
                rec["total"] = rec["complete"] + rec["inComplete"]
        return render_template("dashboard.html", name = session["userName"], role = role, empIds = empIds)
    except Exception as e:
        logger.exception("An exception occurred: "+str(e))


@app.route("/forgotPassword", methods=["POST"])
@login_required
def forgotPasssword():
    return render_template("fPassword.html")


@app.route("/employee")
@login_required
def employee():
    try:
        targets = []
        cursor = targetCo.find({"empId": session["empId"]})
        for doc in cursor:
            targets.append(doc)
        logger.info("Employee ID %s accessed their targets", str(session["empId"]))
        return render_template(
            "employee.html",
            targets=targets,
            name = session["userName"]
        )
    except Exception as e:
        logger.exception("An Exception occurred: " + str(e))
        return render_template("error.html", message="Internal Server Error")

@app.route("/manager")
def manager():
    try:
        targets = []
        cursor = targetCo.find({"manId": session["empId"]})
        for doc in cursor:
            targets.append(doc)
        logger.info("Manager ID %s accessed their targets", str(session["empId"]))
        EmpDocs = []
        cursor = employeeCo.find({"manId" : session["empId"]})
        for doc in cursor:
            EmpDocs.append(doc)
        return render_template("manager.html", targets=targets, name = session["userName"], EmpDocs = EmpDocs)
    except Exception as e:
        logger.exception("An Exception occurred: " + str(e))
        return render_template("error.html", message="Internal Server Error")
    

@app.route("/setTargets", methods=["POST", "GET"])
@login_required
def setTargets():
    try:
        role = "employee"
        targets = []
        cursor = personalTargets.find({"empId" : session["empId"]})
        for doc in cursor:
            targets.append(doc)
        if employeeCo.find_one({"empId" : session["empId"]})["isManager"] == 1:
            role = "manager" 
        if request.method == "POST":
            if request.form["val"] == "setTarget":
                tarNum = request.form["tarNum"]
                title = request.form["title"]
                desc = request.form["desc"]
                startDate = request.form["startDate"]
                eEndDate = request.form["eEndDate"]
                empId = session["empId"]
                personalTargets.insert_one({"tarNum" : tarNum, "empId" : empId, "title" : title, "desc" : desc, "startDate" : startDate, "expectedEndDate" : eEndDate})
                logger.info("Personal target with Number %s set by Employee ID %s", str(tarNum), str(empId))
                return redirect(url_for("setTargets"))
            else:
                empId = session["empId"]
                tarNum = request.form["val"]
                current_date = str(date.today())
                personalTargets.update_one({"tarNum": tarNum , "empId" : session["empId"]}, {"$set": {"endDate": current_date}})
                logger.info("Personal target with Number %s completed by Employee ID %s", str(tarNum), str(empId))
                return redirect(url_for("setTargets"))
        if len(targets) == 0:
            targets = None
        return render_template("setTargets.html", role = role, name = session["userName"], targets = targets)
    except Exception as e:
        logger.exception("An Exception occurred: " + str(e))
        return render_template("error.html", message="Internal Server Error")
    

@app.route("/appraisal", methods=["GET", "POST"])
@login_required
def appraisal():
    try:
        role = "employee"
        appraisalPeriod = None
        goalsList = None
        if employeeCo.find_one({"empId" : session["empId"]})["isManager"] == 1:
            appraisalPeriod = AppraisalManager.find_one({"manId" : session["empId"]}) 
            empList = ManagerCo.find_one({"manId" : session["empId"]})["empId"]
            goalsList = []
            for empId in empList:
                cursor = AppraisalGoals.find({"empId" : empId})
                for doc in cursor:
                    goalsList.append(doc)
            role = "manager" 
        if request.method == "POST":
            if role == "manager":
                if request.form["val"] == "appraisalPeriod":
                    startDate = request.form["startDate"]
                    endDate = request.form["endDate"]
                    criteria = request.form["criteria"]
                    employees = ManagerCo.find_one({"manId" : session["empId"]})
                    employees = employees["empId"]
                    if request.form["val"] == "appraisalPeriod":
                        AppraisalManager.insert_one({"manId" : session["empId"], "startDate" : startDate, "endDate" : endDate, "criteria" : criteria})
                        for empId in employees:
                            AppraisalEmployee.insert_one({"manId" : session["empId"], "empId" : empId, "startDate" : startDate, "endDate" : endDate, "criteria" : criteria})
                    logger.info("%s succesfully added Appraisal Period", str(session["empId"]))
                elif request.form["val"] == "statusEvaluation":
                    type = request.form["submitButton"]
                    goalNumber = request.form["goalNumber"]
                    empId = request.form["EmployeeId"]
                    if type == "Accept":
                        logger.info("Goal of %s is accepted ",str(empId))
                        AppraisalGoals.update_one({"goalNumber" : goalNumber, "empId" : empId}, {"$set" : {"status" : "accept"}})
                    elif type == "Change":
                        logger.info("Goal of %s nedds to be changed ",str(empId))
                        AppraisalGoals.update_one({"goalNumber" : goalNumber, "empId" : empId}, {"$set" : {"status" : "change"}})
                elif request.form["val"] == "feedback":
                    goalNumber = request.form["goalNumber"]
                    empId = request.form["EmployeeId"]
                    feedback = request.form["feedback"]
                    logger.info("Feedback for %s goal of %s employee",str(goalNumber),str(empId))
                    AppraisalGoals.update_one({"goalNumber" : goalNumber, "empId" : empId}, {"$set" : {"feedback" : feedback}})
                elif request.form["val"] == "acceptGoal":
                    goalNumber = request.form["goalNumber"]
                    empId = request.form["EmployeeId"]
                    logger.info("%s Goal of %s is accepted",str(goalNumber), str(empId))
                    AppraisalGoals.update_one({"goalNumber" : goalNumber, "empId" : empId}, {"$set" : {"status" : "accept"}})
                elif request.form["val"] == "changeAppraisalPeriod":
                    startDate = request.form["startDate"]
                    endDate = request.form["endDate"]
                    criteria = request.form["criteria"]
                    empIds = ManagerCo.find_one({"manId" : session["empId"]})["empId"]
                    for empId in empIds:
                        AppraisalEmployee.update_one({"empId" : empId}, {"$set" : {"startDate" : startDate, "endDate" : endDate, "criteria" : criteria}})
                    logger.info("%s Managers appraisal period is changed",str(session["empId"]))
                    AppraisalManager.update_one({"manId" : session["empId"]}, {"$set" : {"startDate" : startDate, "endDate" : endDate, "criteria" : criteria}})
                appraisalPeriod = AppraisalManager.find_one({"manId" : session["empId"]}) 
            else:
                if request.form["val"] == "setAppraisalGoals":
                    goalNumber = request.form["AppraisalNumber"]
                    description = request.form["desc"]
                    startDate = request.form["startDate"]
                    endDate = request.form["eEndDate"]
                    AppraisalGoals.insert_one({"empId" : session["empId"], "goalNumber" : goalNumber, "startDate" : startDate, "endDate" : endDate, "status" : "waiting", "desc" : description, "empName" : session["userName"]})
                    logger.info("Goal Number %s is set for %s employee", str(goalNumber), str(session["empId"]))
                    cursor = AppraisalGoals.find({"empId" : session["empId"]})
                    goalsList = []
                    for doc in cursor:
                        goalsList.append(doc)
                elif request.form["val"] == "changedGoal":
                    goalNumber = request.form["goalNumber"]
                    empId = request.form["empId"]
                    desc = request.form["changedGoal"]
                    AppraisalGoals.update_one({"goalNumber" : goalNumber, "empId" : empId} , { "$set" : {"desc" : desc}})
                    cursor = AppraisalGoals.find({"empId" : session["empId"]})
                    goalsList = []
                    for doc in cursor:
                        goalsList.append(doc)
                    logger.info("Goal Number %s is changed by employee %s", str(goalNumber), str(session["empId"]))
                appraisalPeriod = AppraisalEmployee.find_one({"empId" : session["empId"]})    
        elif role == "employee":
            appraisalPeriod = AppraisalEmployee.find_one({"empId" : session["empId"]})
            cursor = AppraisalGoals.find({"empId" : session["empId"]})
            goalsList = []
            for doc in cursor:
                goalsList.append(doc)
        if len(goalsList) == 0:
            goalsList = None
        return render_template("appraisal.html", name = session["userName"], role = role, appraisalPeriod = appraisalPeriod, goalsList = goalsList)
    except Exception as e:
        logger.exception("An Exception occurred: " + str(e))
        return render_template("error.html", message="Internal Server Error")


@app.route("/document", methods = ["POST", "GET"])
@login_required
def document():
    try:
        rec = targetCo.find_one({"tarId" : request.form["tarId"] , "empId" : request.form["empId"]})
        docData = rec["docData"]
        docData = docData[2:len(docData)-1]
        logger.info("Document viewed for target with ID %s and employee ID %s", str(request.form["tarId"]), str(request.form["empId"]))
        return render_template("document.html", rec = rec, docData = docData)
    except Exception as e:
        logger.exception("An Exception occurred: " + str(e))
        return render_template("error.html", message="Internal Server Error")
    
@app.route("/logout")
@login_required
def logout():
    session.clear()
    return redirect(url_for("Login"))

@app.route("/notifications", methods = ["GET", "POST"])
@login_required
def notifications():
    role = "employee"
    if employeeCo.find_one({"empId" : session["empId"]})["isManager"] == 1:
        role = "manager"
    return render_template("notifications.html", role = role, name = session["userName"])

if __name__ == "__main__":
  app.run(debug=False)