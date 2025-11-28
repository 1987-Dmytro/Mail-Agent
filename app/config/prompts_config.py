"""Prompt version management and storage configuration.

This module provides functions for saving, loading, and managing prompt template versions
in the database. Supports prompt refinement, A/B testing, and rollback capabilities.

Key Functions:
- save_prompt_version: Save a new prompt template version to database
- load_prompt_version: Load a prompt template version (latest or specific version)
- activate_prompt_version: Mark a prompt version as active
- list_prompt_versions: List all versions for a template

Architecture: Enables iterative prompt engineering with version tracking.
"""

from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlmodel import Session, select, desc
import structlog

from app.models.prompt_versions import PromptVersion
from app.api.deps import engine


logger = structlog.get_logger(__name__)


def save_prompt_version(
    template_name: str,
    template_content: str,
    version: str,
    parameters: Optional[Dict[str, Any]] = None,
    set_active: bool = True,
) -> PromptVersion:
    """Save a new prompt template version to the database.

    If set_active=True, deactivates all other versions for this template_name
    and marks the new version as active.

    Args:
        template_name: Name of the prompt template (e.g., "response_generation")
        template_content: Full prompt template string with placeholders
        version: Semantic version string (e.g., "1.0.0", "1.1.0")
        parameters: Optional metadata (token_budget, constraints, etc.)
        set_active: Whether to mark this version as active (default: True)

    Returns:
        Created PromptVersion instance

    Raises:
        ValueError: If version already exists for this template_name
        Exception: If database operation fails

    Examples:
        >>> prompt = save_prompt_version(
        ...     template_name="response_generation",
        ...     template_content="You are an AI...",
        ...     version="1.0.0",
        ...     parameters={"token_budget": 6500}
        ... )
    """
    with Session(engine) as session:
        try:
            # Check if version already exists
            existing = session.exec(
                select(PromptVersion)
                .where(PromptVersion.template_name == template_name)
                .where(PromptVersion.version == version)
            ).first()

            if existing:
                raise ValueError(
                    f"Version {version} already exists for template {template_name}"
                )

            # Deactivate other versions if set_active=True
            if set_active:
                session.exec(
                    select(PromptVersion).where(
                        PromptVersion.template_name == template_name
                    )
                ).all()
                for pv in session.exec(
                    select(PromptVersion).where(
                        PromptVersion.template_name == template_name
                    )
                ):
                    pv.is_active = False

            # Create new version
            new_version = PromptVersion(
                template_name=template_name,
                template_content=template_content,
                version=version,
                parameters=parameters or {},
                is_active=set_active,
                created_at=datetime.now(timezone.utc),
            )

            session.add(new_version)
            session.commit()
            session.refresh(new_version)

            logger.info(
                "prompt_version_saved",
                template_name=template_name,
                version=version,
                is_active=set_active,
                parameters=parameters,
            )

            return new_version

        except Exception as e:
            session.rollback()
            logger.error(
                "prompt_version_save_failed",
                template_name=template_name,
                version=version,
                error=str(e),
            )
            raise


def load_prompt_version(
    template_name: str, version: Optional[str] = None
) -> Optional[PromptVersion]:
    """Load a prompt template version from the database.

    If version is None, loads the latest active version.
    If version is specified, loads that specific version.

    Args:
        template_name: Name of the prompt template
        version: Optional specific version to load (loads latest active if None)

    Returns:
        PromptVersion instance, or None if not found

    Examples:
        >>> # Load latest active version
        >>> prompt = load_prompt_version("response_generation")
        >>> # Load specific version
        >>> prompt = load_prompt_version("response_generation", "1.0.0")
    """
    with Session(engine) as session:
        try:
            if version:
                # Load specific version
                prompt = session.exec(
                    select(PromptVersion)
                    .where(PromptVersion.template_name == template_name)
                    .where(PromptVersion.version == version)
                ).first()

                if prompt:
                    logger.info(
                        "prompt_version_loaded",
                        template_name=template_name,
                        version=version,
                        is_active=prompt.is_active,
                    )
                else:
                    logger.warning(
                        "prompt_version_not_found",
                        template_name=template_name,
                        version=version,
                    )

            else:
                # Load latest active version
                prompt = session.exec(
                    select(PromptVersion)
                    .where(PromptVersion.template_name == template_name)
                    .where(PromptVersion.is_active == True)  # noqa: E712
                    .order_by(desc(PromptVersion.created_at))
                ).first()

                if prompt:
                    logger.info(
                        "prompt_version_loaded_active",
                        template_name=template_name,
                        version=prompt.version,
                        created_at=prompt.created_at,
                    )
                else:
                    logger.warning(
                        "no_active_prompt_version",
                        template_name=template_name,
                    )

            return prompt

        except Exception as e:
            logger.error(
                "prompt_version_load_failed",
                template_name=template_name,
                version=version,
                error=str(e),
            )
            return None


def activate_prompt_version(template_name: str, version: str) -> bool:
    """Mark a specific prompt version as active and deactivate others.

    Args:
        template_name: Name of the prompt template
        version: Version to activate

    Returns:
        True if successful, False otherwise

    Examples:
        >>> success = activate_prompt_version("response_generation", "1.1.0")
    """
    with Session(engine) as session:
        try:
            # Deactivate all versions for this template
            for pv in session.exec(
                select(PromptVersion).where(
                    PromptVersion.template_name == template_name
                )
            ):
                pv.is_active = False

            # Activate the specified version
            target_version = session.exec(
                select(PromptVersion)
                .where(PromptVersion.template_name == template_name)
                .where(PromptVersion.version == version)
            ).first()

            if not target_version:
                logger.error(
                    "prompt_version_activation_failed",
                    template_name=template_name,
                    version=version,
                    reason="version_not_found",
                )
                return False

            target_version.is_active = True
            session.commit()

            logger.info(
                "prompt_version_activated",
                template_name=template_name,
                version=version,
            )

            return True

        except Exception as e:
            session.rollback()
            logger.error(
                "prompt_version_activation_error",
                template_name=template_name,
                version=version,
                error=str(e),
            )
            return False


def list_prompt_versions(template_name: str) -> List[PromptVersion]:
    """List all versions for a prompt template, ordered by creation date (newest first).

    Args:
        template_name: Name of the prompt template

    Returns:
        List of PromptVersion instances

    Examples:
        >>> versions = list_prompt_versions("response_generation")
        >>> for v in versions:
        ...     print(f"{v.version} - Active: {v.is_active}")
    """
    with Session(engine) as session:
        try:
            versions = session.exec(
                select(PromptVersion)
                .where(PromptVersion.template_name == template_name)
                .order_by(desc(PromptVersion.created_at))
            ).all()

            logger.info(
                "prompt_versions_listed",
                template_name=template_name,
                count=len(versions),
            )

            return list(versions)

        except Exception as e:
            logger.error(
                "prompt_versions_list_failed",
                template_name=template_name,
                error=str(e),
            )
            return []
