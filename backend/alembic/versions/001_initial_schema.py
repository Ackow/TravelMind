"""initial schema

Revision ID: 001
Revises: 
Create Date: 2026-08-18 10:00:00.000000

"""
from typing import Union
from collections.abc import Sequence
from alembic import op
import sqlalchemy as sa

revision: str = '001'
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # 1. 创建 trips 表
    op.create_table(
        'trips',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('revision', sa.Integer(), nullable=False),
        sa.Column('current_plan_version', sa.Integer(), nullable=True),
        sa.Column('active_planning_run_id', sa.Uuid(), nullable=True),
        sa.Column('request_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('updated_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )

    # 2. 创建 plan_versions 表
    op.create_table(
        'plan_versions',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('trip_id', sa.Uuid(), nullable=False),
        sa.Column('version', sa.Integer(), nullable=False),
        sa.Column('parent_version', sa.Integer(), nullable=True),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('trigger', sa.String(length=50), nullable=False),
        sa.Column('itinerary_json', sa.JSON(), nullable=False),
        sa.Column('constraint_report_json', sa.JSON(), nullable=False),
        sa.Column('change_summary', sa.Text(), nullable=False),
        sa.Column('planning_run_id', sa.Uuid(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('accepted_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('trip_id', 'version', name='uq_trip_plan_version')
    )
    op.create_index('ix_plan_versions_trip_id', 'plan_versions', ['trip_id'])

    # 3. 创建 planning_runs 表
    op.create_table(
        'planning_runs',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('trip_id', sa.Uuid(), nullable=False),
        sa.Column('trigger', sa.String(length=50), nullable=False),
        sa.Column('status', sa.String(length=50), nullable=False),
        sa.Column('progress_percent', sa.Integer(), nullable=False),
        sa.Column('current_step', sa.String(length=100), nullable=True),
        sa.Column('base_plan_version', sa.Integer(), nullable=True),
        sa.Column('result_plan_version', sa.Integer(), nullable=True),
        sa.Column('feedback_id', sa.Uuid(), nullable=True),
        sa.Column('repair_attempts', sa.Integer(), nullable=False),
        sa.Column('max_repair_attempts', sa.Integer(), nullable=False),
        sa.Column('error_json', sa.JSON(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.Column('started_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('finished_at', sa.DateTime(timezone=True), nullable=True),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_planning_runs_trip_id', 'planning_runs', ['trip_id'])

    # 4. 创建 planning_events 表
    op.create_table(
        'planning_events',
        sa.Column('id', sa.String(length=100), nullable=False),
        sa.Column('run_id', sa.Uuid(), nullable=False),
        sa.Column('sequence', sa.Integer(), nullable=False),
        sa.Column('type', sa.String(length=50), nullable=False),
        sa.Column('step', sa.String(length=100), nullable=True),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('payload_json', sa.JSON(), nullable=False),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['run_id'], ['planning_runs.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('run_id', 'sequence', name='uq_run_event_sequence')
    )
    op.create_index('ix_planning_events_run_id', 'planning_events', ['run_id'])

    # 5. 创建 user_feedbacks 表
    op.create_table(
        'user_feedbacks',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('trip_id', sa.Uuid(), nullable=False),
        sa.Column('base_plan_version', sa.Integer(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('operations_json', sa.JSON(), nullable=False),
        sa.Column('affected_dates_json', sa.JSON(), nullable=False),
        sa.Column('affected_activity_ids_json', sa.JSON(), nullable=False),
        sa.Column('global_scope', sa.Boolean(), nullable=False),
        sa.Column('requires_clarification', sa.Boolean(), nullable=False),
        sa.Column('clarification_question', sa.Text(), nullable=True),
        sa.Column('planning_run_id', sa.Uuid(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(['trip_id'], ['trips.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_user_feedbacks_trip_id', 'user_feedbacks', ['trip_id'])

    # 6. 创建 tool_calls 表
    op.create_table(
        'tool_calls',
        sa.Column('id', sa.Uuid(), nullable=False),
        sa.Column('run_id', sa.Uuid(), nullable=False),
        sa.Column('tool_name', sa.String(length=100), nullable=False),
        sa.Column('input_json', sa.JSON(), nullable=False),
        sa.Column('output_json', sa.JSON(), nullable=False),
        sa.Column('duration_ms', sa.Integer(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_tool_calls_run_id', 'tool_calls', ['run_id'])


def downgrade() -> None:
    op.drop_table('tool_calls')
    op.drop_table('user_feedbacks')
    op.drop_table('planning_events')
    op.drop_table('planning_runs')
    op.drop_table('plan_versions')
    op.drop_table('trips')