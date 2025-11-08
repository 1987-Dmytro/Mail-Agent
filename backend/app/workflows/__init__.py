"""LangGraph workflows for email processing automation.

This module contains state machines for email classification, approval, and action execution.
"""

from app.workflows.states import EmailWorkflowState

__all__ = ["EmailWorkflowState"]
