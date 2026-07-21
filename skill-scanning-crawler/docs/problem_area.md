# Problem Area

Agent systems can be extended with external packages called skills. A skill may contain instructions, scripts, references, templates, and other auxiliary files that help an AI agent perform a task.

The security problem is that agents may trust these skills. A public skill package can contain unsafe instructions, dangerous scripts, credential access, hidden prompt injection, or data-exfiltration logic.

Part 2 of the project studies vulnerability scanners that try to detect these risks.

Part 1, this crawler project, solves the dataset problem: before scanners can be compared, they need a real, reproducible corpus of public skills to scan.

Therefore, this project converts:

```text
Unstructured public repositories
```

into:

```text
Structured, validated, reproducible scanner input
```

The crawler is not the security scanner. It is the acquisition layer that makes the later scanner comparison meaningful.
