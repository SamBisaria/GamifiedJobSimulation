from __future__ import annotations


def build_daily_status_window(
    trace_detail: str,
    day: int,
    current_snapshot: dict[str, object],
    previous_snapshot: dict[str, object],
    all_skills: list[str],
) -> str:
    if trace_detail == "full":
        return build_daily_status_window_full(day, current_snapshot, previous_snapshot, all_skills)
    return build_daily_status_window_concise(day, current_snapshot, previous_snapshot, all_skills)


def build_daily_status_window_full(
    day: int,
    current_snapshot: dict[str, object],
    previous_snapshot: dict[str, object],
    all_skills: list[str],
) -> str:
    dynamic = current_snapshot["dynamic"]
    prev_dynamic = previous_snapshot["dynamic"]
    fixed = current_snapshot["fixed"]
    skills = current_snapshot["skills"]
    prev_skills = previous_snapshot["skills"]

    lines = [
        f"[User: {current_snapshot['user_id']} | Day: {day:03d}]",
        (
            f"Status: {dynamic['status']} "
            f"({'changed' if dynamic['status'] != prev_dynamic['status'] else 'no change'})"
        ),
        (
            f"Company: {dynamic['company']} "
            f"({'changed' if dynamic['company'] != prev_dynamic['company'] else 'no change'})"
        ),
        (
            f"Strategy: {dynamic['strategy']} "
            f"({'changed' if dynamic['strategy'] != prev_dynamic['strategy'] else 'no change'})"
        ),
        f"Wealth: ${float(dynamic['wealth']):.2f} ({float(dynamic['wealth']) - float(prev_dynamic['wealth']):+,.2f})",
        f"Premium: {float(dynamic['premium']):.2f} ({float(dynamic['premium']) - float(prev_dynamic['premium']):+,.2f})",
        f"Salary: ${float(dynamic['salary']):.2f} ({float(dynamic['salary']) - float(prev_dynamic['salary']):+,.2f})",
        f"Engagement: {float(dynamic['engagement']):.3f} ({float(dynamic['engagement']) - float(prev_dynamic['engagement']):+.3f})",
        f"Free Time: {float(dynamic['free_time']):.3f} ({float(dynamic['free_time']) - float(prev_dynamic['free_time']):+.3f})",
        f"Experience: {float(dynamic['experience']):.3f} ({float(dynamic['experience']) - float(prev_dynamic['experience']):+.3f})",
        f"Prep Bonus: {float(dynamic['prep']):.3f} ({float(dynamic['prep']) - float(prev_dynamic['prep']):+.3f})",
        (
            f"Recent Rejections: {int(dynamic['recent_rejections'])} "
            f"({int(dynamic['recent_rejections']) - int(prev_dynamic['recent_rejections']):+d})"
        ),
        (
            f"Unavailable Days: {int(dynamic['unavailable_days'])} "
            f"({int(dynamic['unavailable_days']) - int(prev_dynamic['unavailable_days']):+d})"
        ),
        (
            f"Actions Today: applies={int(dynamic['daily_applies'])} "
            f"messages={int(dynamic['daily_messages'])}"
        ),
        (
            "Fixed Stats: "
            f"charisma={float(fixed['charisma']):.3f}, "
            f"intelligence={float(fixed['intelligence']):.3f}, "
            f"base_exp={float(fixed['base_experience']):.3f}, "
            f"spend_willingness={float(fixed['spending_willingness']):.3f}, "
            f"nepotism={fixed['nepotism_company']}"
        ),
        "Skills:",
    ]

    for skill in all_skills:
        value = float(skills[skill])
        delta = value - float(prev_skills[skill])
        lines.append(f"  {skill}: {value:.3f} ({delta:+.3f})")

    return "\n".join(lines)


