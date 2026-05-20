"""FASE 28.3 — Workflow State Machine.

Defines the lifecycle of an agentic workflow:
  PLANNING → EVALUATED → AWAITING_APPROVAL → APPROVED → SIMULATING → DONE
                                                ↓           ↓           ↓
                                           REJECTED    EXECUTING   ROLLED_BACK
                                           EXPIRED         ↓
                                                       MUTATING
                                                      /        \
                                                  DONE        FAILED → ROLLED_BACK
"""

from __future__ import annotations

import time
import uuid
from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class WorkflowState(Enum):
    PLANNING = "planning"
    EVALUATED = "evaluated"
    GOVERNED = "governed"
    AWAITING_APPROVAL = "awaiting_approval"
    APPROVED = "approved"
    READY_FOR_EXECUTION = "ready_for_execution"
    EXECUTING = "executing"
    MUTATING = "mutating"
    EXECUTING_RESERVED = "executing_reserved"
    SIMULATING = "simulating"
    DONE = "done"
    ROLLBACK_RESERVED = "rollback_reserved"
    ROLLED_BACK = "rolled_back"
    CANCELLED = "cancelled"
    REJECTED = "rejected"
    EXPIRED = "expired"
    FAILED = "failed"


VALID_TRANSITIONS: dict[WorkflowState, set[WorkflowState]] = {
    WorkflowState.PLANNING: {WorkflowState.EVALUATED, WorkflowState.FAILED},
    WorkflowState.EVALUATED: {WorkflowState.GOVERNED, WorkflowState.AWAITING_APPROVAL, WorkflowState.SIMULATING, WorkflowState.FAILED},
    WorkflowState.GOVERNED: {WorkflowState.AWAITING_APPROVAL, WorkflowState.FAILED},
    WorkflowState.AWAITING_APPROVAL: {WorkflowState.APPROVED, WorkflowState.REJECTED, WorkflowState.EXPIRED},
    WorkflowState.APPROVED: {WorkflowState.READY_FOR_EXECUTION, WorkflowState.CANCELLED},
    WorkflowState.READY_FOR_EXECUTION: {WorkflowState.SIMULATING, WorkflowState.EXECUTING, WorkflowState.FAILED},
    WorkflowState.EXECUTING: {WorkflowState.MUTATING, WorkflowState.DONE, WorkflowState.FAILED},
    WorkflowState.MUTATING: {WorkflowState.DONE, WorkflowState.FAILED},
    WorkflowState.EXECUTING_RESERVED: set(),
    WorkflowState.SIMULATING: {WorkflowState.DONE, WorkflowState.ROLLBACK_RESERVED, WorkflowState.ROLLED_BACK, WorkflowState.FAILED, WorkflowState.EXECUTING},
    WorkflowState.DONE: {WorkflowState.ROLLED_BACK},
    WorkflowState.ROLLBACK_RESERVED: set(),
    WorkflowState.ROLLED_BACK: set(),
    WorkflowState.FAILED: {WorkflowState.ROLLED_BACK},
    WorkflowState.CANCELLED: set(),
    WorkflowState.REJECTED: set(),
    WorkflowState.EXPIRED: set(),
}


@dataclass
class AgenticEvent:
    event_id: str = field(default_factory=lambda: uuid.uuid4().hex[:8])
    event_type: str = ""
    plan_id: str = ""
    phase: str = ""
    timestamp: float = field(default_factory=time.time)
    detail: dict[str, Any] = field(default_factory=dict)

    def to_audit(self) -> dict:
        return {
            "timestamp": int(self.timestamp),
            "event_type": self.event_type,
            "payload": {
                "event_id": self.event_id,
                "plan_id": self.plan_id,
                "phase": self.phase,
                **self.detail,
            },
        }


@dataclass
class WorkflowTimeline:
    plan_id: str = ""
    events: list[AgenticEvent] = field(default_factory=list)
    created_at: float = field(default_factory=time.time)
    current_state: WorkflowState = WorkflowState.PLANNING

    def add_event(self, event_type: str, phase: str, detail: dict | None = None) -> AgenticEvent:
        ev = AgenticEvent(
            event_type=event_type,
            plan_id=self.plan_id,
            phase=phase,
            detail=detail or {},
        )
        self.events.append(ev)
        return ev

    def transition(self, new_state: WorkflowState) -> bool:
        allowed = VALID_TRANSITIONS.get(self.current_state, set())
        if new_state in allowed:
            self.current_state = new_state
            self.add_event("state_transition", new_state.value, {
                "from_state": self.current_state.value,
                "to_state": new_state.value,
            })
            return True
        return False

    def to_dict(self) -> dict:
        return {
            "plan_id": self.plan_id,
            "current_state": self.current_state.value,
            "created_at": self.created_at,
            "events": [
                {
                    "event_id": e.event_id,
                    "event_type": e.event_type,
                    "phase": e.phase,
                    "timestamp": e.timestamp,
                    "detail": e.detail,
                }
                for e in self.events
            ],
            "total_events": len(self.events),
        }
