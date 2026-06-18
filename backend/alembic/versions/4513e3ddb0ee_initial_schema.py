"""Initial schema

Revision ID: 4513e3ddb0ee
Revises: 
Create Date: 2026-06-18 15:59:12

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
import geoalchemy2

# revision identifiers, used by Alembic.
revision: str = '4513e3ddb0ee'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. Enable PostGIS extension (required for geospatial mappings)
    op.execute("CREATE EXTENSION IF NOT EXISTS postgis;")

    # 2. Create users table
    op.create_table(
        'users',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('email', sa.String(length=255), nullable=False),
        sa.Column('hashed_password', sa.String(length=255), nullable=False),
        sa.Column('role', sa.String(length=64), server_default='citizen', nullable=False),
        sa.Column('consent_alerts', sa.Boolean(), server_default='false', nullable=False),
        sa.Column('phone_number', sa.String(length=255), nullable=True),
        sa.Column('created_at', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_users_email'), 'users', ['email'], unique=True)
    op.create_index(op.f('ix_users_id'), 'users', ['id'], unique=False)

    # 3. Create weather_forecast_records table
    op.create_table(
        'weather_forecast_records',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('source', sa.String(length=64), nullable=False),
        sa.Column('ingestion_time', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('model_issue_time', sa.DateTime(), nullable=False),
        sa.Column('transformation_history', postgresql.JSONB(astext_type=sa.Text()), server_default='[]', nullable=False),
        sa.Column('data_payload', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_weather_forecast_records_id'), 'weather_forecast_records', ['id'], unique=False)

    # 4. Create graph_nodes table
    op.create_table(
        'graph_nodes',
        sa.Column('id', sa.String(length=64), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.Column('geom', geoalchemy2.types.Geometry(geometry_type='GEOMETRY', srid=4326, from_text='ST_GeomFromEWKT', name='geometry', nullable=True), nullable=True),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('idx_nodes_type', 'graph_nodes', ['type'], unique=False)

    # 5. Create graph_edges table
    op.create_table(
        'graph_edges',
        sa.Column('source_id', sa.String(length=64), nullable=False),
        sa.Column('target_id', sa.String(length=64), nullable=False),
        sa.Column('type', sa.String(length=64), nullable=False),
        sa.Column('properties', postgresql.JSONB(astext_type=sa.Text()), server_default='{}', nullable=False),
        sa.ForeignKeyConstraint(['source_id'], ['graph_nodes.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['target_id'], ['graph_nodes.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('source_id', 'target_id', 'type')
    )
    op.create_index('idx_edges_lookup', 'graph_edges', ['source_id', 'target_id'], unique=False)

    # 6. Create evaluation_logs table
    op.create_table(
        'evaluation_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('query', sa.String(), nullable=False),
        sa.Column('response', sa.String(), nullable=False),
        sa.Column('retrieval_precision', sa.Float(), nullable=False),
        sa.Column('citation_accuracy', sa.Float(), nullable=False),
        sa.Column('hallucination_rate', sa.Float(), nullable=False),
        sa.Column('response_latency', sa.Float(), nullable=False),
        sa.Column('confidence_score', sa.Float(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_evaluation_logs_id'), 'evaluation_logs', ['id'], unique=False)

    # 7. Create audit_logs table
    op.create_table(
        'audit_logs',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('client_ip', sa.String(length=64), nullable=False),
        sa.Column('user_id', sa.Integer(), nullable=True),
        sa.Column('requested_endpoint', sa.String(length=255), nullable=False),
        sa.Column('action', sa.String(length=255), nullable=False),
        sa.Column('timestamp', sa.DateTime(), server_default=sa.func.now(), nullable=False),
        sa.Column('payload_hash', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_audit_logs_id'), 'audit_logs', ['id'], unique=False)


def downgrade() -> None:
    op.drop_index(op.f('ix_audit_logs_id'), table_name='audit_logs')
    op.drop_table('audit_logs')
    op.drop_index(op.f('ix_evaluation_logs_id'), table_name='evaluation_logs')
    op.drop_table('evaluation_logs')
    op.drop_index('idx_edges_lookup', table_name='graph_edges')
    op.drop_table('graph_edges')
    op.drop_index('idx_nodes_type', table_name='graph_nodes')
    op.drop_table('graph_nodes')
    op.drop_index(op.f('ix_weather_forecast_records_id'), table_name='weather_forecast_records')
    op.drop_table('weather_forecast_records')
    op.drop_index(op.f('ix_users_id'), table_name='users')
    op.drop_index(op.f('ix_users_email'), table_name='users')
    op.drop_table('users')
    op.execute("DROP EXTENSION IF EXISTS postgis;")