def build_daily_status_window_concise(
    day: int,
    current_snapshot: dict[str, object],
    previous_snapshot: dict[str, object],
    all_skills: list[str],
) -> str:
    dynamic = current_snapshot["dynamic"]
    prev_dynamic = previous_snapshot["dynamic"]
    skills = current_snapshot["skills"]
    prev_skills = previous_snapshot["skills"]

    lines = [
        f"[User: {current_snapshot['user_id']} | Day: {day:03d} | Trace: concise]",
        f"Status: {dynamic['status']} ({'changed' if dynamic['status'] != prev_dynamic['status'] else 'no change'})",
        f"Company/Job: {dynamic['company']} | Salary: ${float(dynamic['salary']):.2f}",
    ]

    dynamic_fields = [
        ("strategy", "Strategy", "text"),
        ("wealth", "Wealth", "currency"),
        ("premium", "Premium", "currency"),
        ("engagement", "Engagement", "float3"),
        ("free_time", "Free Time", "float3"),
        ("experience", "Experience", "float3"),
        ("prep", "Prep Bonus", "float3"),
        ("recent_rejections", "Recent Rejections", "int"),
        ("unavailable_days", "Unavailable Days", "int"),
        ("daily_applies", "Actions Today (applies)", "int"),
        ("daily_messages", "Actions Today (messages)", "int"),
        ("salary", "Salary", "currency"),
        ("company", "Company", "text"),
    ]

    changed_lines: list[str] = []
    for key, label, kind in dynamic_fields:
        current = dynamic[key]
        previous = prev_dynamic[key]
        if kind == "text":
            if str(current) != str(previous):
                changed_lines.append(f"{label}: {previous} -> {current}")
            continue

        if kind == "int":
            delta = int(current) - int(previous)
            if delta != 0:
                changed_lines.append(f"{label}: {int(current)} ({delta:+d})")
            continue

        delta = float(current) - float(previous)
        if abs(delta) < 0.0005:
            continue
        if kind == "currency":
            changed_lines.append(f"{label}: ${float(current):.2f} ({delta:+,.2f})")
        else:
            changed_lines.append(f"{label}: {float(current):.3f} ({delta:+.3f})")

    skill_changes: list[str] = []
    for skill in all_skills:
        delta = float(skills[skill]) - float(prev_skills[skill])
        if abs(delta) >= 0.005:
            skill_changes.append(f"{skill}: {float(skills[skill]):.3f} ({delta:+.3f})")

    if changed_lines:
        lines.append("Changed Stats:")
        for item in changed_lines:
            lines.append(f"  - {item}")
    else:
        lines.append("Changed Stats: none")

    if skill_changes:
        lines.append("Changed Skills:")
        for item in skill_changes:
            lines.append(f"  - {item}")
    else:
        lines.append("Changed Skills: none")

    return "\n".join(lines)


def build_trace_start_snapshot(
    trace_applicant_id: int,
    start_snapshot: dict[str, object] | None,
    all_skills: list[str],
) -> str:
    if start_snapshot is None:
        return ""

    start_dynamic = start_snapshot["dynamic"]
    start_fixed = start_snapshot["fixed"]
    start_skills = start_snapshot["skills"]

    lines = [
        "=== Trace Start Snapshot ===",
        f"[User: {trace_applicant_id}]",
        (
            f"status={start_dynamic['status']}, company={start_dynamic['company']}, "
            f"strategy={start_dynamic['strategy']}, salary=${float(start_dynamic['salary']):.2f}, "
            f"wealth=${float(start_dynamic['wealth']):.2f}, premium={float(start_dynamic['premium']):.2f}, "
            f"eng={float(start_dynamic['engagement']):.3f}, free_time={float(start_dynamic['free_time']):.3f}, "
            f"exp={float(start_dynamic['experience']):.3f}, prep={float(start_dynamic['prep']):.3f}, "
            f"rejections={int(start_dynamic['recent_rejections'])}, unavailable={int(start_dynamic['unavailable_days'])}"
        ),
        (
            "fixed: "
            f"charisma={float(start_fixed['charisma']):.3f}, "
            f"intelligence={float(start_fixed['intelligence']):.3f}, "
            f"base_exp={float(start_fixed['base_experience']):.3f}, "
            f"spend_willingness={float(start_fixed['spending_willingness']):.3f}, "
            f"nepotism={start_fixed['nepotism_company']}"
        ),
        "skills:",
    ]

    for skill in all_skills:
        lines.append(f"  {skill}: {float(start_skills[skill]):.3f}")

    return "\n".join(lines)


