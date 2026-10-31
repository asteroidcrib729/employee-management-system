-- Read-only. Run on the original database before migration.
SELECT e.EmployeeID, e.DepartmentID AS EmployeeDepartment, e.PositionID, p.DepartmentID AS PositionDepartment
FROM dbo.Employees e LEFT JOIN dbo.Positions p ON e.PositionID=p.PositionID
WHERE e.DepartmentID IS NULL OR e.PositionID IS NULL OR p.DepartmentID IS NULL OR e.DepartmentID<>p.DepartmentID;
SELECT PositionID, DepartmentID, MinSalary, MaxSalary FROM dbo.Positions
WHERE DepartmentID IS NULL OR MinSalary IS NULL OR MaxSalary IS NULL OR MinSalary<0 OR MaxSalary<MinSalary
    OR MaxSalary>9999999999.99 OR MinSalary<>ROUND(MinSalary,2) OR MaxSalary<>ROUND(MaxSalary,2);
SELECT EmployeeID, BaseSalary, Bonus FROM dbo.Employees
WHERE BaseSalary<0 OR Bonus<0 OR BaseSalary>9999999999.99 OR Bonus>9999999999.99
    OR BaseSalary<>ROUND(BaseSalary,2) OR Bonus<>ROUND(Bonus,2);
SELECT ReviewID FROM dbo.PerformanceReview
WHERE EmployeeID IS NULL OR ReviewDate IS NULL OR Rating IS NULL OR Rating NOT BETWEEN 0 AND 9;
SELECT Username FROM dbo.Sign_Up WHERE Password IS NULL OR LEN(Password)>255 OR LEN(Username)=0
    OR Username COLLATE Latin1_General_100_BIN2 LIKE '%[^A-Za-z0-9_.-]%';
SELECT EmployeeID, PhoneNumber, Email FROM dbo.Employees
WHERE (PhoneNumber IS NOT NULL AND LEN(CONVERT(VARCHAR(30),PhoneNumber)) NOT BETWEEN 7 AND 15)
    OR (Email IS NOT NULL AND (Email NOT LIKE '%_@_%._%' OR Email LIKE '% %'));
SELECT DepartmentID FROM dbo.Departments WHERE LEN(LTRIM(RTRIM(DepartmentName)))=0 OR LEN(LTRIM(RTRIM(DepartmentLocation)))=0;
SELECT PositionID FROM dbo.Positions WHERE LEN(LTRIM(RTRIM(PositionTitle)))=0;
SELECT EmployeeID FROM dbo.Employees WHERE LEN(LTRIM(RTRIM(FirstName)))=0 OR LEN(LTRIM(RTRIM(LastName)))=0;
