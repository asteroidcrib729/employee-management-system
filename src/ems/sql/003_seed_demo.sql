-- Optional, idempotent sample data. Inserts missing IDs only; never overwrites records.
SET XACT_ABORT ON;
SET NOCOUNT ON;
IF OBJECT_ID('dbo.EMS_SchemaVersion','U') IS NULL THROW 51000, 'EMS: Initialize or migrate the schema first.', 1;
BEGIN TRY
BEGIN TRANSACTION;
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000001')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000001', 'HR', 'New York', '2023-01-01');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000002')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000002', 'Finance', 'London', '2023-01-02');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000003')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000003', 'IT', 'San Francisco', '2023-01-03');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000004')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000004', 'Sales', 'Chicago', '2023-01-04');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000005')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000005', 'Marketing', 'Los Angeles', '2023-01-05');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000006')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000006', 'Legal', 'Houston', '2023-01-06');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000007')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000007', 'R&D', 'Seattle', '2023-01-07');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000008')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000008', 'Operations', 'Boston', '2023-01-08');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000009')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000009', 'Customer Support', 'Miami', '2023-01-09');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000010')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000010', 'Administration', 'Dallas', '2023-01-10');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000011')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000011', 'Procurement', 'Denver', '2023-01-11');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000012')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000012', 'Logistics', 'Phoenix', '2023-01-12');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000013')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000013', 'Production', 'Philadelphia', '2023-01-13');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000014')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000014', 'Engineering', 'San Diego', '2023-01-14');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000015')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000015', 'Quality Assurance', 'Detroit', '2023-01-15');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000016')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000016', 'Product Management', 'Minneapolis', '2023-01-16');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000017')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000017', 'Compliance', 'Orlando', '2023-01-17');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000018')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000018', 'Investor Relations', 'San Jose', '2023-01-18');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000019')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000019', 'Public Relations', 'Charlotte', '2023-01-19');
IF NOT EXISTS (SELECT 1 FROM dbo.Departments WITH (UPDLOCK,HOLDLOCK) WHERE DepartmentID='DEPT000020')
    INSERT INTO dbo.Departments (DepartmentID, DepartmentName, DepartmentLocation, CreationDate) VALUES ('DEPT000020', 'Facilities', 'Columbus', '2023-01-20');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000001')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000001', 'HR Manager', 'DEPT000001', 50000, 70000, 'Manage HR department');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000002')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000002', 'Accountant', 'DEPT000002', 60000, 80000, 'Handle financial records');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000003')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000003', 'Software Engineer', 'DEPT000003', 80000, 120000, 'Develop software');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000004')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000004', 'Sales Manager', 'DEPT000004', 70000, 90000, 'Manage sales team');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000005')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000005', 'Marketing Specialist', 'DEPT000005', 60000, 85000, 'Develop marketing strategies');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000006')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000006', 'Legal Advisor', 'DEPT000006', 90000, 110000, 'Provide legal advice');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000007')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000007', 'Research Scientist', 'DEPT000007', 85000, 95000, 'Conduct research');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000008')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000008', 'Operations Manager', 'DEPT000008', 75000, 95000, 'Oversee operations');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000009')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000009', 'Customer Support Rep', 'DEPT000009', 40000, 60000, 'Support customers');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000010')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000010', 'Admin Assistant', 'DEPT000010', 35000, 50000, 'Administrative support');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000011')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000011', 'Procurement Officer', 'DEPT000011', 55000, 75000, 'Handle procurement');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000012')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000012', 'Logistics Coordinator', 'DEPT000012', 50000, 70000, 'Coordinate logistics');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000013')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000013', 'Production Supervisor', 'DEPT000013', 60000, 80000, 'Supervise production');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000014')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000014', 'Engineer', 'DEPT000014', 70000, 100000, 'Engineering tasks');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000015')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000015', 'QA Analyst', 'DEPT000015', 60000, 85000, 'Quality assurance');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000016')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000016', 'Product Manager', 'DEPT000016', 90000, 120000, 'Manage products');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000017')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000017', 'Compliance Officer', 'DEPT000017', 65000, 85000, 'Ensure compliance');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000018')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000018', 'IR Specialist', 'DEPT000018', 80000, 100000, 'Investor relations');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000019')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000019', 'PR Manager', 'DEPT000019', 75000, 95000, 'Public relations');
