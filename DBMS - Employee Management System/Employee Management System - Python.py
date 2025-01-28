import pyodbc
import hashlib

# Establish Connection To SQL Server Database
Connector = pyodbc.connect('Driver={SQL Server};'
                           'Server=DESKTOP-B0CSIHC\\NEWMSSQLSERVER;'
                           'Database=EmployeeManagementDB;'
                           'Trusted_Connection=yes;')

# Function To Add New Employee
def Add_Employee():
    EmployeeID = input("Enter Employee ID: ")
    FirstName = input("Enter First Name: ")
    LastName = input("Enter Last Name: ")
    Email = input("Enter Email: ")
    PhoneNumber = input("Enter Phone Number: ")
    HireDate = input("Enter Hire Date (YYYY-MM-DD): ")
    BaseSalary = int(input("Enter Base Salary: "))
    Bonus = int(input("Enter Bonus: "))
    PayDate = input("Enter Pay Date (YYYY-MM-DD): ")
    DepartmentID = input("Enter Department ID: ")
    PositionID = input("Enter Position ID: ")

    Cursor = Connector.cursor()

    Query = ('''
    INSERT INTO Employees(
            EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, 
            DepartmentID, PositionID
        )
        VALUES
            (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''')
    Values = (
        EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID,
        PositionID
    )

    Cursor.execute(Query, Values)
    Connector.commit()
    Cursor.close()
    print("EMPLOYEE ADDED SUCCESSFULLY!")

# Function To List All Employees
def Display_Employees():
    Cursor = Connector.cursor()
    Cursor.execute('SELECT * FROM Employees')

    for Record in Cursor:
        print(f"Employee ID: {Record[0]}")
        print(f"First Name: {Record[1]}")
        print(f"Last Name: {Record[2]}")
        print(f"Email: {Record[3]}")
        print(f"Phone Number: {Record[4]}")
        print(f"Hire Date: {Record[5]}")
        print(f"Base Salary: {Record[6]}")
        print(f"Bonus: {Record[7]}")
        print(f"Annual Compensation: {Record[8]}")
        print(f"Pay Date: {Record[9]}")
        print(f"Department ID: {Record[10]}")
        print(f"Position ID: {Record[11]}")
        print("")

    Cursor.close()

# Function To Update Existing Employee's Details
def Update_Employee():
    EmployeeID = input("Enter Employee ID: ")
    FirstName = input("Enter First Name: ")
    LastName = input("Enter Last Name: ")
    Email = input("Enter Email: ")
    PhoneNumber = input("Enter Phone Number: ")
    HireDate = input("Enter Hire Date (YYYY-MM-DD): ")
    BaseSalary = int(input("Enter Base Salary: "))
    Bonus = int(input("Enter Bonus: "))
    PayDate = input("Enter Pay Date (YYYY-MM-DD): ")
    DepartmentID = input("Enter Department ID: ")
    PositionID = input("Enter Position ID: ")

    Cursor = Connector.cursor()

    Query = ('''
    UPDATE Employees
    SET FirstName = ?, LastName = ?, Email = ?, PhoneNumber = ?, HireDate = ?, BaseSalary = ?, Bonus = ?, PayDate = ?,
    DepartmentID = ?, PositionID = ?
    WHERE EmployeeID = ?
    ''')
    Values = (
        FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID,
        EmployeeID
    )

    Cursor.execute(Query, Values)
    Connector.commit()
    Cursor.close()
    print("EMPLOYEE DETAILS UPDATED SUCCESSFULLY!")

# Function To Remove An Employee From Employees Table
def Remove_Employee():
    EmployeeID = input("Enter Employee ID To Remove Employee: ")

    Cursor = Connector.cursor()

    Query = ('''
    DELETE FROM PerformanceReview WHERE EmployeeID = ?
    DELETE FROM Employees WHERE EmployeeID = ?
    ''')
    Values = (EmployeeID, EmployeeID)

    Cursor.execute(Query, Values)
    Connector.commit()
    Cursor.close()
    print("EMPLOYEE REMOVED SUCCESSFULLY!")

# Function To Add New Department To The Departments Table
def Add_Department():
    DepartmentID = input("Enter Department ID: ")
    DepartmentName = input("Enter Department Name: ")
    DepartmentLocation = input("Enter Department Location: ")
    CreationDate = input("Enter Department Creation Date (YYYY-MM-DD): ")

    Cursor = Connector.cursor()
    Query = ('''
    INSERT INTO Departments(DepartmentID, DepartmentName, DepartmentLocation, CreationDate)
    VALUES(?, ?, ?, ?)
    ''')
    Values = (DepartmentID, DepartmentName, DepartmentLocation, CreationDate)

    Cursor.execute(Query, Values)
    Connector.commit()
    Cursor.close()
    print("DEPARTMENT ADDED SUCCESSFULLY!")

# Function To Display All Departments
def Display_Departments():
    Cursor = Connector.cursor()
    Cursor.execute('SELECT * FROM Departments')

    for Record in Cursor:
        print(f"Department ID: {Record[0]}")
        print(f"Department Name: {Record[1]}")
        print(f"Department Location: {Record[2]}")
        print(f"Creation Date: {Record[3]}")
        print("")

    Cursor.close()

