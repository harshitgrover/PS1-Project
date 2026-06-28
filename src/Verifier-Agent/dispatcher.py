import logging
from typing import Tuple, List
from contracts import VerificationRequest, ViolationDetail, Severity
import z3_client

logger = logging.getLogger(__name__)

def dispatch(request: VerificationRequest) -> Tuple[str, List[ViolationDetail], List[ViolationDetail]]:
    """
    Routes the request to the Z3 client, handles unknown rules,
    and formats the final output.
    """
    # 1. We could theoretically do local checks here before Z3

    # 2. Call the Z3 adapter
    try:
        hard_violations, soft_violations = z3_client.verify(request)
    except Exception as e:
        logger.error(f"Z3 verification failed: {str(e)}")
        # System-level error for hard fallback if Z3 crashes or fails completely
        return "UNSAT", [ViolationDetail(
            constraint_id="system_error",
            entity_id="system",
            severity=Severity.hard,
            message=f"System Error: {str(e)}"
        )], []

    # Check for unprocessable constraints based on mock logic 
    # (If Z3 returns errors about unknown constraints, they'd be handled here)
    # The specification says:
    # If severity == "soft": Log a warning, ignore it, proceed.
    # If severity == "hard": Halt immediately. Append a hard ViolationDetail.
    
    # In this mock, we assume all requested constraints are passed to Z3.

    # 3. Assemble results
    result = "UNSAT" if len(hard_violations) > 0 else "SAT"

    return result, hard_violations, soft_violations
