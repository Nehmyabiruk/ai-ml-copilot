from sqlalchemy.orm import Session

from app.models.project import Project
from app.schemas.project import ProjectCreate


def create_project(
    db: Session,
    project_data: ProjectCreate,
) -> Project:

    project = Project(
        name=project_data.name,
        description=project_data.description,
        repository_url=project_data.repository_url,
    )

    db.add(project)
    db.commit()
    db.refresh(project)

    return project