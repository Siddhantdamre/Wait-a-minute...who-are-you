from statistics import mean


def _score_summary(records):
    total = len(records)
    committed = [record for record in records if record["parsed_action"] == "COMMIT"]
    parse_errors = [record for record in records if record["parse_error"]]
    wrong_commits = [
        record
        for record in committed
        if record["gold_action"] != "COMMIT"
    ]
    silent_failures = [
        record
        for record in records
        if record["parsed_action"] == "COMMIT"
        and record["gold_action"] == "ABSTAIN"
        and (record["parsed_confidence"] or 0.0) > 0.8
    ]

    return {
        "n_tasks": total,
        "final_accuracy": round(mean(record["correct"] for record in records), 4) if records else 0.0,
        "commit_accuracy": round(mean(record["correct"] for record in committed), 4) if committed else 0.0,
        "abstain_rate": round(mean(record["parsed_action"] == "ABSTAIN" for record in records), 4) if records else 0.0,
        "bluff_rate": round(mean(record["parsed_action"] == "COMMIT" and record["gold_action"] in {"ABSTAIN", "ESCALATE"} for record in records), 4) if records else 0.0,
        "escalation_rate": round(mean(record["parsed_action"] == "ESCALATE" for record in records), 4) if records else 0.0,
        "silent_failure_rate": round(len(silent_failures) / total, 4) if total else 0.0,
        "average_confidence": round(mean(record["parsed_confidence"] or 0.0 for record in records), 4) if records else 0.0,
        "average_confidence_on_wrong_commit": round(
            mean(record["parsed_confidence"] or 0.0 for record in wrong_commits), 4
        ) if wrong_commits else 0.0,
        "parse_error_rate": round(len(parse_errors) / total, 4) if total else 0.0,
    }


def score_records(records):
    summary = _score_summary(records)

    by_task_type = {}
    for task_type in sorted({record["task_type"] for record in records}):
        typed_records = [record for record in records if record["task_type"] == task_type]
        by_task_type[task_type] = _score_summary(typed_records)

    return {
        "summary": summary,
        "by_task_type": by_task_type,
    }