def build_trace_start_end_summary(
    trace_applicant_id: int,
    start_snapshot: dict[str, object] | None,
    end_snapshot: dict[str, object],
    all_skills: list[str],
) -> str:
    if start_snapshot is None:
        return ""

    start_dynamic = start_snapshot["dynamic"]
    end_dynamic = end_snapshot["dynamic"]
    start_fixed = start_snapshot["fixed"]
    end_skills = end_snapshot["skills"]
    start_skills = start_snapshot["skills"]

    lines = [
        "\n=== Trace Start vs End ===",
        f"[User: {trace_applicant_id}]",
        "Start:",
        (
            f"  status={start_dynamic['status']}, company={start_dynamic['company']}, "
            f"strategy={start_dynamic['strategy']}, salary=${float(start_dynamic['salary']):.2f}, "
            f"wealth=${float(start_dynamic['wealth']):.2f}, premium={float(start_dynamic['premium']):.2f}, "
            f"eng={float(start_dynamic['engagement']):.3f}, free_time={float(start_dynamic['free_time']):.3f}, "
            f"exp={float(start_dynamic['experience']):.3f}, prep={float(start_dynamic['prep']):.3f}, "
            f"rejections={int(start_dynamic['recent_rejections'])}, unavailable={int(start_dynamic['unavailable_days'])}"
        ),
        (
            "  fixed: "
            f"charisma={float(start_fixed['charisma']):.3f}, "
            f"intelligence={float(start_fixed['intelligence']):.3f}, "
            f"base_exp={float(start_fixed['base_experience']):.3f}, "
            f"spend_willingness={float(start_fixed['spending_willingness']):.3f}, "
            f"nepotism={start_fixed['nepotism_company']}"
        ),
        "End:",
        (
            f"  status={end_dynamic['status']}, company={end_dynamic['company']}, "
            f"strategy={end_dynamic['strategy']}, salary=${float(end_dynamic['salary']):.2f}, "
            f"wealth=${float(end_dynamic['wealth']):.2f} ({float(end_dynamic['wealth']) - float(start_dynamic['wealth']):+,.2f}), "
            f"premium={float(end_dynamic['premium']):.2f} ({float(end_dynamic['premium']) - float(start_dynamic['premium']):+,.2f}), "
            f"eng={float(end_dynamic['engagement']):.3f} ({float(end_dynamic['engagement']) - float(start_dynamic['engagement']):+.3f}), "
            f"free_time={float(end_dynamic['free_time']):.3f} ({float(end_dynamic['free_time']) - float(start_dynamic['free_time']):+.3f}), "
            f"exp={float(end_dynamic['experience']):.3f} ({float(end_dynamic['experience']) - float(start_dynamic['experience']):+.3f}), "
            f"prep={float(end_dynamic['prep']):.3f} ({float(end_dynamic['prep']) - float(start_dynamic['prep']):+.3f}), "
            f"rejections={int(end_dynamic['recent_rejections'])} ({int(end_dynamic['recent_rejections']) - int(start_dynamic['recent_rejections']):+d}), "
            f"unavailable={int(end_dynamic['unavailable_days'])} ({int(end_dynamic['unavailable_days']) - int(start_dynamic['unavailable_days']):+d})"
        ),
        "Skill Changes (start -> end):",
    ]

    for skill in all_skills:
        start_value = float(start_skills[skill])
        end_value = float(end_skills[skill])
        lines.append(f"  {skill}: {start_value:.3f} -> {end_value:.3f} ({end_value - start_value:+.3f})")

    return "\n".join(lines)
