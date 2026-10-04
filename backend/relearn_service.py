
# ==========================================
# RE:LEARN BACKEND SERVICE
# ==========================================

def relearn_service(
    question_id,
    student_working,
    error_type=None,
    error_step=None,
    reassessment_result=None
):
    """
    Main Re:Learn adaptive learning service.

    Pipeline:
    Student Attempt
        -> Diagnosis
        -> Intervention
        -> Reassessment
        -> Transfer / Additional Support
    """

    diagnosis = diagnose_question_attempt(
        question_id=question_id,
        student_working=student_working,
        error_type=error_type,
        error_step=error_step
    )

    if diagnosis["message"] != "Misconception diagnosed":
        return {
            "status": "Diagnosis incomplete",
            "question_id": question_id,
            "diagnosis": diagnosis,
            "intervention": None,
            "adaptive_path": None
        }

    misconception_id = diagnosis["misconception_id"]

    intervention = get_intervention_safe(
        misconception_id
    )

    adaptive_path = get_adaptive_path_safe(
        misconception_id,
        reassessment_result
    )

    return {
        "status": "Adaptive learning response generated",
        "question_id": question_id,
        "diagnosis": diagnosis,
        "intervention": intervention,
        "adaptive_path": adaptive_path
    }
