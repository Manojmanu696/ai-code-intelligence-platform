from __future__ import annotations

from typing import Any, Dict


def _normalize_tool(value: Any) -> str:
    return str(value or "").strip().lower()


def _normalize_rule(value: Any) -> str:
    return str(value or "").strip().upper()


def _normalize_severity(value: Any) -> str:
    sev = str(value or "low").strip().lower()
    if sev in {"high", "medium", "low"}:
        return sev
    return "low"


def _security_severity_phrase(severity: str) -> str:
    if severity == "high":
        return "This is a high-risk security concern and should be fixed immediately."
    if severity == "medium":
        return "This is a medium-risk security concern and should be reviewed soon."
    return "This is a lower-severity security concern, but it should still be cleaned up."


def _quality_severity_phrase(severity: str) -> str:
    if severity == "high":
        return "This can seriously affect runtime stability or code correctness."
    if severity == "medium":
        return "This can affect maintainability, clarity, or reliability."
    return "This is mainly a readability or hygiene issue, but fixing it improves code quality."


def _bandit_rule_details(rule: str) -> Dict[str, str]:
    rules: Dict[str, Dict[str, str]] = {
        "B101": {
            "explanation": "The use of assert statements in production code is discouraged because Python can remove them when optimization flags are enabled.",
            "fix": "Do not rely on assert for security or runtime validation. Raise explicit exceptions or use normal conditional checks.",
            "risk": "Validation bypass or unexpected behavior in optimized execution.",
            "impact": "Important checks may silently disappear in production.",
        },
        "B102": {
            "explanation": "Using exec executes dynamically generated Python code, which is dangerous when inputs are not fully trusted.",
            "fix": "Avoid exec. Replace it with explicit logic, controlled dispatch tables, or safe parsing approaches.",
            "risk": "Arbitrary code execution.",
            "impact": "An attacker may execute unintended Python code.",
        },
        "B103": {
            "explanation": "Setting file or resource permissions too loosely can expose sensitive data or unsafe write access.",
            "fix": "Use the most restrictive permissions needed for the file or directory.",
            "risk": "Unauthorized access.",
            "impact": "Sensitive files may become readable or writable by unintended users.",
        },
        "B104": {
            "explanation": "Binding a service to all network interfaces can unintentionally expose it beyond the intended machine or network.",
            "fix": "Bind only to trusted interfaces when possible, such as localhost for local-only services.",
            "risk": "Unintended network exposure.",
            "impact": "A service may become reachable from untrusted networks.",
        },
        "B105": {
            "explanation": "A hardcoded password string was detected. Secrets should not be stored directly in source code.",
            "fix": "Move secrets to environment variables, secret managers, or secure configuration files that are excluded from version control.",
            "risk": "Credential exposure.",
            "impact": "Anyone with code access may obtain the secret.",
        },
        "B106": {
            "explanation": "A hardcoded password was detected in a function argument or similar code path.",
            "fix": "Pass secrets from secure runtime configuration instead of embedding them in code.",
            "risk": "Credential exposure.",
            "impact": "Secrets can leak through source control, logs, or code sharing.",
        },
        "B107": {
            "explanation": "A hardcoded password default was detected. Default secrets are unsafe because they are predictable and often reused.",
            "fix": "Require secrets to be provided securely at runtime and fail fast if they are missing.",
            "risk": "Predictable credentials.",
            "impact": "Attackers may guess or reuse default credentials.",
        },
        "B108": {
            "explanation": "Use of insecure temporary file or directory patterns can create race conditions or unsafe file access.",
            "fix": "Use Python's tempfile utilities safely and avoid constructing temporary paths manually.",
            "risk": "Insecure temporary file handling.",
            "impact": "Temporary files may be hijacked or overwritten.",
        },
        "B110": {
            "explanation": "A bare except with pass can hide security problems and make failures invisible.",
            "fix": "Catch only expected exceptions and log or handle them explicitly.",
            "risk": "Silent failure.",
            "impact": "Real problems may be hidden and remain unresolved.",
        },
        "B112": {
            "explanation": "A try/except/finally pattern may suppress useful exception details or hide critical failures.",
            "fix": "Preserve exceptions appropriately and avoid swallowing unexpected errors.",
            "risk": "Error masking.",
            "impact": "Security or runtime failures can become harder to detect.",
        },
        "B201": {
            "explanation": "Flask debug mode should not be enabled in production because it can reveal sensitive internals.",
            "fix": "Disable debug mode in production and control it using secure environment-based configuration.",
            "risk": "Sensitive information disclosure.",
            "impact": "Debug tooling may expose stack traces or internals.",
        },
        "B301": {
            "explanation": "Pickle and similar unsafe deserialization mechanisms can execute arbitrary code when loading untrusted data.",
            "fix": "Do not deserialize untrusted pickle data. Prefer safer formats such as JSON for external input.",
            "risk": "Arbitrary code execution through unsafe deserialization.",
            "impact": "Loading attacker-controlled data may execute code.",
        },
        "B302": {
            "explanation": "marshal is not safe for untrusted data and is not intended as a secure serialization format.",
            "fix": "Use safer, well-understood formats such as JSON for external input.",
            "risk": "Unsafe deserialization.",
            "impact": "Untrusted payloads may cause unsafe behavior or compatibility issues.",
        },
        "B303": {
            "explanation": "Weak cryptographic hashes such as MD5 or SHA1 are no longer considered secure for sensitive security use cases.",
            "fix": "Use stronger algorithms such as SHA-256 or SHA-512 unless a non-security checksum is explicitly intended.",
            "risk": "Weak cryptography.",
            "impact": "Hash collisions may weaken integrity or authentication assumptions.",
        },
        "B304": {
            "explanation": "Use of insecure ciphers or cryptographic primitives can weaken confidentiality protections.",
            "fix": "Prefer modern, well-reviewed cryptographic libraries and recommended cipher suites.",
            "risk": "Weak encryption.",
            "impact": "Encrypted data may be easier to break or misuse.",
        },
        "B305": {
            "explanation": "Using insecure block cipher modes may leak patterns or weaken encryption guarantees.",
            "fix": "Use secure authenticated encryption modes recommended by modern cryptography guidance.",
            "risk": "Insecure encryption mode.",
            "impact": "Data confidentiality or integrity may be reduced.",
        },
        "B306": {
            "explanation": "The use of mktemp-style APIs is insecure because generated names can be predicted or raced.",
            "fix": "Use secure tempfile APIs that create files atomically.",
            "risk": "Race condition and temporary file insecurity.",
            "impact": "Attackers may pre-create or intercept temporary files.",
        },
        "B307": {
            "explanation": "eval executes dynamic Python expressions and is unsafe with untrusted input.",
            "fix": "Replace eval with explicit parsing, mapping, or controlled logic.",
            "risk": "Arbitrary code execution.",
            "impact": "An attacker may execute injected Python expressions.",
        },
        "B308": {
            "explanation": "mark_safe and similar calls can disable escaping protections and lead to injection issues in templating contexts.",
            "fix": "Allow frameworks to escape content by default and only mark content safe when it is strictly trusted and sanitized.",
            "risk": "Injection or XSS exposure.",
            "impact": "Untrusted content may reach users without proper escaping.",
        },
        "B309": {
            "explanation": "HTTPS certificate validation issues can allow man-in-the-middle attacks.",
            "fix": "Always verify certificates and use modern HTTP/TLS libraries with secure defaults.",
            "risk": "TLS validation weakness.",
            "impact": "Network traffic may be intercepted or modified.",
        },
        "B310": {
            "explanation": "URL opening or fetching operations can be risky when targets are not validated. This may enable unsafe outbound requests or access to untrusted resources.",
            "fix": "Validate URLs, allowlist trusted domains, enforce HTTPS, and set timeouts before making external requests.",
            "risk": "Unsafe URL access or SSRF-style behavior.",
            "impact": "The application may access malicious or internal network resources.",
        },
        "B311": {
            "explanation": "The random module is not suitable for security-sensitive randomness such as tokens, passwords, or secrets.",
            "fix": "Use the secrets module or a cryptographically secure RNG for security-sensitive values.",
            "risk": "Predictable randomness.",
            "impact": "Attackers may guess generated secrets or tokens.",
        },
        "B312": {
            "explanation": "Use of telnetlib is insecure because Telnet does not protect credentials and traffic.",
            "fix": "Replace Telnet with secure protocols such as SSH.",
            "risk": "Cleartext network communication.",
            "impact": "Credentials and session data may be exposed in transit.",
        },
        "B313": {
            "explanation": "XML parsing can be dangerous when unsafe parsers allow entity expansion or related attacks.",
            "fix": "Use hardened XML parsers and disable unsafe features for untrusted XML.",
            "risk": "Unsafe XML parsing.",
            "impact": "Attackers may cause denial of service or data exposure through crafted XML.",
        },
        "B314": {
            "explanation": "Unsafe XML parser usage may expose the application to XXE-style issues or parser abuse.",
            "fix": "Use secure XML parser settings and avoid parsing untrusted XML with unsafe defaults.",
            "risk": "XML external entity or parser abuse risk.",
            "impact": "Sensitive files or network resources may be accessed indirectly.",
        },
        "B315": {
            "explanation": "Unsafe XML parsing patterns can create denial-of-service or data exposure risks.",
            "fix": "Use hardened parsing libraries and disable external entities for untrusted input.",
            "risk": "Unsafe XML handling.",
            "impact": "Malformed XML may crash or exploit the parser.",
        },
        "B316": {
            "explanation": "Unsafe XML handling can expose the application to parser-level attacks.",
            "fix": "Choose secure XML libraries and restrict dangerous XML features.",
            "risk": "Parser abuse.",
            "impact": "Attackers may exploit parsing behavior.",
        },
        "B317": {
            "explanation": "Unsafe XML parsing configuration was detected.",
            "fix": "Disable external entities and use hardened XML parsers for untrusted input.",
            "risk": "Unsafe XML parser behavior.",
            "impact": "The parser may expose data or consume excessive resources.",
        },
        "B318": {
            "explanation": "Unsafe XML parsing pattern detected.",
            "fix": "Use secure parsing libraries and avoid unsafe parser defaults.",
            "risk": "XML parsing weakness.",
            "impact": "Untrusted XML may trigger harmful parser behavior.",
        },
        "B319": {
            "explanation": "Unsafe XML parsing pattern detected.",
            "fix": "Ensure XML parsing is hardened before accepting untrusted data.",
            "risk": "XML-related security risk.",
            "impact": "The application may mishandle crafted XML input.",
        },
        "B320": {
            "explanation": "lxml or similar XML APIs may become unsafe depending on parser configuration and input trust level.",
            "fix": "Disable dangerous XML features and use secure parser settings for untrusted content.",
            "risk": "Unsafe XML processing.",
            "impact": "XML input may cause XXE-style or resource abuse issues.",
        },
        "B321": {
            "explanation": "FTP is insecure because it transfers data and credentials without strong protection.",
            "fix": "Use secure alternatives such as SFTP, FTPS, or HTTPS-based transfer methods.",
            "risk": "Insecure network transport.",
            "impact": "Credentials and transferred data may be exposed.",
        },
        "B323": {
            "explanation": "Use of insecure hashing or digest patterns was detected.",
            "fix": "Use a stronger cryptographic primitive appropriate for the security context.",
            "risk": "Weak integrity protection.",
            "impact": "Attackers may exploit weak hashing behavior.",
        },
        "B324": {
            "explanation": "Use of weak hash functions through hashlib was detected.",
            "fix": "Prefer SHA-256 or stronger algorithms for security-sensitive use cases.",
            "risk": "Weak cryptographic hash.",
            "impact": "Hash-based protections may be weaker than expected.",
        },
        "B401": {
            "explanation": "Importing telnetlib is risky because Telnet is insecure and should generally be avoided.",
            "fix": "Replace Telnet-based communication with secure protocols such as SSH.",
            "risk": "Insecure protocol usage.",
            "impact": "Network traffic and credentials may be exposed.",
        },
        "B403": {
            "explanation": "Importing pickle-related functionality is risky when untrusted data may be loaded.",
            "fix": "Avoid unsafe deserialization for external input and prefer safer data formats.",
            "risk": "Unsafe deserialization.",
            "impact": "Attacker-controlled payloads may execute code.",
        },
        "B404": {
            "explanation": "The subprocess module itself is not always unsafe, but it is commonly associated with command execution risks.",
            "fix": "Review every subprocess call carefully, avoid shell=True when possible, and never pass untrusted data directly into commands.",
            "risk": "Potential command execution misuse.",
            "impact": "Unsafe command execution can lead to injection or misuse.",
        },
        "B405": {
            "explanation": "Importing XML parsing modules can be risky when they are later used with untrusted input.",
            "fix": "Use secure XML handling patterns and hardened parser settings.",
            "risk": "Potential unsafe XML usage.",
            "impact": "Later parser usage may introduce XXE-style or parser abuse issues.",
        },
        "B406": {
            "explanation": "Unsafe XML parser usage may expose the application to attacks if input is untrusted.",
            "fix": "Use safe XML libraries or secure parser configuration.",
            "risk": "Unsafe XML handling.",
            "impact": "Parsing attacker input may expose data or degrade availability.",
        },
        "B407": {
            "explanation": "Unsafe XML parser usage may create security risk depending on input source and parser configuration.",
            "fix": "Disable dangerous features and validate the trust boundary for XML input.",
            "risk": "XML parser risk.",
            "impact": "XML-based attacks may become possible.",
        },
        "B408": {
            "explanation": "Unsafe XML mini-dom style parsing was detected.",
            "fix": "Use hardened parsers and secure XML settings for untrusted input.",
            "risk": "Unsafe XML parsing.",
            "impact": "The parser may expose the application to crafted XML attacks.",
        },
        "B409": {
            "explanation": "Unsafe XML parsing pattern was detected.",
            "fix": "Use secure XML libraries and disable external entities or unsafe parser features.",
            "risk": "XML parsing weakness.",
            "impact": "Malicious XML may affect confidentiality or availability.",
        },
        "B410": {
            "explanation": "Importing lxml or related XML APIs may become unsafe depending on configuration.",
            "fix": "Only use hardened XML parser settings for untrusted XML input.",
            "risk": "Potential XML security issue.",
            "impact": "Parser misuse may lead to exposure or denial of service.",
        },
        "B411": {
            "explanation": "Using xmlrpc or related modules may be risky depending on how input and network boundaries are handled.",
            "fix": "Validate inputs carefully and prefer secure, modern interfaces where possible.",
            "risk": "RPC-related exposure.",
            "impact": "Poorly controlled RPC endpoints may expand attack surface.",
        },
        "B412": {
            "explanation": "Importing asyncore or similar network server modules can expand network exposure if used unsafely.",
            "fix": "Ensure network services bind safely and validate untrusted input strictly.",
            "risk": "Network exposure.",
            "impact": "Improperly exposed services may be reachable by attackers.",
        },
        "B413": {
            "explanation": "Importing pycrypto or similar outdated crypto libraries may create maintenance or security concerns.",
            "fix": "Use modern, actively maintained cryptography libraries.",
            "risk": "Outdated cryptography dependency.",
            "impact": "The project may rely on insecure or unsupported crypto code.",
        },
        "B501": {
            "explanation": "Disabling SSL/TLS certificate verification weakens transport security and enables interception attacks.",
            "fix": "Always verify certificates unless there is a very controlled non-production need.",
            "risk": "Man-in-the-middle vulnerability.",
            "impact": "Attackers may impersonate remote services.",
        },
        "B602": {
            "explanation": "Using subprocess with shell=True can allow command injection if any part of the command is influenced by input.",
            "fix": "Avoid shell=True. Pass command arguments as a list and validate any dynamic values with strict allowlists.",
            "risk": "Command injection vulnerability.",
            "impact": "An attacker may execute arbitrary shell commands.",
        },
        "B603": {
            "explanation": "Even without shell=True, subprocess calls are risky when arguments are assembled from untrusted data.",
            "fix": "Avoid string concatenation for command building and validate every dynamic argument before execution.",
            "risk": "Unsafe process execution.",
            "impact": "Untrusted input may still trigger unintended command behavior.",
        },
        "B604": {
            "explanation": "Any other process-spawning pattern that involves shell execution can create injection risk.",
            "fix": "Prefer direct argument lists and avoid shell interpretation whenever possible.",
            "risk": "Command injection risk.",
            "impact": "Shell parsing may execute attacker-controlled input.",
        },
        "B605": {
            "explanation": "Starting a process through a shell expands injection risk because shell metacharacters may be interpreted.",
            "fix": "Call executables directly with argument lists instead of shell-based command strings.",
            "risk": "Shell injection.",
            "impact": "User-controlled input may alter command behavior.",
        },
        "B606": {
            "explanation": "Starting a process with unsafe executable handling may create security or reliability issues.",
            "fix": "Use explicit executable paths and avoid untrusted command construction.",
            "risk": "Unsafe process invocation.",
            "impact": "The wrong executable or unsafe command may run.",
        },
        "B607": {
            "explanation": "Launching a process with a partial path may rely on the environment PATH and execute unintended binaries.",
            "fix": "Use full executable paths for security-sensitive command execution.",
            "risk": "Path hijacking risk.",
            "impact": "A malicious executable earlier in PATH may be run.",
        },
        "B608": {
            "explanation": "Building SQL queries through string formatting can lead to SQL injection.",
            "fix": "Use parameterized queries or ORM query binding instead of manual string interpolation.",
            "risk": "SQL injection.",
            "impact": "Attackers may read, modify, or destroy database data.",
        },
        "B609": {
            "explanation": "Wildcard injection in Linux commands may expand unexpectedly and operate on unintended files.",
            "fix": "Avoid shell wildcard expansion on untrusted or dynamic input.",
            "risk": "Command misuse.",
            "impact": "Commands may affect more files or paths than intended.",
        },
        "B610": {
            "explanation": "Use of Django's extra() or similar raw query features can create SQL injection risk when not handled carefully.",
            "fix": "Prefer ORM-safe query methods and parameter binding.",
            "risk": "SQL injection risk.",
            "impact": "Untrusted input may alter database queries.",
        },
        "B611": {
            "explanation": "Calling raw SQL execution paths directly can become unsafe when inputs are not parameterized.",
            "fix": "Use parameter binding and avoid dynamically concatenated SQL.",
            "risk": "Database injection risk.",
            "impact": "Attackers may manipulate database queries.",
        },
    }
    return rules.get(rule, {})