# Function To Add New Performance Reviews To The Performance Review Table
def Add_Performance_Review():
    ReviewID = input("ENTER REVIEW ID: ")
    EmployeeID = input("ENTER Employee ID: ")
    ReviewDate = input("Enter Review Date (YYYY-MM-DD): ")
    Comments = input("Enter Comments: ")
    Rating = input("Enter Rating: ")

    Cursor = Connector.cursor()
    Query = ('''
    INSERT INTO PerformanceReview(ReviewID, EmployeeID, ReviewDate, Comments, Rating)
    VALUES(?, ?, ?, ?, ?)
    ''')
    Values = (ReviewID, EmployeeID, ReviewDate, Comments, Rating)

    Cursor.execute(Query, Values)
    Connector.commit()
    Cursor.close()
    print("PERFORMANCE REVIEW ADDED SUCCESSFULLY!")

# Function To Display All Performance Review
def Display_Performance_Review():
    Cursor = Connector.cursor()
    Cursor.execute('SELECT * FROM PerformanceReview')

    for Record in Cursor:
        print(f"Review ID: {Record[0]}")
        print(f"Employee ID: {Record[1]}")
        print(f"Review Date: {Record[2]}")
        print(f"Comments: {Record[3]}")
        print(f"Rating: {Record[4]}")
        print("")

    Cursor.close()

# Function To Add A New Position
def Add_Position():
    PositionID = input("Enter Position ID: ")
    PositionTitle = input("Enter Position Title: ")
    DepartmentID = input("Enter Department ID: ")
    MinSalary = input("Enter Minimum Salary: ")
    MaxSalary = input("Enter Maximum Salary: ")
    JobDescription = input("Enter Job Description: ")

    Cursor = Connector.cursor()
    Query = ('''
    INSERT INTO Positions(PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription)
    VALUES(?, ?, ?, ?, ?, ?)
    ''')

    Values = (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription)

    Cursor.execute(Query, Values)
    Connector.commit()
    Cursor.close()
    print("POSITION ADDED SUCCESSFULLY!")

# Function To Display All Positions
def Display_Positions():
    Cursor = Connector.cursor()
    Cursor.execute('SELECT * FROM Positions')

    for Record in Cursor:
        print(f"Position ID: {Record[0]}")
        print(f"Position Title: {Record[1]}")
        print(f"Department ID: {Record[2]}")
        print(f"Minimum Salary: {Record[3]}")
        print(f"Maximum Salary: {Record[4]}")
        print(f"Job Description: {Record[5]}")
        print("")

    Cursor.close()

# Main Function To Run The Employee Management System
def EMP():
    while True:
        print("-----------------------------------------")
        print("WELCOME TO EMPLOYEE MANAGEMENT SYSTEM!")
        print("0. Exit Employee Management System")
        print("1. Add Department")
        print("2. List Departments")
        print("3. Add Position")
        print("4. List Positions")
        print("5. Add Employee")
        print("6. List Employees")
        print("7. Update Employee\'s Details")
        print("8. Remove Employee")
        print("9. Add Performance Review")
        print("10. List Performance Reviews")
        print("-----------------------------------------")
        Choice = int(input("Enter Your Choice (0-1-10): "))
        print("-----------------------------------------")

        match Choice:
            case 0:
                print("EXITING EMPLOYEE MANAGEMENT SYSTEM!")
                break
            case 1:
                Add_Department()
            case 2:
                Display_Departments()
            case 3:
                Add_Position()
            case 4:
                Display_Positions()
            case 5:
                Add_Employee()
            case 6:
                Display_Employees()
            case 7:
                Update_Employee()
            case 8:
                Remove_Employee()
            case 9:
                Add_Performance_Review()
            case 10:
                Display_Performance_Review()
            case _:
                print("INVALID CHOICE! TRY AGAIN!")

        print("-----------------------------------------")

def Signup():
    Username = input("Enter Username: ")
    Password = input("Enter Password: ")

    Cursor = Connector.cursor()

    Query = ('''
        INSERT INTO Sign_Up(Username, Password)
        VALUES(?, ?)
        ''')

    try:
        if Password.isascii() and len(Password) >= 9:
            Hasher = hashlib.sha256(Password.encode())
            Hashed_Password = Hasher.hexdigest()

            Values = (Username, Hashed_Password)

            Cursor.execute(Query, Values)
            Connector.commit()
            Cursor.close()
            print("SIGN-UP SUCCESSFUL!")
        else:
            print("INVALID PASSWORD! TRY AGAIN!")
    except pyodbc.IntegrityError:
        print("USERNAME ALREADY EXISTS!")

def Login():
    Username = input("Enter Username: ")
    Password = input("Enter Password: ")

    Hasher = hashlib.sha256(Password.encode())
    Hashed_Password = Hasher.hexdigest()

    Cursor = Connector.cursor()

    Query = ('''
    SELECT * FROM Sign_Up WHERE Username = ? AND Password = ?
    ''')
    Values = (Username, Hashed_Password)

    Cursor.execute(Query, Values)

    Flag = Cursor.fetchone()

    if Flag:
        print("LOGIN SUCCESSFUL!")
        EMP()
    else:
        print("INVALID USERNAME OR PASSWORD!")

    Cursor.close()

def main():
    while True:
        print("-----------------------------------------")
        print("WELCOME TO EMPLOYEE MANAGEMENT SYSTEM!")
        print("0. Exit Employee Management System")
        print("1. SIGN-UP")
        print("2. LOG-IN")
        print("-----------------------------------------")
        Choice = int(input("Enter Your Choice (0-1-2): "))
        print("-----------------------------------------")

        match Choice:
            case 0:
                print("EXITING EMPLOYEE MANAGEMENT SYSTEM!")
                break
            case 1:
                Signup()
            case 2:
                Login()
            case _:
                print("INVALID CHOICE! TRY AGAIN!")

        print("-----------------------------------------")

if __name__ == "__main__":
    main()