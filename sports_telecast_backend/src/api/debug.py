"""
Debug endpoints for development use only.

This module exposes routes under the /debug prefix that allow inspection of the
database state from within the running backend instance. These endpoints must
not be enabled in production environments.

Routes:
- GET /debug/tables: Lists all tables in the 'public' schema and returns the current
  Alembic migration version for the connected database.
"""
from __future__ import annotations

from typing import List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy import text
from sqlalchemy.ext.asyncio import AsyncSession

# Attempt to import the project's async session dependency.
# Adjusted to match existing project structure: src/database/connection.py
try:
    # get_db_session should yield an AsyncSession when used as a dependency
    from src.database.connection import get_db_session  # type: ignore
except Exception as e:  # pragma: no cover - defensive in case of refactor
    raise RuntimeError(
        "Failed to import get_db_session from src.database.connection. "
        "Please ensure the async DB session dependency is available."
    ) from e

router = APIRouter(
    prefix="/debug",
    tags=["Debug"],
    responses={404: {"description": "Not found"}},
)


class DebugTableInfo(BaseModel):
    """Model describing a single table in the public schema."""

    schema: str = Field(..., description="Schema name (should be 'public').")
    name: str = Field(..., description="Table name.")
    type: str = Field(..., description="Object type (e.g., 'r' for ordinary table).")


class DebugTablesResponse(BaseModel):
    """Response payload for /debug/tables endpoint."""

    environment: str = Field(
        default="development",
        description="Environment indicator. This endpoint is meant for development only.",
    )
    tables: List[DebugTableInfo] = Field(
        default_factory=list,
        description="List of tables discovered in the 'public' schema.",
    )
    alembic_version: Optional[str] = Field(
        default=None,
        description="Current Alembic migration version from alembic_version table, if present.",
    )
    notes: Optional[str] = Field(
        default="Do not enable this endpoint in production.",
        description="Additional notes.",
    )


# PUBLIC_INTERFACE
@router.get(
    "/tables",
    response_model=DebugTablesResponse,
    summary="Debug: List DB tables and Alembic version",
    description=(
        "Development-only endpoint. Returns the list of tables in the 'public' schema "
        "and the current Alembic migration version for the database this backend is connected to.\n\n"
        "Security: This endpoint should NOT be exposed in production."
    ),
)
async def debug_tables(db: AsyncSession = Depends(get_db_session)) -> DebugTablesResponse:
    """
    Debug endpoint to inspect database tables and Alembic migration version.

    Parameters:
        db (AsyncSession): The application's async SQLAlchemy session injected via dependency.

    Returns:
        DebugTablesResponse: Object containing:
            - environment: string indicating development-only usage
            - tables: list of tables in the 'public' schema
            - alembic_version: the current Alembic version string (if table exists)
            - notes: warnings about production exposure

    Raises:
        HTTPException: If a database error occurs while executing inspection queries.
    """
    try:
        # List all relations in public schema. Using pg_catalog to avoid requiring SQLAlchemy inspector sync path.
        tables_sql = text(
            """
            SELECT n.nspname AS schema,
                   c.relname AS name,
                   c.relkind AS type
            FROM pg_catalog.pg_class c
            JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
            WHERE n.nspname = 'public'
              AND c.relkind IN ('r','p','v','m','f') -- tables, partitions, views, matviews, foreign tables
            ORDER BY c.relname;
            """
        )
        result = await db.execute(tables_sql)
        rows = result.mappings().all()
        tables: List[DebugTableInfo] = [
            DebugTableInfo(schema=row["schema"], name=row["name"], type=row["type"])
            for row in rows
        ]

        # Try to fetch Alembic version if alembic_version table exists.
        # We guard the select with EXISTS check to avoid errors when the table is missing.
        version_sql = text(
            """
            DO $$
            BEGIN
                IF EXISTS (
                    SELECT 1
                    FROM pg_catalog.pg_class c
                    JOIN pg_catalog.pg_namespace n ON n.oid = c.relnamespace
                    WHERE n.nspname='public' AND c.relname='alembic_version' AND c.relkind='r'
                ) THEN
                    -- dummy, will be replaced by select below
                    NULL;
                END IF;
            END $$;
            """
        )
        # Execute the guard DO block to ensure compatibility in environments without the table.
        await db.execute(version_sql)

        # Now attempt selection; if missing, catch gracefully.
        alembic_version: Optional[str] = None
        try:
            version_select = text("SELECT version_num FROM alembic_version LIMIT 1;")
            vresult = await db.execute(version_select)
            vrow = vresult.first()
            if vrow:
                alembic_version = vrow[0]
        except Exception:
            # Table doesn't exist or not accessible
            alembic_version = None

        return DebugTablesResponse(
            environment="development",
            tables=tables,
            alembic_version=alembic_version,
            notes="Do not enable this endpoint in production.",
        )
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database inspection error: {e}") from e
