-- Supplemental committed-change journal. Not Azure SQL Audit or Defender.
-- Uses existing database storage; never copies salaries, contact data or passwords.
SET XACT_ABORT ON;
SET NOCOUNT ON;
IF NOT EXISTS (SELECT 1 FROM dbo.EMS_SchemaVersion WHERE Version=1)
    THROW 51000, 'EMS: Supported application schema required.', 1;
IF DATABASE_PRINCIPAL_ID('ems_app_runtime') IS NULL
    THROW 51000, 'EMS: Restricted runtime role required.', 1;
IF OBJECT_ID('dbo.EMS_ChangeJournal','U') IS NOT NULL
    AND OBJECT_ID('dbo.EMS_SecurityFeatures','U') IS NULL
    THROW 51000, 'EMS: Unrecognized existing journal; operator review required.', 1;
BEGIN TRY
    BEGIN TRANSACTION;
    IF OBJECT_ID('dbo.EMS_SecurityFeatures','U') IS NULL
        CREATE TABLE dbo.EMS_SecurityFeatures (
            Feature VARCHAR(40) NOT NULL PRIMARY KEY,
            Version INT NOT NULL,
            InstalledUtc DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME()
        );
    IF OBJECT_ID('dbo.EMS_ChangeJournal','U') IS NULL
        CREATE TABLE dbo.EMS_ChangeJournal (
            EventId BIGINT IDENTITY(1,1) NOT NULL PRIMARY KEY,
            OccurredUtc DATETIME2(7) NOT NULL DEFAULT SYSUTCDATETIME(),
            StatementId UNIQUEIDENTIFIER NOT NULL,
            DatabaseActor NVARCHAR(128) NOT NULL,
            ClaimedAppActor NVARCHAR(20) NULL,
            ObjectName VARCHAR(128) NOT NULL,
            Operation VARCHAR(40) NOT NULL,
            EntityId NVARCHAR(128) NULL,
            SubjectRole VARCHAR(10) NULL
        );
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE object_id=OBJECT_ID('dbo.EMS_ChangeJournal') AND name='EMS_Journal_Time')
        CREATE INDEX EMS_Journal_Time ON dbo.EMS_ChangeJournal(OccurredUtc, EventId);

    -- Fixed allowlisted identifiers only. SQL ownership chaining permits trigger
    -- inserts while direct runtime reads/inserts/updates/deletes remain denied.
    DECLARE @Table SYSNAME, @Key SYSNAME, @RoleExpression NVARCHAR(200), @SQL NVARCHAR(MAX);
    DECLARE journal_tables CURSOR LOCAL FAST_FORWARD FOR
        SELECT TableName, KeyName FROM (VALUES
            ('Departments','DepartmentID'), ('Positions','PositionID'),
            ('Employees','EmployeeID'), ('PerformanceReview','ReviewID'), ('Sign_Up','Username')
        ) t(TableName,KeyName);
    OPEN journal_tables;
    FETCH NEXT FROM journal_tables INTO @Table,@Key;
    WHILE @@FETCH_STATUS=0
    BEGIN
        SET @RoleExpression=CASE WHEN @Table='Sign_Up' THEN
            N'CASE WHEN i.Role=''admin'' OR d.Role=''admin'' THEN ''admin'' ELSE COALESCE(i.Role,d.Role) END'
            ELSE N'NULL' END;
        SET @SQL=N'CREATE OR ALTER TRIGGER dbo.'+QUOTENAME('EMS_Journal_'+@Table)+N'
            ON dbo.'+QUOTENAME(@Table)+N' AFTER INSERT, UPDATE, DELETE AS
            BEGIN
                SET NOCOUNT ON;
                DECLARE @Request UNIQUEIDENTIFIER=NEWID();
                INSERT dbo.EMS_ChangeJournal
                    (StatementId,DatabaseActor,ClaimedAppActor,ObjectName,Operation,EntityId,SubjectRole)
                SELECT @Request,ORIGINAL_LOGIN(),
                    CONVERT(NVARCHAR(20),SESSION_CONTEXT(N''ems.app_actor'')),
                    N'''+@Table+N''',
                    CASE WHEN i.'+QUOTENAME(@Key)+N' IS NULL THEN ''DELETE''
                         WHEN d.'+QUOTENAME(@Key)+N' IS NULL THEN ''INSERT'' ELSE ''UPDATE'' END,
                    CONVERT(NVARCHAR(128),COALESCE(i.'+QUOTENAME(@Key)+N',d.'+QUOTENAME(@Key)+N')),
                    '+@RoleExpression+N'
                FROM inserted i FULL OUTER JOIN deleted d ON i.'+QUOTENAME(@Key)+N'=d.'+QUOTENAME(@Key)+N';
            END';
        EXEC sys.sp_executesql @SQL;
        FETCH NEXT FROM journal_tables INTO @Table,@Key;
    END;
    CLOSE journal_tables;
    DEALLOCATE journal_tables;

    EXEC(N'CREATE OR ALTER TRIGGER EMS_Journal_DDL ON DATABASE FOR DDL_DATABASE_LEVEL_EVENTS AS
        BEGIN
            SET NOCOUNT ON;
            DECLARE @Event XML=EVENTDATA();
            INSERT dbo.EMS_ChangeJournal
                (StatementId,DatabaseActor,ObjectName,Operation)
            VALUES (NEWID(),ORIGINAL_LOGIN(),
                COALESCE(@Event.value(''(/EVENT_INSTANCE/ObjectName)[1]'',''VARCHAR(128)''),''DATABASE''),
                @Event.value(''(/EVENT_INSTANCE/EventType)[1]'',''VARCHAR(40)''));
        END');
    DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.EMS_ChangeJournal TO ems_app_runtime;
    DENY SELECT, INSERT, UPDATE, DELETE ON OBJECT::dbo.EMS_SecurityFeatures TO ems_app_runtime;
    IF NOT EXISTS (SELECT 1 FROM dbo.EMS_SecurityFeatures WHERE Feature='CommittedChangeJournal')
        INSERT dbo.EMS_SecurityFeatures(Feature,Version) VALUES ('CommittedChangeJournal',1);
    ELSE IF EXISTS (SELECT 1 FROM dbo.EMS_SecurityFeatures WHERE Feature='CommittedChangeJournal' AND Version<>1)
        THROW 51000, 'EMS: Unsupported change journal version.', 1;
    COMMIT TRANSACTION;
END TRY
BEGIN CATCH
    IF XACT_STATE()<>0 ROLLBACK TRANSACTION;
    THROW;
END CATCH;