def _flake8_rule_details(rule: str) -> Dict[str, str]:
    rules: Dict[str, Dict[str, str]] = {
        "E111": {
            "explanation": "Indentation is not a multiple of the expected width, which harms readability and may indicate structural mistakes.",
            "fix": "Use consistent indentation throughout the file, typically 4 spaces in Python.",
            "risk": "Formatting and possible structural confusion.",
            "impact": "Code may become harder to read or maintain.",
        },
        "E112": {
            "explanation": "An expected indentation block is missing.",
            "fix": "Indent the block correctly after statements such as if, for, while, def, or class.",
            "risk": "Syntax or structure issue.",
            "impact": "Python may reject or misinterpret the code structure.",
        },
        "E113": {
            "explanation": "Unexpected indentation was found in the file.",
            "fix": "Remove the extra indentation and align the block properly.",
            "risk": "Code structure issue.",
            "impact": "The file may be misleading or syntactically invalid.",
        },
        "E201": {
            "explanation": "Whitespace was found immediately after an opening bracket, which violates common Python style conventions.",
            "fix": "Remove the extra space after the opening bracket.",
            "risk": "Style inconsistency.",
            "impact": "Code readability is reduced.",
        },
        "E202": {
            "explanation": "Whitespace was found before a closing bracket, which reduces formatting consistency.",
            "fix": "Remove the extra space before the closing bracket.",
            "risk": "Style inconsistency.",
            "impact": "Formatting becomes uneven and harder to scan.",
        },
        "E225": {
            "explanation": "Missing whitespace around an operator reduces readability and makes expressions harder to scan.",
            "fix": "Add spaces around operators according to PEP 8 guidance.",
            "risk": "Readability issue.",
            "impact": "The expression becomes harder to understand quickly.",
        },
        "E231": {
            "explanation": "Missing whitespace after a comma, semicolon, or colon reduces readability.",
            "fix": "Add the expected whitespace after punctuation.",
            "risk": "Style issue.",
            "impact": "Code becomes less consistent and harder to read.",
        },
        "E261": {
            "explanation": "Inline comments should be separated from code by at least two spaces for readability.",
            "fix": "Add enough space before the inline comment.",
            "risk": "Style issue.",
            "impact": "Comments become harder to distinguish from code.",
        },
        "E262": {
            "explanation": "Inline comment formatting is inconsistent with standard Python style.",
            "fix": "Format the comment cleanly and keep spacing consistent.",
            "risk": "Comment readability issue.",
            "impact": "Documentation within the code becomes less clear.",
        },
        "E265": {
            "explanation": "Block comments should start with # followed by a space for consistent readability.",
            "fix": "Add a space after the hash in block comments.",
            "risk": "Comment style issue.",
            "impact": "Comments become less readable and less consistent.",
        },
        "E266": {
            "explanation": "Too many leading # characters were used in a block comment.",
            "fix": "Use a single # for a normal comment unless a specific convention requires otherwise.",
            "risk": "Comment formatting issue.",
            "impact": "Comments look noisy and inconsistent.",
        },
        "E302": {
            "explanation": "Top-level function and class definitions should usually be surrounded by two blank lines.",
            "fix": "Insert the required blank lines around top-level definitions.",
            "risk": "PEP 8 spacing issue.",
            "impact": "File structure becomes harder to scan visually.",
        },
        "E305": {
            "explanation": "Expected blank lines after a class or function definition were not found.",
            "fix": "Add the required blank lines to separate logical sections clearly.",
            "risk": "PEP 8 spacing issue.",
            "impact": "Definitions may blend into surrounding code.",
        },
        "E401": {
            "explanation": "Multiple imports were placed on one line, which reduces clarity and makes diffs less clean.",
            "fix": "Split imports into one import per line where appropriate.",
            "risk": "Maintainability issue.",
            "impact": "Imports become harder to read and manage.",
        },
        "E402": {
            "explanation": "A module-level import was not placed at the top of the file.",
            "fix": "Move imports to the top unless there is a documented reason to keep them local.",
            "risk": "Style and import-order issue.",
            "impact": "Execution order becomes less predictable and style consistency drops.",
        },
        "E501": {
            "explanation": "The line exceeds the configured maximum length, which reduces readability and can make maintenance harder.",
            "fix": "Wrap the statement using parentheses, split long strings, or refactor the expression into smaller parts.",
            "risk": "Readability and maintainability issue.",
            "impact": "Long lines are harder to review and edit safely.",
        },
        "E701": {
            "explanation": "Multiple statements were placed on one line after a colon, which reduces clarity.",
            "fix": "Split the statements across separate lines and use normal Python block structure.",
            "risk": "Readability and maintainability issue.",
            "impact": "Control flow becomes harder to understand.",
        },
        "E702": {
            "explanation": "Multiple statements were written on one line separated by semicolons.",
            "fix": "Move each statement onto its own line.",
            "risk": "Readability issue.",
            "impact": "Debugging and reviewing become harder.",
        },
        "E703": {
            "explanation": "A trailing semicolon is unnecessary in Python and is considered style noise.",
            "fix": "Remove the semicolon.",
            "risk": "Style issue.",
            "impact": "The code becomes less idiomatic and slightly noisier.",
        },
        "E711": {
            "explanation": "Comparisons to None should use 'is' or 'is not' instead of equality operators.",
            "fix": "Replace == None with 'is None' and != None with 'is not None'.",
            "risk": "Correctness and style issue.",
            "impact": "The intent becomes clearer and more Pythonic.",
        },
        "E712": {
            "explanation": "Comparisons to True or False using equality reduce clarity.",
            "fix": "Use direct truthiness checks or 'is True'/'is False' only when truly needed.",
            "risk": "Readability issue.",
            "impact": "Boolean logic may look more confusing than necessary.",
        },
        "F401": {
            "explanation": "An imported name is not used anywhere in the file.",
            "fix": "Remove the unused import or use it intentionally if it is required.",
            "risk": "Code clutter.",
            "impact": "Unused imports make the code noisier and can mislead readers.",
        },
        "F402": {
            "explanation": "An import was shadowed by a loop variable or similar reassignment.",
            "fix": "Rename the variable or avoid reusing imported names.",
            "risk": "Name shadowing issue.",
            "impact": "The original imported object may become inaccessible or confusing.",
        },
        "F403": {
            "explanation": "Wildcard imports make it unclear which names are present in the module.",
            "fix": "Import only the specific names you need.",
            "risk": "Namespace pollution.",
            "impact": "The code becomes harder to understand and maintain.",
        },
        "F405": {
            "explanation": "A name may be undefined because wildcard imports make resolution unclear.",
            "fix": "Replace wildcard imports with explicit imports so the source of each name is clear.",
            "risk": "Potential undefined-name issue.",
            "impact": "The module may fail or become hard to reason about.",
        },
        "F541": {
            "explanation": "An f-string was used without any placeholders, so string interpolation is unnecessary.",
            "fix": "Convert it to a normal string unless interpolation is actually needed.",
            "risk": "Unnecessary complexity.",
            "impact": "The code is slightly noisier than needed.",
        },
        "F621": {
            "explanation": "A variable or name appears to be defined multiple times in an unpacking or similar context.",
            "fix": "Ensure each variable name is used appropriately and only where intended.",
            "risk": "Logic or correctness issue.",
            "impact": "Assignments may not behave as expected.",
        },
        "F622": {
            "explanation": "An attempt was made to export undefined names through __all__.",
            "fix": "Only export names that are actually defined in the module.",
            "risk": "Module export issue.",
            "impact": "Imports from the module may fail or confuse consumers.",
        },
        "F631": {
            "explanation": "A test or assertion contains suspicious tuple truthiness behavior.",
            "fix": "Review the expression and ensure the logic checks the intended condition.",
            "risk": "Logic issue.",
            "impact": "The code may behave differently than expected.",
        },
        "F632": {
            "explanation": "A comparison uses a literal or expression in a suspicious way that may indicate a bug.",
            "fix": "Review the comparison carefully and rewrite it to reflect the intended logic.",
            "risk": "Potential correctness issue.",
            "impact": "Conditions may always evaluate unexpectedly.",
        },
        "F704": {
            "explanation": "A yield statement appears outside a proper function context.",
            "fix": "Move the yield into a generator function or rewrite the logic appropriately.",
            "risk": "Syntax or structural issue.",
            "impact": "The file may not execute correctly.",
        },
        "F706": {
            "explanation": "A return statement appears outside a function or in an invalid context.",
            "fix": "Move the return into a valid function body.",
            "risk": "Syntax issue.",
            "impact": "Python will reject the file.",
        },
        "F707": {
            "explanation": "A default except block was not placed last.",
            "fix": "Move broad exception handlers to the end after specific exceptions.",
            "risk": "Exception handling issue.",
            "impact": "Specific exceptions may never be reached properly.",
        },
        "F722": {
            "explanation": "A type annotation comment appears invalid or cannot be parsed correctly.",
            "fix": "Fix the annotation syntax so it is valid Python typing syntax.",
            "risk": "Typing/comment syntax issue.",
            "impact": "Type tooling and readability may suffer.",
        },
        "F821": {
            "explanation": "A name was used before being defined or imported.",
            "fix": "Define the variable, correct the spelling, or import the missing name before use.",
            "risk": "Runtime crash.",
            "impact": "The code will fail with a NameError when executed.",
        },
        "F822": {
            "explanation": "An undefined name was referenced in an __all__ export.",
            "fix": "Only include names that are actually defined in the module.",
            "risk": "Export correctness issue.",
            "impact": "Module consumers may receive import-time errors or confusion.",
        },
        "F823": {
            "explanation": "A local variable may be referenced before assignment.",
            "fix": "Ensure the variable is assigned before every path where it is used.",
            "risk": "Runtime crash.",
            "impact": "The function may fail with an UnboundLocalError.",
        },
        "F831": {
            "explanation": "A duplicate argument name was found in a function definition.",
            "fix": "Rename the duplicate argument so each parameter name is unique.",
            "risk": "Syntax issue.",
            "impact": "Python will reject the function definition.",
        },
        "E999": {
            "explanation": "Python could not parse the file because of a syntax error.",
            "fix": "Review quotes, brackets, indentation, commas, and other syntax near the flagged location, then rescan.",
            "risk": "Syntax failure.",
            "impact": "The file cannot run until the syntax issue is fixed.",
        },
        "W191": {
            "explanation": "Tabs were used for indentation, which can lead to inconsistent formatting across editors.",
            "fix": "Replace tabs with spaces and keep indentation consistent.",
            "risk": "Formatting inconsistency.",
            "impact": "Indentation may render differently across tools.",
        },
        "W291": {
            "explanation": "Trailing whitespace was found at the end of a line.",
            "fix": "Remove trailing spaces from the line.",
            "risk": "Style issue.",
            "impact": "Whitespace noise makes diffs and formatting less clean.",
        },
        "W292": {
            "explanation": "The file does not end with a newline, which can create minor tool and diff issues.",
            "fix": "Add a newline at the end of the file.",
            "risk": "Style and tooling issue.",
            "impact": "Some tools and diffs behave less cleanly without a final newline.",
        },
        "W293": {
            "explanation": "Blank lines contain whitespace, which adds noise to the file.",
            "fix": "Remove whitespace from otherwise blank lines.",
            "risk": "Formatting issue.",
            "impact": "The file becomes noisier and less clean in diffs.",
        },
    }
    return rules.get(rule, {})


