"""add GitHub App ownership and repository links

Revision ID: b7f31d3c2e09
Revises: 8c6281353437
"""
from alembic import op
import sqlalchemy as sa

revision = "b7f31d3c2e09"
down_revision = "8c6281353437"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("app_users",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("session_token", sa.String(128), nullable=False, unique=True),
        sa.Column("github_login", sa.String(255), nullable=True),
        sa.Column("github_account_id", sa.Integer(), nullable=True, unique=True),
        sa.Column("github_oauth_state", sa.String(128), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_app_users_session_token", "app_users", ["session_token"])
    op.create_table("github_installations",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("installation_id", sa.Integer(), nullable=False, unique=True),
        sa.Column("user_id", sa.Integer(), sa.ForeignKey("app_users.id", ondelete="CASCADE"), nullable=False),
        sa.Column("account_login", sa.String(255), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
    )
    op.create_index("ix_github_installations_user_id", "github_installations", ["user_id"])
    op.create_table("github_repositories",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("installation_id", sa.Integer(), sa.ForeignKey("github_installations.id", ondelete="CASCADE"), nullable=False),
        sa.Column("github_repository_id", sa.Integer(), nullable=False),
        sa.Column("full_name", sa.String(500), nullable=False),
        sa.Column("default_branch", sa.String(255), nullable=False),
        sa.UniqueConstraint("installation_id", "github_repository_id", name="uq_installation_repository"),
    )
    op.create_index("ix_github_repositories_installation_id", "github_repositories", ["installation_id"])
    op.create_index("ix_github_repositories_github_repository_id", "github_repositories", ["github_repository_id"])
    op.add_column("projects", sa.Column("owner_user_id", sa.Integer(), nullable=True))
    op.add_column("projects", sa.Column("github_repository_id", sa.Integer(), nullable=True))
    op.create_foreign_key("fk_projects_owner_user", "projects", "app_users", ["owner_user_id"], ["id"], ondelete="SET NULL")
    op.create_foreign_key("fk_projects_github_repository", "projects", "github_repositories", ["github_repository_id"], ["id"], ondelete="SET NULL")
    op.create_index("ix_projects_owner_user_id", "projects", ["owner_user_id"])
    op.create_index("ix_projects_github_repository_id", "projects", ["github_repository_id"])


def downgrade() -> None:
    op.drop_index("ix_projects_github_repository_id", table_name="projects")
    op.drop_index("ix_projects_owner_user_id", table_name="projects")
    op.drop_constraint("fk_projects_github_repository", "projects", type_="foreignkey")
    op.drop_constraint("fk_projects_owner_user", "projects", type_="foreignkey")
    op.drop_column("projects", "github_repository_id")
    op.drop_column("projects", "owner_user_id")
    op.drop_table("github_repositories")
    op.drop_table("github_installations")
    op.drop_index("ix_app_users_session_token", table_name="app_users")
    op.drop_table("app_users")
