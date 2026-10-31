-- Run against an existing, empty application database. Never creates/drops a database.
SET XACT_ABORT ON;
SET NOCOUNT ON;
IF OBJECT_ID('dbo.EMS_SchemaVersion', 'U') IS NOT NULL
BEGIN
    IF EXISTS (SELECT 1 FROM dbo.EMS_SchemaVersion WHERE Version = 1) RETURN;
    THROW 51000, 'EMS: Unsupported schema version.', 1;
END;
IF OBJECT_ID('dbo.Departments', 'U') IS NOT NULL OR OBJECT_ID('dbo.Positions', 'U') IS NOT NULL
   OR OBJECT_ID('dbo.Employees', 'U') IS NOT NULL OR OBJECT_ID('dbo.PerformanceReview', 'U') IS NOT NULL
   OR OBJECT_ID('dbo.Sign_Up', 'U') IS NOT NULL
    THROW 51000, 'EMS: Existing tables found. Back up the database and use --migrate.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    CREATE TABLE dbo.Departments (
        DepartmentID VARCHAR(10) NOT NULL PRIMARY KEY,
        DepartmentName VARCHAR(100) NOT NULL,
        DepartmentLocation VARCHAR(100) NOT NULL,
        CreationDate DATE NOT NULL DEFAULT (CONVERT(DATE, GETDATE())),
        CONSTRAINT EMS_DepartmentID CHECK (DepartmentID COLLATE Latin1_General_100_BIN2 LIKE 'DEPT[0-9][0-9][0-9][0-9][0-9][0-9]'),
        CONSTRAINT EMS_DepartmentText CHECK (LEN(LTRIM(RTRIM(DepartmentName))) > 0 AND LEN(LTRIM(RTRIM(DepartmentLocation))) > 0)
    );
    CREATE TABLE dbo.Positions (
        PositionID VARCHAR(10) NOT NULL PRIMARY KEY,
        PositionTitle VARCHAR(100) NOT NULL,
        DepartmentID VARCHAR(10) NOT NULL REFERENCES dbo.Departments(DepartmentID),
        MinSalary DECIMAL(12,2) NOT NULL,
        MaxSalary DECIMAL(12,2) NOT NULL,
        JobDescription VARCHAR(100) NULL,
        CONSTRAINT EMS_PositionID CHECK (PositionID COLLATE Latin1_General_100_BIN2 LIKE 'POST[0-9][0-9][0-9][0-9][0-9][0-9]'),
        CONSTRAINT EMS_PositionTitle CHECK (LEN(LTRIM(RTRIM(PositionTitle))) > 0),
        CONSTRAINT EMS_SalaryRange CHECK (MinSalary >= 0 AND MaxSalary >= MinSalary),
        CONSTRAINT EMS_PositionDepartment UNIQUE (PositionID, DepartmentID)
    );
    CREATE TABLE dbo.Employees (
        EmployeeID VARCHAR(9) NOT NULL PRIMARY KEY,
        FirstName VARCHAR(50) NOT NULL,
        LastName VARCHAR(50) NOT NULL,
        Email VARCHAR(100) NULL,
        PhoneNumber VARCHAR(16) NULL,
        HireDate DATE NOT NULL,
        BaseSalary DECIMAL(12,2) NOT NULL,
        Bonus DECIMAL(12,2) NOT NULL,
        -- Both components are monthly recurring amounts, not annual amounts or one-off bonuses.
        AnnualCompensation AS (BaseSalary + Bonus) * 12,
        PayDate DATE NOT NULL,
        DepartmentID VARCHAR(10) NOT NULL REFERENCES dbo.Departments(DepartmentID),
        PositionID VARCHAR(10) NOT NULL REFERENCES dbo.Positions(PositionID),
        CONSTRAINT EMS_EmployeeID CHECK (EmployeeID COLLATE Latin1_General_100_BIN2 LIKE 'EMP[0-9][0-9][0-9][0-9][0-9][0-9]'),
        CONSTRAINT EMS_EmployeeNames CHECK (LEN(LTRIM(RTRIM(FirstName))) > 0 AND LEN(LTRIM(RTRIM(LastName))) > 0),
        CONSTRAINT EMS_Compensation CHECK (BaseSalary >= 0 AND Bonus >= 0),
        CONSTRAINT EMS_Email CHECK (Email IS NULL OR (Email LIKE '%_@_%._%' AND Email NOT LIKE '% %')),
        CONSTRAINT EMS_Phone CHECK (PhoneNumber IS NULL OR
            (LEN(PhoneNumber) BETWEEN 7 AND 15 AND PhoneNumber COLLATE Latin1_General_100_BIN2 NOT LIKE '%[^0-9]%') OR
            (LEFT(PhoneNumber,1) = '+' AND LEN(PhoneNumber) BETWEEN 8 AND 16 AND SUBSTRING(PhoneNumber,2,15) COLLATE Latin1_General_100_BIN2 NOT LIKE '%[^0-9]%')),
        CONSTRAINT EMS_EmployeePositionDepartment FOREIGN KEY (PositionID, DepartmentID)
            REFERENCES dbo.Positions(PositionID, DepartmentID)
    );
    CREATE TABLE dbo.PerformanceReview (
        ReviewID VARCHAR(9) NOT NULL PRIMARY KEY,
        EmployeeID VARCHAR(9) NOT NULL REFERENCES dbo.Employees(EmployeeID),
        ReviewDate DATE NOT NULL DEFAULT (CONVERT(DATE, GETDATE())),
        Comments VARCHAR(255) NULL,
        Rating INT NOT NULL,
        CONSTRAINT EMS_ReviewID CHECK (ReviewID COLLATE Latin1_General_100_BIN2 LIKE 'REV[0-9][0-9][0-9][0-9][0-9][0-9]'),
        CONSTRAINT EMS_Rating CHECK (Rating BETWEEN 0 AND 9)
    );
    CREATE TABLE dbo.Sign_Up (
        Username VARCHAR(20) NOT NULL PRIMARY KEY,
        Password VARCHAR(255) NOT NULL,
        Role VARCHAR(10) NOT NULL DEFAULT 'viewer',
        CONSTRAINT EMS_Role CHECK (Role IN ('admin', 'viewer')),
        CONSTRAINT EMS_Username CHECK (LEN(Username) BETWEEN 1 AND 20 AND Username COLLATE Latin1_General_100_BIN2 NOT LIKE '%[^A-Za-z0-9_.-]%')
    );
    CREATE INDEX EMS_Employees_Department ON dbo.Employees(DepartmentID);
    CREATE INDEX EMS_Employees_PositionDepartment ON dbo.Employees(PositionID, DepartmentID);
    CREATE INDEX EMS_Reviews_Employee ON dbo.PerformanceReview(EmployeeID);
    EXEC('CREATE VIEW dbo.EmployeeManagementView AS
        SELECT e.EmployeeID, e.FirstName, e.LastName, e.Email, e.PhoneNumber, e.HireDate,
            e.BaseSalary, e.Bonus, e.AnnualCompensation, e.PayDate,
            d.DepartmentID, d.DepartmentName, d.DepartmentLocation, d.CreationDate AS DepartmentCreationDate,
            p.PositionID, p.PositionTitle, p.MinSalary, p.MaxSalary, p.JobDescription,
            r.ReviewID, r.ReviewDate, r.Comments, r.Rating
        FROM dbo.Employees e JOIN dbo.Departments d ON e.DepartmentID = d.DepartmentID
        JOIN dbo.Positions p ON e.PositionID = p.PositionID AND e.DepartmentID = p.DepartmentID
        LEFT JOIN dbo.PerformanceReview r ON e.EmployeeID = r.EmployeeID');
    CREATE TABLE dbo.EMS_SchemaVersion (Version INT NOT NULL PRIMARY KEY);
    INSERT INTO dbo.EMS_SchemaVersion VALUES (1);
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
