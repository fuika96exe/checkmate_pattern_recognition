"""Quality gate for the portable package: no function may exceed cognitive complexity 15."""
from pathlib import Path

from complexipy import file_complexity

PACKAGE = Path(__file__).resolve().parents[1] / "xq_classify"
LIMIT = 15


def test_every_function_is_within_the_cognitive_complexity_limit():
    measured = [
        (path, function)
        for path in sorted(PACKAGE.rglob("*.py"))
        for function in file_complexity(str(path)).functions
    ]
    assert measured, "complexipy reported no functions"
    over = [
        f"{path.relative_to(PACKAGE).as_posix()}:{function.line_start} {function.name} = {function.complexity}"
        for path, function in measured
        if function.complexity > LIMIT
    ]
    assert not over, "over the limit:\n" + "\n".join(over)
