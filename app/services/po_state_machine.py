"""
Purchase Order State Machine

This module is the SINGLE SOURCE OF TRUTH for all PO status transitions.
All status changes must go through this module.

Benefits:
- Clear visualization of PO lifecycle
- Centralized validation
- Easy to modify workflow
- Prevents invalid state transitions
"""

from typing import Optional, List, Dict
from datetime import datetime, timezone
from fastapi import HTTPException


# =============================================================================
# STATUS DEFINITIONS (Single Source of Truth)
# =============================================================================

class POStatus:
    """PO Status constants - use these instead of strings."""
    DRAFT = "DRAFT"
    PENDING_APPROVAL = "PENDING_APPROVAL"
    APPROVED = "APPROVED"
    SENT_TO_VENDOR = "SENT_TO_VENDOR"
    ACKNOWLEDGED = "ACKNOWLEDGED"
    PARTIALLY_RECEIVED = "PARTIALLY_RECEIVED"
    FULLY_RECEIVED = "FULLY_RECEIVED"
    CLOSED = "CLOSED"
    CANCELLED = "CANCELLED"

    @classmethod
    def all(cls) -> List[str]:
        return [
            cls.DRAFT, cls.PENDING_APPROVAL, cls.APPROVED,
            cls.SENT_TO_VENDOR, cls.ACKNOWLEDGED,
            cls.PARTIALLY_RECEIVED, cls.FULLY_RECEIVED,
            cls.CLOSED, cls.CANCELLED
        ]


# =============================================================================
# TRANSITION RULES
# =============================================================================

# Define what transitions are allowed from each status
# Format: current_status -> [list of allowed next statuses]
PO_TRANSITIONS: Dict[str, List[str]] = {
    POStatus.DRAFT: [
        POStatus.PENDING_APPROVAL,  # Submit for approval
        POStatus.APPROVED,          # Direct approve (super admin)
        POStatus.CANCELLED,         # Cancel draft
    ],
    POStatus.PENDING_APPROVAL: [
        POStatus.APPROVED,          # Approve
        POStatus.DRAFT,             # Reject/send back to draft
        POStatus.CANCELLED,         # Cancel
    ],
    POStatus.APPROVED: [
        POStatus.SENT_TO_VENDOR,    # Send PO to vendor
        POStatus.CANCELLED,         # Cancel before sending
    ],
    POStatus.SENT_TO_VENDOR: [
        POStatus.ACKNOWLEDGED,      # Vendor acknowledged
        POStatus.PARTIALLY_RECEIVED,# Start receiving goods
        POStatus.FULLY_RECEIVED,    # All goods received at once
        POStatus.CANCELLED,         # Cancel (with vendor agreement)
    ],
    POStatus.ACKNOWLEDGED: [
        POStatus.PARTIALLY_RECEIVED,# Start receiving goods
        POStatus.FULLY_RECEIVED,    # All goods received at once
        POStatus.CANCELLED,         # Cancel
    ],
    POStatus.PARTIALLY_RECEIVED: [
        POStatus.PARTIALLY_RECEIVED,# Receive more goods
        POStatus.FULLY_RECEIVED,    # All remaining goods received
        POStatus.CLOSED,            # Close with partial receipt
    ],
    POStatus.FULLY_RECEIVED: [
        POStatus.CLOSED,            # Close PO
    ],
    POStatus.CLOSED: [],            # Terminal state - no transitions
    POStatus.CANCELLED: [],         # Terminal state - no transitions
}

# Human-readable action names for each transition
TRANSITION_ACTIONS: Dict[tuple, str] = {
    (POStatus.DRAFT, POStatus.PENDING_APPROVAL): "Submit for Approval",
    (POStatus.DRAFT, POStatus.APPROVED): "Direct Approve",
    (POStatus.DRAFT, POStatus.CANCELLED): "Cancel",
    (POStatus.PENDING_APPROVAL, POStatus.APPROVED): "Approve",
    (POStatus.PENDING_APPROVAL, POStatus.DRAFT): "Reject",
    (POStatus.PENDING_APPROVAL, POStatus.CANCELLED): "Cancel",
    (POStatus.APPROVED, POStatus.SENT_TO_VENDOR): "Send to Vendor",
    (POStatus.APPROVED, POStatus.CANCELLED): "Cancel",
    (POStatus.SENT_TO_VENDOR, POStatus.ACKNOWLEDGED): "Vendor Acknowledged",
    (POStatus.SENT_TO_VENDOR, POStatus.PARTIALLY_RECEIVED): "Receive Goods",
    (POStatus.SENT_TO_VENDOR, POStatus.FULLY_RECEIVED): "Receive All Goods",
    (POStatus.ACKNOWLEDGED, POStatus.PARTIALLY_RECEIVED): "Receive Goods",
    (POStatus.ACKNOWLEDGED, POStatus.FULLY_RECEIVED): "Receive All Goods",
    (POStatus.PARTIALLY_RECEIVED, POStatus.FULLY_RECEIVED): "Receive Remaining",
    (POStatus.PARTIALLY_RECEIVED, POStatus.CLOSED): "Close PO",
    (POStatus.FULLY_RECEIVED, POStatus.CLOSED): "Close PO",
}


