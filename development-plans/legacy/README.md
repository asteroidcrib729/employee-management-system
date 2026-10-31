# Preserved coursework

These are historical artifacts, not current setup instructions or security claims.

- `original-source.zip` preserves the original Python script and all three SQL files byte-for-byte. It includes an unguarded database-drop script. Do not execute archived SQL against a working database.
- The DOCX/PDF reports, JPG diagrams, and original RAR have been moved here unchanged.
- `original-hashes.json` records each original repository path and SHA-256 digest. The source ZIP was checked against those hashes before the original loose source files were removed.
- The original setup scripts were duplicates. The current schema has one authoritative source in `src/ems/sql/001_schema.sql`; migration and demo seed are separate. Application data access uses SQLAlchemy ORM models in `src/ems/models.py`.

Corrections to the original documents:

- The original password implementation had unsalted SHA-256 hashes, despite the report's reference to salts. The current implementation stores a salt inside its versioned PBKDF2 hash string.
- There is no separate salaries table. Compensation fields belong to `Employees`.
- The original ER diagram omitted employee compensation fields and does not describe the current constraints, text phone field, account roles, or schema-version table. See [the current design](../design.md).
- Claims about dashboards, analytics, payroll integration, disaster recovery, and employee self-service do not describe implemented application features.
