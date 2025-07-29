"""Add comprehensive audit tables for ACCA Manual J compliance

Revision ID: add_audit_tables
Revises: 458d242aaf4d
Create Date: 2025-07-29 12:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = 'add_audit_tables'
down_revision: Union[str, None] = '458d242aaf4d'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create calculation_audits table
    op.create_table('calculation_audits',
        sa.Column('audit_id', sa.String(), nullable=False),
        sa.Column('project_id', sa.String(), nullable=False),
        sa.Column('user_id', sa.String(), nullable=False),
        sa.Column('calculation_timestamp', sa.DateTime(), nullable=False),
        sa.Column('calculation_method', sa.String(), nullable=False),
        sa.Column('software_version', sa.String(), nullable=False),
        sa.Column('blueprint_schema', sa.JSON(), nullable=True),
        sa.Column('climate_data', sa.JSON(), nullable=True),
        sa.Column('system_parameters', sa.JSON(), nullable=True),
        sa.Column('envelope_data', sa.JSON(), nullable=True),
        sa.Column('calculation_results', sa.JSON(), nullable=True),
        sa.Column('heating_total_btu', sa.Integer(), nullable=True),
        sa.Column('cooling_total_btu', sa.Integer(), nullable=True),
        sa.Column('data_quality_score', sa.Float(), nullable=True),
        sa.Column('validation_flags', sa.JSON(), nullable=True),
        sa.Column('acca_compliance_verified', sa.Boolean(), nullable=False),
        sa.Column('processing_time_seconds', sa.Float(), nullable=True),
        sa.Column('processing_stages', sa.JSON(), nullable=True),
        sa.Column('error_details', sa.JSON(), nullable=True),
        sa.Column('reviewed_by', sa.String(), nullable=True),
        sa.Column('review_timestamp', sa.DateTime(), nullable=True),
        sa.Column('review_notes', sa.Text(), nullable=True),
        sa.Column('review_approved', sa.Boolean(), nullable=True),
        sa.PrimaryKeyConstraint('audit_id')
    )
    op.create_index('idx_calc_audit_project_user', 'calculation_audits', ['project_id', 'user_id'])
    op.create_index('idx_calc_audit_timestamp', 'calculation_audits', ['calculation_timestamp'])
    op.create_index('idx_calc_audit_loads', 'calculation_audits', ['heating_total_btu', 'cooling_total_btu'])
    op.create_index(op.f('ix_calculation_audits_project_id'), 'calculation_audits', ['project_id'])
    op.create_index(op.f('ix_calculation_audits_user_id'), 'calculation_audits', ['user_id'])

    # Create room_calculation_details table
    op.create_table('room_calculation_details',
        sa.Column('detail_id', sa.String(), nullable=False),
        sa.Column('audit_id', sa.String(), nullable=False),
        sa.Column('room_name', sa.String(), nullable=False),
        sa.Column('room_area_sqft', sa.Float(), nullable=False),
        sa.Column('room_type', sa.String(), nullable=False),
        sa.Column('floor_number', sa.Integer(), nullable=False),
        sa.Column('dimensions_ft', sa.JSON(), nullable=True),
        sa.Column('window_count', sa.Integer(), nullable=False),
        sa.Column('orientation', sa.String(), nullable=True),
        sa.Column('heating_load_btu', sa.Float(), nullable=False),
        sa.Column('cooling_load_btu', sa.Float(), nullable=False),
        sa.Column('load_components', sa.JSON(), nullable=True),
        sa.Column('required_airflow_cfm', sa.Integer(), nullable=True),
        sa.Column('recommended_duct_size', sa.String(), nullable=True),
        sa.Column('calculation_method', sa.String(), nullable=False),
        sa.Column('data_confidence', sa.Float(), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['calculation_audits.audit_id'], ),
        sa.PrimaryKeyConstraint('detail_id')
    )
    op.create_index('idx_room_detail_audit', 'room_calculation_details', ['audit_id'])
    op.create_index('idx_room_detail_loads', 'room_calculation_details', ['heating_load_btu', 'cooling_load_btu'])
    op.create_index(op.f('ix_room_calculation_details_audit_id'), 'room_calculation_details', ['audit_id'])

    # Create data_source_metadata table
    op.create_table('data_source_metadata',
        sa.Column('metadata_id', sa.String(), nullable=False),
        sa.Column('audit_id', sa.String(), nullable=False),
        sa.Column('source_type', sa.String(), nullable=False),
        sa.Column('source_name', sa.String(), nullable=False),
        sa.Column('source_version', sa.String(), nullable=True),
        sa.Column('data_completeness', sa.Float(), nullable=False),
        sa.Column('data_confidence', sa.Float(), nullable=False),
        sa.Column('extraction_method', sa.String(), nullable=False),
        sa.Column('source_metadata', sa.JSON(), nullable=True),
        sa.Column('extracted_at', sa.DateTime(), nullable=False),
        sa.Column('last_updated', sa.DateTime(), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['calculation_audits.audit_id'], ),
        sa.PrimaryKeyConstraint('metadata_id')
    )
    op.create_index(op.f('ix_data_source_metadata_audit_id'), 'data_source_metadata', ['audit_id'])

    # Create compliance_checks table
    op.create_table('compliance_checks',
        sa.Column('check_id', sa.String(), nullable=False),
        sa.Column('audit_id', sa.String(), nullable=False),
        sa.Column('check_category', sa.String(), nullable=False),
        sa.Column('check_name', sa.String(), nullable=False),
        sa.Column('check_description', sa.String(), nullable=False),
        sa.Column('passed', sa.Boolean(), nullable=False),
        sa.Column('check_value', sa.Float(), nullable=True),
        sa.Column('expected_range_min', sa.Float(), nullable=True),
        sa.Column('expected_range_max', sa.Float(), nullable=True),
        sa.Column('severity', sa.String(), nullable=False),
        sa.Column('recommendation', sa.Text(), nullable=True),
        sa.Column('checked_at', sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(['audit_id'], ['calculation_audits.audit_id'], ),
        sa.PrimaryKeyConstraint('check_id')
    )
    op.create_index('idx_compliance_audit', 'compliance_checks', ['audit_id'])
    op.create_index('idx_compliance_category', 'compliance_checks', ['check_category', 'passed'])
    op.create_index(op.f('ix_compliance_checks_audit_id'), 'compliance_checks', ['audit_id'])


def downgrade() -> None:
    # Drop tables in reverse order to handle foreign key constraints
    op.drop_table('compliance_checks')
    op.drop_table('data_source_metadata')  
    op.drop_table('room_calculation_details')
    op.drop_table('calculation_audits')