# =============================================================================
# HELPER FUNCTIONS
# =============================================================================

def can_transition(current_status: str, new_status: str) -> bool:
    """Check if a transition is allowed."""
    allowed = PO_TRANSITIONS.get(current_status, [])
    return new_status in allowed


def get_allowed_transitions(current_status: str) -> List[str]:
    """Get list of statuses that can be transitioned to from current status."""
    return PO_TRANSITIONS.get(current_status, [])


def get_transition_action(current_status: str, new_status: str) -> str:
    """Get human-readable action name for a transition."""
    return TRANSITION_ACTIONS.get((current_status, new_status), f"{current_status} -> {new_status}")


def validate_transition(current_status: str, new_status: str) -> None:
    """
    Validate a status transition. Raises HTTPException if invalid.

    Use this in endpoints before changing status.
    """
    if current_status == new_status:
        return  # No change, always allowed

    if not can_transition(current_status, new_status):
        allowed = get_allowed_transitions(current_status)
        if not allowed:
            raise HTTPException(
                status_code=400,
                detail=f"PO in '{current_status}' status cannot be modified. This is a terminal state."
            )
        raise HTTPException(
            status_code=400,
            detail=f"Cannot change PO from '{current_status}' to '{new_status}'. "
                   f"Allowed transitions: {', '.join(allowed)}"
        )


# =============================================================================
# STATUS CHECK HELPERS (for common operations)
# =============================================================================

def can_submit(status: str) -> bool:
    """Can this PO be submitted for approval?"""
    return status == POStatus.DRAFT


def can_approve(status: str) -> bool:
    """Can this PO be approved?"""
    return status in [POStatus.DRAFT, POStatus.PENDING_APPROVAL]


def can_reject(status: str) -> bool:
    """Can this PO be rejected?"""
    return status == POStatus.PENDING_APPROVAL


def can_send_to_vendor(status: str) -> bool:
    """Can this PO be sent to vendor?"""
    return status == POStatus.APPROVED


def can_receive_goods(status: str) -> bool:
    """Can goods be received against this PO?"""
    return status in [POStatus.SENT_TO_VENDOR, POStatus.ACKNOWLEDGED, POStatus.PARTIALLY_RECEIVED]


def can_edit(status: str) -> bool:
    """Can this PO be edited?"""
    return status == POStatus.DRAFT


def can_delete(status: str) -> bool:
    """Can this PO be deleted?"""
    return status == POStatus.DRAFT


def can_cancel(status: str) -> bool:
    """Can this PO be cancelled?"""
    return status not in [POStatus.CLOSED, POStatus.CANCELLED, POStatus.FULLY_RECEIVED]


def is_terminal(status: str) -> bool:
    """Is this a terminal (final) state?"""
    return status in [POStatus.CLOSED, POStatus.CANCELLED]


def is_active(status: str) -> bool:
    """Is this PO still active (not closed/cancelled)?"""
    return not is_terminal(status)


# =============================================================================
# TRANSITION EXECUTOR
# =============================================================================

def transition_po(po, new_status: str, user_id=None) -> None:
    """
    Transition a PO to a new status.

    This function:
    1. Validates the transition is allowed
    2. Updates the status
    3. Sets audit fields based on the transition

    Args:
        po: PurchaseOrder model instance
        new_status: Target status
        user_id: ID of user performing the action (for audit)

    Raises:
        HTTPException: If transition is not allowed
    """
    current_status = po.status

    # Validate transition
    validate_transition(current_status, new_status)

    # Update status
    po.status = new_status

    # Set audit fields based on transition
    now = datetime.now(timezone.utc)

    if new_status == POStatus.APPROVED:
        po.approved_by = user_id
        po.approved_at = now

    elif new_status == POStatus.SENT_TO_VENDOR:
        po.sent_to_vendor_at = now

    elif new_status == POStatus.ACKNOWLEDGED:
        po.vendor_acknowledged_at = now

    elif new_status == POStatus.CLOSED:
        po.closed_at = now


# =============================================================================
# VISUALIZATION (for debugging/documentation)
# =============================================================================

def print_state_diagram():
    """Print a text representation of the state machine."""
    print("\n=== PO State Machine ===\n")
    for status in POStatus.all():
        transitions = get_allowed_transitions(status)
        if transitions:
            print(f"{status}:")
            for t in transitions:
                action = get_transition_action(status, t)
                print(f"  -> {t} ({action})")
        else:
            print(f"{status}: [TERMINAL STATE]")
        print()


if __name__ == "__main__":
    # Run this file directly to see the state diagram
    print_state_diagram()
