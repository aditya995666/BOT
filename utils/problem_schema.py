class SystemProblem:
    def __init__(self, title, cause, severity, fix):
        self.title = title
        self.cause = cause
        self.severity = severity
        self.fix = fix

    def to_dict(self):
        return {
            "title": self.title,
            "cause": self.cause,
            "severity": self.severity,
            "fix": self.fix
        }