def explain_issue(issue: Dict[str, Any]) -> Dict[str, str]:
    tool = _normalize_tool(issue.get("tool"))
    rule = _normalize_rule(issue.get("rule_id"))
    severity = _normalize_severity(issue.get("severity"))
    message = str(issue.get("message", "")).strip()

    if tool == "bandit":
        details = _bandit_rule_details(rule)
        if details:
            return {
                "explanation": f"{details['explanation']} {_security_severity_phrase(severity)}",
                "fix": details["fix"],
                "risk": details["risk"],
                "impact": details["impact"],
            }

        return {
            "explanation": (
                f"Bandit detected a security-related issue for rule {rule or 'UNKNOWN'}. "
                f"{_security_severity_phrase(severity)}"
            ),
            "fix": (
                "Review the flagged code path, validate all untrusted input, avoid dangerous APIs, "
                "and replace insecure patterns with safer alternatives."
            ),
            "risk": "Security vulnerability or unsafe coding pattern.",
            "impact": (
                "The flagged code may expose the application to exploitation, data leakage, "
                "or other security weaknesses depending on context."
            ),
        }

    if tool == "flake8":
        details = _flake8_rule_details(rule)
        if details:
            return {
                "explanation": f"{details['explanation']} {_quality_severity_phrase(severity)}",
                "fix": details["fix"],
                "risk": details["risk"],
                "impact": details["impact"],
            }

        fallback_explanation = (
            f"Flake8 reported a code quality issue for rule {rule or 'UNKNOWN'}. "
            f"{_quality_severity_phrase(severity)}"
        )
        if message:
            fallback_explanation += f" Reported message: {message}"

        return {
            "explanation": fallback_explanation,
            "fix": (
                "Apply the recommended style or correctness fix for the flagged rule and "
                "rescan the project to verify the issue is resolved."
            ),
            "risk": "Code quality or correctness concern.",
            "impact": (
                "The issue may reduce readability, maintainability, or runtime reliability "
                "depending on the affected code path."
            ),
        }

    return {
        "explanation": "A generic issue was detected, but the tool type is not recognized by the rule helper.",
        "fix": "Inspect the issue details manually and apply the appropriate correction.",
        "risk": "Unknown risk.",
        "impact": "The real impact depends on the specific issue context.",
    }