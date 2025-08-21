# Database Models and Enum Storage Notes

This backend uses SQLAlchemy ORM with Enum values that are intended to be stored as lowercase strings in the database.

Key points:
- User roles are defined in src/database/models.py as:
  - UserRoleEnum with values: "user", "admin", "moderator" (lowercase values; member names are uppercase).
- The ORM mapping for users.role uses SQLAlchemy Enum with name "userroleenum" and native_enum=True.

Expected persistence:
- When persisting a UserDB record, SQLAlchemy should send the Enum's .value (lowercase) to the database.
- Example: role = UserRoleEnum.USER -> inserts "user" into the column.

Potential mismatch and root cause of uppercase INSERT values:
- If you observe SQLAlchemy logs showing role => 'USER' (uppercase), it usually means one of:
  1) The underlying database type for the column is a PostgreSQL enum "userroleenum" that was created elsewhere with uppercase labels ('USER','ADMIN','MODERATOR'). SQLAlchemy may then serialize using the Enum member name to match the DB labels.
  2) Upstream code assigned a raw string "USER" to the role field, bypassing the enum normalization step.

Migrations vs ORM:
- Current Alembic migration 002 adds the `users.role` column as VARCHAR(32) with default 'user' and does NOT create a PostgreSQL enum type.
- Meanwhile, the ORM uses a native PostgreSQL enum mapping (create_type=False). If the database already has an enum "userroleenum" with uppercase labels, this mismatch leads to uppercase values being observed in bind parameters.

How to fix consistently:
Option A (String column):
- Change the ORM mapping for UserDB.role to a String(32) column and enforce allowed values at the application level.
- Add a database CHECK constraint via Alembic to restrict values to ('user','admin','moderator').

Option B (Native PostgreSQL enum):
- Update Alembic to create/ensure a PostgreSQL enum type "userroleenum" with lowercase labels ('user','admin','moderator').
- Alter the users.role column to use this enum type.
- Keep ORM mapping as native_enum=True and set create_type=True for first-time deployments. For environments where the DB type already exists, keep create_type=False.

Additional checks:
- Ensure seeders or tests do not assign role="USER" uppercase.
- The repository normalization (UserRepository._normalize_role) coerces arbitrary input to lowercase-backed Enum members, but if the DB column/type expects uppercase labels, you will still see uppercase being used to match that type.

Troubleshooting steps:
1) Inspect the DB column and type:
   - \d+ public.users
   - \dT+ userroleenum
2) If userroleenum exists with uppercase labels, either recreate it with lowercase labels (data migration) or switch to String storage (Option A).
3) Verify API layer (Pydantic) is not sending role on registration; default role is user.