IF NOT EXISTS (SELECT 1 FROM dbo.Positions WITH (UPDLOCK,HOLDLOCK) WHERE PositionID='POST000020')
    INSERT INTO dbo.Positions (PositionID, PositionTitle, DepartmentID, MinSalary, MaxSalary, JobDescription) VALUES ('POST000020', 'Facilities Manager', 'DEPT000020', 60000, 80000, 'Manage facilities');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000001')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000001', 'John', 'Doe', 'john.doe@example.com', '1234567890', '2020-01-15', 50000, 5000, '2024-06-30', 'DEPT000001', 'POST000001');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000002')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000002', 'Jane', 'Smith', 'jane.smith@example.com', '2345678901', '2019-03-20', 60000, 6000, '2024-06-30', 'DEPT000002', 'POST000002');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000003')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000003', 'Robert', 'Brown', 'robert.brown@example.com', '3456789012', '2021-05-10', 55000, 5500, '2024-06-30', 'DEPT000003', 'POST000003');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000004')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000004', 'Emily', 'Davis', 'emily.davis@example.com', '4567890123', '2018-07-25', 70000, 7000, '2024-06-30', 'DEPT000004', 'POST000004');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000005')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000005', 'Michael', 'Wilson', 'michael.wilson@example.com', '5678901234', '2020-11-05', 50000, 4000, '2024-06-30', 'DEPT000005', 'POST000005');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000006')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000006', 'Sarah', 'Miller', 'sarah.miller@example.com', '6789012345', '2019-08-15', 62000, 6200, '2024-06-30', 'DEPT000006', 'POST000006');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000007')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000007', 'David', 'Martinez', 'david.martinez@example.com', '7890123456', '2022-03-18', 58000, 5800, '2024-06-30', 'DEPT000007', 'POST000007');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000008')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000008', 'Laura', 'Anderson', 'laura.anderson@example.com', '8901234567', '2018-12-22', 51000, 5100, '2024-06-30', 'DEPT000008', 'POST000008');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000009')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000009', 'James', 'Taylor', 'james.taylor@example.com', '9012345678', '2017-09-30', 56000, 5600, '2024-06-30', 'DEPT000009', 'POST000009');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000010')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000010', 'Jessica', 'Thomas', 'jessica.thomas@example.com', '1123456789', '2016-06-01', 53000, 5300, '2024-06-30', 'DEPT000010', 'POST000010');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000011')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000011', 'William', 'Jackson', 'william.jackson@example.com', '2234567890', '2021-11-11', 49000, 4900, '2024-06-30', 'DEPT000011', 'POST000011');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000012')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000012', 'Olivia', 'White', 'olivia.white@example.com', '3345678901', '2020-10-19', 61000, 6100, '2024-06-30', 'DEPT000012', 'POST000012');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000013')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000013', 'Joshua', 'Harris', 'joshua.harris@example.com', '4456789012', '2018-04-13', 54000, 5400, '2024-06-30', 'DEPT000013', 'POST000013');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000014')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000014', 'Sophia', 'Clark', 'sophia.clark@example.com', '5567890123', '2019-07-29', 58000, 5800, '2024-06-30', 'DEPT000014', 'POST000014');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000015')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000015', 'Daniel', 'Lewis', 'daniel.lewis@example.com', '6678901234', '2022-02-05', 50000, 5000, '2024-06-30', 'DEPT000015', 'POST000015');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000016')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000016', 'Ava', 'Robinson', 'ava.robinson@example.com', '7789012345', '2021-06-23', 62000, 6200, '2024-06-30', 'DEPT000016', 'POST000016');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000017')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000017', 'Matthew', 'Walker', 'matthew.walker@example.com', '8890123456', '2020-09-17', 57000, 5700, '2024-06-30', 'DEPT000017', 'POST000017');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000018')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000018', 'Mia', 'Hall', 'mia.hall@example.com', '9901234567', '2019-05-21', 59000, 5900, '2024-06-30', 'DEPT000018', 'POST000018');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000019')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000019', 'Christopher', 'Allen', 'christopher.allen@example.com', '1012345678', '2018-11-08', 52000, 5200, '2024-06-30', 'DEPT000019', 'POST000019');
IF NOT EXISTS (SELECT 1 FROM dbo.Employees WITH (UPDLOCK,HOLDLOCK) WHERE EmployeeID='EMP000020')
    INSERT INTO dbo.Employees (EmployeeID, FirstName, LastName, Email, PhoneNumber, HireDate, BaseSalary, Bonus, PayDate, DepartmentID, PositionID) VALUES ('EMP000020', 'Isabella', 'Young', 'isabella.young@example.com', '1123456789', '2017-08-03', 60000, 6000, '2024-06-30', 'DEPT000020', 'POST000020');
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000001')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000001', 'EMP000001', GETDATE(), 'Excellent performance.', 9);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000002')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000002', 'EMP000002', GETDATE(), 'Good performance.', 7);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000003')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000003', 'EMP000003', GETDATE(), 'Satisfactory performance.', 5);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000004')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000004', 'EMP000004', GETDATE(), 'Needs improvement.', 4);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000005')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000005', 'EMP000005', GETDATE(), 'Outstanding performance.', 1);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000006')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000006', 'EMP000006', GETDATE(), 'Meets expectations.', 6);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000007')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000007', 'EMP000007', GETDATE(), 'Below expectations.', 3);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000008')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000008', 'EMP000008', GETDATE(), 'Exceeds expectations.', 8);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000009')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000009', 'EMP000009', GETDATE(), 'Good teamwork.', 7);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000010')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000010', 'EMP000010', GETDATE(), 'Poor performance.', 2);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000011')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000011', 'EMP000011', GETDATE(), 'Excellent leadership.', 9);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000012')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000012', 'EMP000012', GETDATE(), 'Satisfactory work.', 5);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000013')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000013', 'EMP000013', GETDATE(), 'Room for growth.', 4);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000014')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000014', 'EMP000014', GETDATE(), 'Highly dependable.', 8);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000015')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000015', 'EMP000015', GETDATE(), 'Outstanding commitment.', 9);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000016')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000016', 'EMP000016', GETDATE(), 'Average performance.', 6);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000017')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000017', 'EMP000017', GETDATE(), 'Needs significant improvement.', 3);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000018')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000018', 'EMP000018', GETDATE(), 'Consistently good.', 7);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000019')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000019', 'EMP000019', GETDATE(), 'Excellent innovation.', 9);
IF NOT EXISTS (SELECT 1 FROM dbo.PerformanceReview WITH (UPDLOCK,HOLDLOCK) WHERE ReviewID='REV000020')
    INSERT INTO dbo.PerformanceReview (ReviewID, EmployeeID, ReviewDate, Comments, Rating) VALUES ('REV000020', 'EMP000020', GETDATE(), 'Underperformed.', 2);
COMMIT TRANSACTION;
END TRY
BEGIN CATCH
IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
THROW;
END CATCH;
