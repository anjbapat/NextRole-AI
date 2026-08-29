from nextrole.models import FitAnalysis, InterviewPrep, JobAnalysis


def build_fallback_interview(job: JobAnalysis, fit: FitAnalysis) -> InterviewPrep:
    gaps = fit.weak_areas[:4]
    strengths = fit.strong_matches[:3]
    questions = []
    for topic in gaps:
        questions.append(
            {
                "question": f"How would you approach a project that requires {topic}?",
                "category": "technical",
                "difficulty": "medium",
                "why_asked": f"The job lists {topic}, but the resume has limited or no direct evidence.",
                "preparation_hint": f"Learn the core concepts of {topic}, build a small example, and explain how your existing experience transfers.",
                "focus": topic,
            }
        )
    for topic in strengths:
        questions.append(
            {
                "question": f"Describe a project where you used {topic}. What tradeoffs and results mattered?",
                "category": "resume",
                "difficulty": "medium",
                "why_asked": f"{topic} is a documented match for this role.",
                "preparation_hint": "Prepare a concise STAR response using only resume-supported facts.",
                "focus": topic,
            }
        )
    if not questions:
        questions.append(
            {
                "question": f"How would your experience help you succeed as {job.title}?",
                "category": "behavioral",
                "difficulty": "easy",
                "why_asked": "This connects the candidate's background to the target role.",
                "preparation_hint": "Choose two supported examples and explain their relevance.",
                "focus": job.title,
            }
        )
    knowledge = [
        {
            "topic": x,
            "priority": "HIGH" if i < 2 else "MEDIUM",
            "action": f"Review {x}, complete one hands-on exercise, and prepare a two-minute explanation.",
        }
        for i, x in enumerate(gaps)
    ]
    plan = [
        f"Study {x}: fundamentals, one practical example, and one likely interview answer."
        for x in gaps
    ]
    if not plan:
        plan = ["Review the strongest resume examples and prepare concise STAR responses."]
    return InterviewPrep(likely_questions=questions[:6], knowledge_gaps=knowledge, study_plan=plan)
