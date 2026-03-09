from typing import Dict, Any


def explain_issue(issue: Dict[str, Any]) -> Dict[str, str]:
    tool = str(issue.get("tool", "")).lower()
    rule = str(issue.get("rule_id", ""))
    severity = str(issue.get("severity", "low"))

    # -----------------------------
    # Bandit (Security issues)
    # -----------------------------
    if tool == "bandit":

        if rule == "B602":
            return {
                "explanation": "Using subprocess with shell=True may allow command injection if user input is passed.",
                "fix": "Avoid shell=True and pass arguments as a list: subprocess.run(['cmd','arg']).",
                "risk": "Command injection vulnerability."
            }

        if rule == "B404":
            return {
                "explanation": "Importing subprocess is flagged because it is commonly used for command execution.",
                "fix": "Ensure commands are validated and avoid executing untrusted input.",
                "risk": "Potential remote command execution."
            }

        return {
            "explanation": "Security issue detected by Bandit.",
            "fix": "Review the code path and sanitize inputs.",
            "risk": "Security vulnerability."
        }

    # -----------------------------
    # Flake8 (Code quality)
    # -----------------------------
    if tool == "flake8":

        if rule == "E501":
            return {
                "explanation": "Line is too long which reduces readability.",
                "fix": "Split long statements into multiple lines.",
                "risk": "Maintainability issue."
            }

        if rule == "F821":
            return {
                "explanation": "Undefined variable used in the code.",
                "fix": "Define the variable or import the correct module.",
                "risk": "Runtime crash."
            }

        if rule == "F401":
            return {
                "explanation": "Unused import detected.",
                "fix": "Remove unused imports.",
                "risk": "Code clutter."
            }

        if rule == "W292":
            return {
                "explanation": "File missing newline at end.",
                "fix": "Add a newline at the end of the file.",
                "risk": "Style issue."
            }

        return {
            "explanation": "Code quality issue detected by Flake8.",
            "fix": "Follow Python style guidelines.",
            "risk": f"{severity} severity quality issue."
        }

    return {
        "explanation": "General issue detected.",
        "fix": "Review and correct the code.",
        "risk": "Unknown risk."
    }