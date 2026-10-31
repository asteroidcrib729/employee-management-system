-- Back up first and stop all application sessions. Never deletes employee/user records.
SET XACT_ABORT ON;
SET NOCOUNT ON;
IF OBJECT_ID('dbo.EMS_SchemaVersion', 'U') IS NOT NULL
BEGIN
    IF EXISTS (SELECT 1 FROM dbo.EMS_SchemaVersion WHERE Version = 1) RETURN;
    THROW 51000, 'EMS: Unsupported schema version.', 1;
END;
IF OBJECT_ID('dbo.Departments', 'U') IS NULL OR OBJECT_ID('dbo.Positions', 'U') IS NULL
   OR OBJECT_ID('dbo.Employees', 'U') IS NULL OR OBJECT_ID('dbo.PerformanceReview', 'U') IS NULL
   OR OBJECT_ID('dbo.Sign_Up', 'U') IS NULL
    THROW 51000, 'EMS: Original five-table schema required. Use --init-db for an empty database.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    IF EXISTS (SELECT 1 FROM dbo.Employees e LEFT JOIN dbo.Positions p ON e.PositionID=p.PositionID
        WHERE e.DepartmentID IS NULL OR e.PositionID IS NULL OR p.DepartmentID IS NULL OR e.DepartmentID<>p.DepartmentID)
        THROW 51000, 'EMS: Employee and position departments disagree. Run the legacy preflight report and reconcile explicitly.', 1;
    IF EXISTS (SELECT 1 FROM dbo.Positions WHERE DepartmentID IS NULL OR MinSalary IS NULL OR MaxSalary IS NULL
        OR MinSalary<0 OR MaxSalary<MinSalary OR MaxSalary>9999999999.99
        OR MinSalary<>ROUND(MinSalary,2) OR MaxSalary<>ROUND(MaxSalary,2))
        THROW 51000, 'EMS: Positions contain missing, negative, reversed or non-cent salary ranges.', 1;
    IF EXISTS (SELECT 1 FROM dbo.Employees WHERE BaseSalary<0 OR Bonus<0 OR BaseSalary>9999999999.99 OR Bonus>9999999999.99
        OR BaseSalary<>ROUND(BaseSalary,2) OR Bonus<>ROUND(Bonus,2))
        THROW 51000, 'EMS: Employee compensation cannot be negative, exceed the supported limit or require rounding.', 1;
    IF EXISTS (SELECT 1 FROM dbo.PerformanceReview WHERE EmployeeID IS NULL OR ReviewDate IS NULL OR Rating IS NULL OR Rating NOT BETWEEN 0 AND 9)
        THROW 51000, 'EMS: Reviews require an employee, date and rating from 0 to 9.', 1;
    IF EXISTS (SELECT 1 FROM dbo.Sign_Up WHERE Password IS NULL OR LEN(Password)>255
        OR LEN(Username)=0 OR Username COLLATE Latin1_General_100_BIN2 LIKE '%[^A-Za-z0-9_.-]%')
        THROW 51000, 'EMS: Existing credentials require operator review. Preserve account hashes; supported usernames use letters, digits, dots, underscores and hyphens.', 1;

    -- View/computed metadata is rebuilt after conversion. Failed constraints roll back all DDL.
    IF OBJECT_ID('dbo.EmployeeManagementView', 'V') IS NOT NULL DROP VIEW dbo.EmployeeManagementView;
    -- The original foreign keys/defaults have generated names. Remove only the four
    -- known relationships and the two salary defaults before changing their columns.
    IF (SELECT COUNT(*) FROM sys.foreign_keys WHERE parent_object_id IN
        (OBJECT_ID('dbo.Positions'),OBJECT_ID('dbo.Employees'),OBJECT_ID('dbo.PerformanceReview'))) <> 4
        THROW 51000, 'EMS: Customized foreign keys found; this migration supports the original coursework schema only.', 1;
    IF EXISTS (
        SELECT 1 FROM sys.foreign_key_columns f
        WHERE f.parent_object_id IN (OBJECT_ID('dbo.Positions'),OBJECT_ID('dbo.Employees'),OBJECT_ID('dbo.PerformanceReview'))
        AND NOT (
            (f.parent_object_id=OBJECT_ID('dbo.Positions') AND COL_NAME(f.parent_object_id,f.parent_column_id)='DepartmentID'
                AND f.referenced_object_id=OBJECT_ID('dbo.Departments') AND COL_NAME(f.referenced_object_id,f.referenced_column_id)='DepartmentID') OR
            (f.parent_object_id=OBJECT_ID('dbo.Employees') AND COL_NAME(f.parent_object_id,f.parent_column_id)='DepartmentID'
                AND f.referenced_object_id=OBJECT_ID('dbo.Departments') AND COL_NAME(f.referenced_object_id,f.referenced_column_id)='DepartmentID') OR
            (f.parent_object_id=OBJECT_ID('dbo.Employees') AND COL_NAME(f.parent_object_id,f.parent_column_id)='PositionID'
                AND f.referenced_object_id=OBJECT_ID('dbo.Positions') AND COL_NAME(f.referenced_object_id,f.referenced_column_id)='PositionID') OR
            (f.parent_object_id=OBJECT_ID('dbo.PerformanceReview') AND COL_NAME(f.parent_object_id,f.parent_column_id)='EmployeeID'
                AND f.referenced_object_id=OBJECT_ID('dbo.Employees') AND COL_NAME(f.referenced_object_id,f.referenced_column_id)='EmployeeID')
        ))
        THROW 51000, 'EMS: Customized relationships require a separate migration review.', 1;
    DECLARE @DropDependencies NVARCHAR(MAX)=N'';
    SELECT @DropDependencies=@DropDependencies + N'ALTER TABLE dbo.'+QUOTENAME(OBJECT_NAME(parent_object_id))+N' DROP CONSTRAINT '+QUOTENAME(name)+N';'
        FROM sys.foreign_keys WHERE parent_object_id IN (OBJECT_ID('dbo.Positions'),OBJECT_ID('dbo.Employees'),OBJECT_ID('dbo.PerformanceReview'));
    SELECT @DropDependencies=@DropDependencies + N'ALTER TABLE dbo.Positions DROP CONSTRAINT '+QUOTENAME(name)+N';'
        FROM sys.default_constraints WHERE parent_object_id=OBJECT_ID('dbo.Positions')
        AND COL_NAME(parent_object_id,parent_column_id) IN ('MinSalary','MaxSalary');
    EXEC sys.sp_executesql @DropDependencies;
    IF OBJECT_ID('dbo.Check_Rating','C') IS NOT NULL ALTER TABLE dbo.PerformanceReview DROP CONSTRAINT Check_Rating;
    ALTER TABLE dbo.Employees DROP COLUMN AnnualCompensation;
    IF OBJECT_ID('dbo.Check_PhoneNumber', 'C') IS NOT NULL ALTER TABLE dbo.Employees DROP CONSTRAINT Check_PhoneNumber;
    ALTER TABLE dbo.Employees ALTER COLUMN PhoneNumber VARCHAR(16) NULL;
    ALTER TABLE dbo.Employees ALTER COLUMN BaseSalary DECIMAL(12,2) NOT NULL;
    ALTER TABLE dbo.Employees ALTER COLUMN Bonus DECIMAL(12,2) NOT NULL;
    ALTER TABLE dbo.Employees ADD AnnualCompensation AS (BaseSalary + Bonus) * 12;
    ALTER TABLE dbo.Employees ALTER COLUMN DepartmentID VARCHAR(10) NOT NULL;
    ALTER TABLE dbo.Employees ALTER COLUMN PositionID VARCHAR(10) NOT NULL;
    ALTER TABLE dbo.Positions ALTER COLUMN DepartmentID VARCHAR(10) NOT NULL;
    ALTER TABLE dbo.Positions ALTER COLUMN MinSalary DECIMAL(12,2) NOT NULL;
    ALTER TABLE dbo.Positions ALTER COLUMN MaxSalary DECIMAL(12,2) NOT NULL;
    ALTER TABLE dbo.PerformanceReview ALTER COLUMN EmployeeID VARCHAR(9) NOT NULL;
    ALTER TABLE dbo.PerformanceReview ALTER COLUMN ReviewDate DATE NOT NULL;
    ALTER TABLE dbo.PerformanceReview ALTER COLUMN Rating INT NOT NULL;
    ALTER TABLE dbo.Sign_Up ALTER COLUMN Password VARCHAR(255) NOT NULL;
    -- Original accounts had no privileges model: all migrate to viewer, never admin.
    ALTER TABLE dbo.Sign_Up ADD Role VARCHAR(10) NOT NULL CONSTRAINT EMS_DefaultRole DEFAULT 'viewer' WITH VALUES;
    EXEC('ALTER TABLE dbo.Sign_Up ADD CONSTRAINT EMS_Role CHECK (Role IN (''admin'',''viewer''))');
    ALTER TABLE dbo.Sign_Up ADD CONSTRAINT EMS_Username CHECK (LEN(Username) BETWEEN 1 AND 20 AND Username COLLATE Latin1_General_100_BIN2 NOT LIKE '%[^A-Za-z0-9_.-]%');
    ALTER TABLE dbo.Departments ADD CONSTRAINT EMS_DepartmentText CHECK (LEN(LTRIM(RTRIM(DepartmentName)))>0 AND LEN(LTRIM(RTRIM(DepartmentLocation)))>0);
    ALTER TABLE dbo.Positions ADD CONSTRAINT EMS_PositionTitle CHECK (LEN(LTRIM(RTRIM(PositionTitle)))>0);
    ALTER TABLE dbo.Positions ADD CONSTRAINT EMS_SalaryRange CHECK (MinSalary>=0 AND MaxSalary>=MinSalary);
    ALTER TABLE dbo.Positions ADD CONSTRAINT EMS_PositionDepartment UNIQUE (PositionID,DepartmentID);
    ALTER TABLE dbo.Positions ADD CONSTRAINT EMS_Positions_Department FOREIGN KEY (DepartmentID) REFERENCES dbo.Departments(DepartmentID);
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_Employees_Department FOREIGN KEY (DepartmentID) REFERENCES dbo.Departments(DepartmentID);
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_Employees_Position FOREIGN KEY (PositionID) REFERENCES dbo.Positions(PositionID);
    ALTER TABLE dbo.PerformanceReview ADD CONSTRAINT EMS_Reviews_EmployeeFK FOREIGN KEY (EmployeeID) REFERENCES dbo.Employees(EmployeeID);
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_EmployeePositionDepartment FOREIGN KEY (PositionID,DepartmentID) REFERENCES dbo.Positions(PositionID,DepartmentID);
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_EmployeeNames CHECK (LEN(LTRIM(RTRIM(FirstName)))>0 AND LEN(LTRIM(RTRIM(LastName)))>0);
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_Compensation CHECK (BaseSalary>=0 AND Bonus>=0);
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_Email CHECK (Email IS NULL OR (Email LIKE '%_@_%._%' AND Email NOT LIKE '% %'));
    -- Compile the text constraint after ALTER COLUMN; the legacy type is BIGINT.
    EXEC(N'ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_Phone CHECK (PhoneNumber IS NULL OR
        (LEN(PhoneNumber) BETWEEN 7 AND 15 AND PhoneNumber COLLATE Latin1_General_100_BIN2 NOT LIKE ''%[^0-9]%'') OR
        (LEFT(PhoneNumber,1)=''+'' AND LEN(PhoneNumber) BETWEEN 8 AND 16 AND SUBSTRING(PhoneNumber,2,15) COLLATE Latin1_General_100_BIN2 NOT LIKE ''%[^0-9]%''))');
    ALTER TABLE dbo.PerformanceReview ADD CONSTRAINT EMS_Rating CHECK (Rating BETWEEN 0 AND 9);
    -- Match the case-sensitive identifier checks in the current schema.
    ALTER TABLE dbo.Departments ADD CONSTRAINT EMS_DepartmentID CHECK (DepartmentID COLLATE Latin1_General_100_BIN2 LIKE 'DEPT[0-9][0-9][0-9][0-9][0-9][0-9]');
    ALTER TABLE dbo.Positions ADD CONSTRAINT EMS_PositionID CHECK (PositionID COLLATE Latin1_General_100_BIN2 LIKE 'POST[0-9][0-9][0-9][0-9][0-9][0-9]');
    ALTER TABLE dbo.Employees ADD CONSTRAINT EMS_EmployeeID CHECK (EmployeeID COLLATE Latin1_General_100_BIN2 LIKE 'EMP[0-9][0-9][0-9][0-9][0-9][0-9]');
    ALTER TABLE dbo.PerformanceReview ADD CONSTRAINT EMS_ReviewID CHECK (ReviewID COLLATE Latin1_General_100_BIN2 LIKE 'REV[0-9][0-9][0-9][0-9][0-9][0-9]');
    CREATE INDEX EMS_Employees_Department ON dbo.Employees(DepartmentID);
    CREATE INDEX EMS_Employees_PositionDepartment ON dbo.Employees(PositionID,DepartmentID);
    CREATE INDEX EMS_Reviews_Employee ON dbo.PerformanceReview(EmployeeID);
    EXEC('CREATE VIEW dbo.EmployeeManagementView AS
        SELECT e.EmployeeID, e.FirstName, e.LastName, e.Email, e.PhoneNumber, e.HireDate,
            e.BaseSalary, e.Bonus, e.AnnualCompensation, e.PayDate,
            d.DepartmentID, d.DepartmentName, d.DepartmentLocation, d.CreationDate AS DepartmentCreationDate,
            p.PositionID, p.PositionTitle, p.MinSalary, p.MaxSalary, p.JobDescription,
            r.ReviewID, r.ReviewDate, r.Comments, r.Rating
        FROM dbo.Employees e JOIN dbo.Departments d ON e.DepartmentID=d.DepartmentID
        JOIN dbo.Positions p ON e.PositionID=p.PositionID AND e.DepartmentID=p.DepartmentID
        LEFT JOIN dbo.PerformanceReview r ON e.EmployeeID=r.EmployeeID');
    CREATE TABLE dbo.EMS_SchemaVersion (Version INT NOT NULL PRIMARY KEY);
    INSERT INTO dbo.EMS_SchemaVersion VALUES (1);
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE() <> 0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
