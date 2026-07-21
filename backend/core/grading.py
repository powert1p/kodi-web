"""Answer grading — rule-based + Claude LLM fallback.

Strategy:
    1. Multi-stage normalisation and comparison pipeline (fast, free).
    2. If rule-based says "incorrect" and ANTHROPIC_API_KEY is set,
       ask Claude to double-check (catches false negatives from open-format).

    Rule-based handles:
    - "1/2" vs "0.5" vs "0,5", integer vs float
    - Mixed numbers: "2 1/3"
    - Unicode minus signs (−, –, —)
    - Units: "32%" == "32", "75°" == "75", "12 см" == "12"
    - Multi-value: "16; 25" vs "25; 16" (set comparison)
    - Text with number: "Уменьшится на 51%" vs "51"
    - Parentheses/braces: "(3; 2)" vs "3; 2"
"""

from __future__ import annotations

import ast
import asyncio
import logging
import re
import unicodedata
from fractions import Fraction

logger = logging.getLogger(__name__)

_anthropic_client = None

# ── Character normalisation tables ────────────────────────────

_DASHES = str.maketrans({
    "\u2212": "-",  # MINUS SIGN
    "\u2013": "-",  # EN DASH
    "\u2014": "-",  # EM DASH
    "\u2010": "-",  # HYPHEN
    "\u2011": "-",  # NON-BREAKING HYPHEN
    "\u00d7": "*",  # MULTIPLICATION SIGN
})

_MIXED_RE = re.compile(r"^(-?\d+)\s+(\d+\s*/\s*\d+)$")

# ── Unit / suffix stripping ───────────────────────────────────

_UNITS_RE = re.compile(
    r"\s*(?:"
    r"км/час|км/ч|м/с|т/га"           # compound speed/area units first
    r"|см(?:[²³]|\^[23])?|дм(?:[²³]|\^[23])?"  # length + area/volume
    r"|мм(?:[²³]|\^[23])?|км(?:[²³]|\^[23])?"
    r"|м(?:[²³]|\^[23])?"             # metre (must come after км/мм/дм/см)
    r"|кг|г(?:р(?:амм\w*)?)?|тонн\w*" # mass
    r"|литр\w*|л"                      # volume
    r"|тг|тенге|сом|руб\w*"           # currency
    r"|мин(?:ут\w*)?|час\w*|сек(?:унд\w*)?" # time
    r"|лет|год\w*|месяц\w*|дн(?:ей|я)?"    # time periods
    r"|недел\w*"                       # weeks
    r"|градус\w*|°"                    # degrees
    r"|%"                              # percent
    r")\s*$",
    re.IGNORECASE,
)


def _strip_wrapping(text: str) -> str:
    """Remove wrapping parentheses or braces if balanced inside."""
    if len(text) < 2:
        return text
    if (text[0] == "(" and text[-1] == ")") or \
       (text[0] == "{" and text[-1] == "}"):
        inner = text[1:-1]
        opener = text[0]
        closer = text[-1]
        depth = 0
        balanced = True
        for ch in inner:
            if ch == opener:
                depth += 1
            elif ch == closer:
                depth -= 1
            if depth < 0:
                balanced = False
                break
        if balanced and depth == 0:
            return inner
    return text


# ── Normalisation ─────────────────────────────────────────────

def _normalise(text: str) -> str:
    """Lower-case, strip, collapse whitespace, normalise unicode,
    strip units and wrapping brackets."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASHES)
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = text.rstrip(".")
    text = _strip_wrapping(text)
    text = _UNITS_RE.sub("", text)
    text = text.replace(",", ".")
    text = text.strip()
    return text


def _normalise_keep_separators(text: str) -> str:
    """Normalise but keep ; and , as-is (for multi-value splitting)."""
    text = unicodedata.normalize("NFKC", text)
    text = text.translate(_DASHES)
    text = text.strip().lower()
    text = re.sub(r"\s+", " ", text)
    text = re.sub(r"\s*:\s*", ":", text)
    text = text.rstrip(".")
    text = _strip_wrapping(text)
    return text


def _compact(text: str) -> str:
    """Aggressive normalisation: remove all spaces, treat : as /."""
    compact = (
        _normalise(text)
        .replace(" ", "")
        .replace(":", "/")
        .replace("÷", "/")
        .replace("·", "*")
        .replace("⋅", "*")
    )

    def canonical_decimal(match: re.Match[str]) -> str:
        fraction = match.group(2).rstrip("0")
        return match.group(1) if not fraction else f"{match.group(1)}.{fraction}"

    return re.sub(r"(?<![\d.])(\d+)\.(\d+)(?![\d.])", canonical_decimal, compact)


# ── Safe algebraic equivalence ──────────────────────────────────────────────

_MAX_ALGEBRA_TERMS = 64
_MAX_ALGEBRA_POWER = 8
_MAX_ALGEBRA_COEFFICIENT_BITS = 256

_Monomial = tuple[tuple[str, int], ...]
_Polynomial = dict[_Monomial, Fraction]


def _clean_polynomial(polynomial: _Polynomial) -> _Polynomial:
    """Удаляет нулевые коэффициенты и ограничивает сложность выражения."""
    clean = {term: value for term, value in polynomial.items() if value}
    if len(clean) > _MAX_ALGEBRA_TERMS:
        raise ValueError("too many polynomial terms")
    for term, value in clean.items():
        if sum(power for _, power in term) > _MAX_ALGEBRA_POWER:
            raise ValueError("polynomial power is too large")
        if (
            value.numerator.bit_length() > _MAX_ALGEBRA_COEFFICIENT_BITS
            or value.denominator.bit_length() > _MAX_ALGEBRA_COEFFICIENT_BITS
        ):
            raise ValueError("polynomial coefficient is too large")
    return clean


def _add_polynomials(left: _Polynomial, right: _Polynomial) -> _Polynomial:
    result = dict(left)
    for term, value in right.items():
        result[term] = result.get(term, Fraction(0)) + value
    return _clean_polynomial(result)


def _scale_polynomial(polynomial: _Polynomial, factor: Fraction) -> _Polynomial:
    return _clean_polynomial({term: value * factor for term, value in polynomial.items()})


def _multiply_polynomials(left: _Polynomial, right: _Polynomial) -> _Polynomial:
    result: _Polynomial = {}
    for left_term, left_value in left.items():
        for right_term, right_value in right.items():
            powers: dict[str, int] = dict(left_term)
            for variable, power in right_term:
                powers[variable] = powers.get(variable, 0) + power
            term = tuple(sorted((variable, power) for variable, power in powers.items() if power))
            result[term] = result.get(term, Fraction(0)) + left_value * right_value
    return _clean_polynomial(result)


def _polynomial_from_ast(node: ast.AST, *, depth: int = 0) -> _Polynomial:
    """Строит многочлен без eval: только числа, переменные и базовые операции."""
    if depth > 24:
        raise ValueError("algebra expression is too deep")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("unsupported algebra constant")
        value = Fraction(str(node.value))
        return _clean_polynomial({(): value})

    if isinstance(node, ast.Name):
        if len(node.id) != 1 or not node.id.isascii() or not node.id.isalpha():
            raise ValueError("unsupported algebra variable")
        return {((node.id, 1),): Fraction(1)}

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
        operand = _polynomial_from_ast(node.operand, depth=depth + 1)
        return operand if isinstance(node.op, ast.UAdd) else _scale_polynomial(operand, Fraction(-1))

    if not isinstance(node, ast.BinOp):
        raise ValueError("unsupported algebra syntax")

    left = _polynomial_from_ast(node.left, depth=depth + 1)
    right = _polynomial_from_ast(node.right, depth=depth + 1)
    if isinstance(node.op, ast.Add):
        return _add_polynomials(left, right)
    if isinstance(node.op, ast.Sub):
        return _add_polynomials(left, _scale_polynomial(right, Fraction(-1)))
    if isinstance(node.op, ast.Mult):
        return _multiply_polynomials(left, right)
    if isinstance(node.op, ast.Div):
        if set(right) != {()} or not right[()]:
            raise ValueError("division by a variable or zero")
        return _scale_polynomial(left, Fraction(1, 1) / right[()])
    if isinstance(node.op, ast.Pow):
        if set(right) != {()} or right[()].denominator != 1:
            raise ValueError("non-integer algebra power")
        power = int(right[()])
        if not 0 <= power <= _MAX_ALGEBRA_POWER:
            raise ValueError("algebra power is out of bounds")
        result: _Polynomial = {(): Fraction(1)}
        for _ in range(power):
            result = _multiply_polynomials(result, left)
        return result
    raise ValueError("unsupported algebra operator")


def _parse_expression(text: str) -> ast.AST:
    """Парсит короткую школьную запись в ограниченное AST без выполнения."""
    expression = unicodedata.normalize("NFKC", text).lower().strip()
    expression = expression.translate(_DASHES)
    expression = (
        expression.replace("·", "*")
        .replace("⋅", "*")
        .replace("÷", "/")
        .replace(":", "/")
    )
    expression = expression.replace(",", ".").replace("^", "**")
    expression = re.sub(r"\s+", "", expression)
    expression = re.sub(r"(?<=[0-9])(?=[a-z(])", "*", expression)
    expression = re.sub(r"(?<=[a-z])(?=\()", "*", expression)
    expression = re.sub(r"(?<=\))(?=[0-9a-z(])", "*", expression)
    if not expression or len(expression) > 200:
        raise ValueError("algebra expression is empty or too long")
    parsed = ast.parse(expression, mode="eval")
    if sum(1 for _ in ast.walk(parsed)) > 96:
        raise ValueError("algebra expression has too many nodes")
    return parsed.body


def _parse_polynomial(text: str) -> _Polynomial:
    """Парсит короткую школьную запись в ограниченный точный многочлен."""
    return _polynomial_from_ast(_parse_expression(text))


def _expression_fingerprint(node: ast.AST, *, depth: int = 0) -> tuple[object, ...]:
    """Сохраняет структуру вычисления, нормализуя только + и × как коммутативные."""
    if depth > 24:
        raise ValueError("algebra expression is too deep")

    if isinstance(node, ast.Constant):
        if isinstance(node.value, bool) or not isinstance(node.value, (int, float)):
            raise ValueError("unsupported algebra constant")
        return ("number", Fraction(str(node.value)))

    if isinstance(node, ast.Name):
        if len(node.id) != 1 or not node.id.isascii() or not node.id.isalpha():
            raise ValueError("unsupported algebra variable")
        return ("variable", node.id)

    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.UAdd):
        return _expression_fingerprint(node.operand, depth=depth + 1)
    if isinstance(node, ast.UnaryOp) and isinstance(node.op, ast.USub):
        return ("negate", _expression_fingerprint(node.operand, depth=depth + 1))
    if not isinstance(node, ast.BinOp):
        raise ValueError("unsupported algebra syntax")

    if isinstance(node.op, (ast.Add, ast.Mult)):
        operator_type = type(node.op)
        operator_name = "add" if operator_type is ast.Add else "multiply"
        operands: list[tuple[object, ...]] = []

        def collect(current: ast.AST) -> None:
            if isinstance(current, ast.BinOp) and type(current.op) is operator_type:
                collect(current.left)
                collect(current.right)
                return
            operands.append(_expression_fingerprint(current, depth=depth + 1))

        collect(node)
        return (operator_name, *sorted(operands, key=repr))

    operators = {
        ast.Sub: "subtract",
        ast.Div: "divide",
        ast.Pow: "power",
    }
    operator_name = operators.get(type(node.op))
    if operator_name is None:
        raise ValueError("unsupported algebra operator")
    return (
        operator_name,
        _expression_fingerprint(node.left, depth=depth + 1),
        _expression_fingerprint(node.right, depth=depth + 1),
    )


def _equation_expressions(text: str) -> tuple[ast.AST, ast.AST]:
    """Возвращает безопасно разобранные левую и правую части равенства."""
    normalised = _normalise(text)
    if normalised.count("=") != 1:
        raise ValueError("not a single equation")
    left, right = normalised.split("=", 1)
    return _parse_expression(left), _parse_expression(right)


def _equation_fingerprint(text: str) -> tuple[tuple[object, ...], tuple[object, ...]]:
    """Структурный отпечаток двух сторон числового равенства."""
    left, right = _equation_expressions(text)
    return (
        _expression_fingerprint(left),
        _expression_fingerprint(right),
    )


def _constant_expression_value(node: ast.AST) -> Fraction | None:
    """Вычисляет только полностью числовое подвыражение без переменных."""
    if any(isinstance(item, ast.Name) for item in ast.walk(node)):
        return None
    try:
        polynomial = _polynomial_from_ast(node)
    except (TypeError, ValueError, ZeroDivisionError):
        return None
    if not polynomial:
        return Fraction(0)
    if set(polynomial) == {()}:
        return polynomial[()]
    return None


def _expression_matches_stage(student: ast.AST, correct: ast.AST) -> bool:
    """Сравнивает форму шага, разрешая лишь вычисление до эталонной константы."""
    student_fingerprint = _expression_fingerprint(student)
    correct_fingerprint = _expression_fingerprint(correct)
    if student_fingerprint == correct_fingerprint:
        return True
    if correct_fingerprint[0] != "number" or student_fingerprint[0] == "number":
        return False
    return _constant_expression_value(student) == correct_fingerprint[1]


def _compare_equation_structure(student_answer: str, correct_answer: str) -> bool:
    """Сопоставляет конкретную форму этапа, не схлопывая цепочку по residual."""
    student_left, student_right = _equation_expressions(student_answer)
    correct_left, correct_right = _equation_expressions(correct_answer)
    return (
        _expression_matches_stage(student_left, correct_left)
        and _expression_matches_stage(student_right, correct_right)
    ) or (
        _expression_matches_stage(student_left, correct_right)
        and _expression_matches_stage(student_right, correct_left)
    )


def _equation_polynomial(text: str) -> _Polynomial:
    if text.count("=") != 1:
        raise ValueError("not a single equation")
    left, right = text.split("=", 1)
    return _add_polynomials(
        _parse_polynomial(left),
        _scale_polynomial(_parse_polynomial(right), Fraction(-1)),
    )


def _proportional_polynomials(left: _Polynomial, right: _Polynomial) -> bool:
    """Уравнения эквивалентны, если их разности отличаются на ненулевой множитель."""
    if not left or not right:
        return left == right
    if set(left) != set(right):
        return False
    pivot = min(left)
    factor = left[pivot] / right[pivot]
    return factor != 0 and all(left[term] == right[term] * factor for term in left)


def _normalise_algebraic(text: str) -> str:
    """Нормализует школьные проценты для безопасного AST-парсинга."""
    source = _normalise(text)
    # Финальный знак процента уже снят как единица ответа. Оставшийся
    # «· 100%» в школьной формуле означает перевод доли в проценты.
    source = re.sub(r"(?<![\d.])100%", "100", source)
    return re.sub(
        r"(?<![\w.])(-?\d+(?:\.\d+)?)%",
        r"(\1/100)",
        source,
    )


def _normalise_calculation_expression(text: str) -> str:
    """Сохраняет процент как коэффициент внутри арифметического действия."""
    if "%" not in text or not re.search(r"[+\-*/·:×÷]", text):
        return _normalise_algebraic(text)
    source = re.sub(r"(?<![\d.])100%", "100", text)
    source = re.sub(
        r"(?<![\w.])(-?\d+(?:[.,]\d+)?)%",
        r"(\1/100)",
        source,
    )
    return _normalise_algebraic(source)


def _compare_algebraic(
    student_answer: str,
    correct_answer: str,
    *,
    allow_equation_scaling: bool = True,
) -> bool | None:
    """Возвращает точное сравнение или None для неподдерживаемой записи."""
    try:
        student = _normalise_algebraic(student_answer)
        correct = _normalise_algebraic(correct_answer)
        student_is_equation = student.count("=") == 1
        correct_is_equation = correct.count("=") == 1
        if student_is_equation != correct_is_equation:
            if student_is_equation:
                left, right = student.split("=", 1)
                left_polynomial = _parse_polynomial(left)
                right_polynomial = _parse_polynomial(right)
                expected = _parse_polynomial(correct)
                if left_polynomial == right_polynomial == expected:
                    return True
            return None
        if student_is_equation:
            student_polynomial = _equation_polynomial(student)
            correct_polynomial = _equation_polynomial(correct)
            if not allow_equation_scaling:
                return _compare_equation_structure(student, correct)
            student_has_variable = any(term for term in student_polynomial)
            correct_has_variable = any(term for term in correct_polynomial)
            if (
                not student_polynomial
                or not correct_polynomial
                or not student_has_variable
                or not correct_has_variable
            ):
                return _compare_equation_structure(student, correct)
            return _proportional_polynomials(
                student_polynomial,
                correct_polynomial,
            )
        return _parse_polynomial(student) == _parse_polynomial(correct)
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
        return None


# ── Number parsing ────────────────────────────────────────────

def _try_as_number(text: str) -> float | None:
    """Try to parse text as a number (int, float, simple or mixed fraction).

    Supports: 42, 3.14, 3,14, -5, 1/2, -2/3, 2 1/3, -1 3/4, 4:9.
    """
    text = text.replace(",", ".").strip()
    if text.count(":") == 1 and "/" not in text:
        text = text.replace(":", "/")

    m = _MIXED_RE.match(text)
    if m:
        try:
            whole = int(m.group(1))
            frac = Fraction(m.group(2).replace(" ", ""))
            sign = -1 if whole < 0 else 1
            return float(abs(whole)) * sign + sign * float(frac)
        except (ValueError, ZeroDivisionError):
            pass

    text = text.replace(" ", "")
    if "/" in text:
        try:
            return float(Fraction(text))
        except (ValueError, ZeroDivisionError):
            pass
    try:
        return float(text)
    except ValueError:
        return None


def _try_as_fraction(text: str) -> Fraction | None:
    """Try to parse text as an exact Fraction.

    Supports: 1/2, 4/6, 0.5, 0,5, 2 1/3, -3/4, 4:9.
    """
    text = text.replace(",", ".").strip()
    if text.count(":") == 1 and "/" not in text:
        text = text.replace(":", "/")

    m = _MIXED_RE.match(text)
    if m:
        try:
            whole = int(m.group(1))
            frac = Fraction(m.group(2).replace(" ", ""))
            sign = -1 if whole < 0 else 1
            return Fraction(abs(whole)) * sign + frac * sign
        except (ValueError, ZeroDivisionError):
            pass

    text = text.replace(" ", "")
    try:
        return Fraction(text)
    except (ValueError, ZeroDivisionError):
        return None


# ── Multi-value comparison ────────────────────────────────────

def _compare_multi_value(sa: str, ca: str) -> bool | None:
    """Compare answers that contain multiple values separated by ; or ,.

    Returns True/False if comparison is possible, None if not applicable.
    Both inputs should be normalised with _normalise_keep_separators.
    """
    for sep in (";", ","):
        if sep not in ca and sep not in sa:
            continue

        ca_parts = [_normalise(p) for p in ca.split(sep) if p.strip()]
        if len(ca_parts) < 2:
            # Also try the other separator for ca
            other = "," if sep == ";" else ";"
            ca_parts = [_normalise(p) for p in ca.split(other) if p.strip()]
            if len(ca_parts) < 2:
                continue

        # Split sa by either ; or ,
        sa_parts = [_normalise(p) for p in re.split(r"[;,]", sa) if p.strip()]

        if len(ca_parts) != len(sa_parts):
            return None

        ca_nums = [_try_as_number(p) for p in ca_parts]
        sa_nums = [_try_as_number(p) for p in sa_parts]

        if all(n is not None for n in ca_nums) and \
           all(n is not None for n in sa_nums):
            if _nums_equal(ca_nums, sa_nums):
                return True
            if _nums_equal(sorted(ca_nums), sorted(sa_nums)):
                return True
            return False

        # Text fallback: compare sorted parts
        if sorted(ca_parts) == sorted(sa_parts):
            return True
        if ca_parts == sa_parts:
            return True
        return False

    return None


def _nums_equal(a: list[float | None], b: list[float | None]) -> bool:
    """Element-wise numeric comparison with tolerance."""
    if len(a) != len(b):
        return False
    return all(
        x is not None and y is not None and abs(x - y) < 1e-6
        for x, y in zip(a, b)
    )


# ── Extract number from text answer ──────────────────────────

_NUMBER_IN_TEXT_RE = re.compile(r"-?\d+(?:[.,]\d+)?(?:\s*/\s*\d+)?")


def _extract_number_from_text(text: str) -> float | None:
    """Extract a single number from a text answer like 'Уменьшится на 51%'.

    Returns the number if exactly one is found, None otherwise.
    """
    nums = _NUMBER_IN_TEXT_RE.findall(text)
    if len(nums) == 1:
        return _try_as_number(nums[0])
    return None


# ── Unit conversion ───────────────────────────────────────────

# Unit conversion tables — value is the multiplier to convert to base unit
_UNIT_TO_BASE = {
    # Длина → метры
    'мм': ('length', 0.001), 'см': ('length', 0.01), 'дм': ('length', 0.1),
    'м': ('length', 1.0), 'км': ('length', 1000.0),
    'mm': ('length', 0.001), 'cm': ('length', 0.01), 'dm': ('length', 0.1),
    'm': ('length', 1.0), 'km': ('length', 1000.0),
    # Масса → граммы
    'мг': ('mass', 0.001), 'г': ('mass', 1.0), 'кг': ('mass', 1000.0),
    'ц': ('mass', 100000.0), 'т': ('mass', 1000000.0),
    'тонн': ('mass', 1000000.0), 'тонна': ('mass', 1000000.0),
    'mg': ('mass', 0.001), 'g': ('mass', 1.0), 'kg': ('mass', 1000.0),
    't': ('mass', 1000000.0),
    # Площадь → м²
    'мм²': ('area', 1e-6), 'см²': ('area', 1e-4), 'дм²': ('area', 0.01),
    'м²': ('area', 1.0), 'км²': ('area', 1e6),
    'га': ('area', 10000.0), 'а': ('area', 100.0),
    'mm²': ('area', 1e-6), 'cm²': ('area', 1e-4), 'dm²': ('area', 0.01),
    'm²': ('area', 1.0), 'km²': ('area', 1e6),
    # Объём → литры
    'мл': ('volume', 0.001), 'л': ('volume', 1.0), 'дл': ('volume', 0.1),
    'см³': ('volume', 0.001), 'дм³': ('volume', 1.0), 'м³': ('volume', 1000.0),
    'ml': ('volume', 0.001), 'l': ('volume', 1.0),
    'cm³': ('volume', 0.001), 'dm³': ('volume', 1.0), 'm³': ('volume', 1000.0),
    # Время → секунды (все словоформы)
    'с': ('time', 1.0), 'сек': ('time', 1.0),
    'секунд': ('time', 1.0), 'секунда': ('time', 1.0), 'секунды': ('time', 1.0),
    'мин': ('time', 60.0),
    'минут': ('time', 60.0), 'минута': ('time', 60.0), 'минуты': ('time', 60.0),
    'ч': ('time', 3600.0),
    'час': ('time', 3600.0), 'часа': ('time', 3600.0), 'часов': ('time', 3600.0),
    'сут': ('time', 86400.0), 'суток': ('time', 86400.0),
    'день': ('time', 86400.0), 'дня': ('time', 86400.0), 'дней': ('time', 86400.0),
    'sec': ('time', 1.0), 'min': ('time', 60.0), 'h': ('time', 3600.0),
    # Скорость → м/с
    'м/с': ('speed', 1.0), 'м/мин': ('speed', 1/60),
    'км/ч': ('speed', 1/3.6), 'км/час': ('speed', 1/3.6),
}

_UNIT_NUMBER_RE = re.compile(r'^(-?\d+(?:[.,]\d+)?)\s*(.+)$')


def _extract_number_and_unit(text: str):
    """Extract (number, unit) from text like '3см', '0.3 дм', '150kg'."""
    text = text.strip().lower()
    # Normalise unicode dashes to ASCII minus
    text = text.translate(_DASHES)
    # Replace comma with period for Russian decimals
    text = text.replace(',', '.')
    # Try to match number followed by optional unit
    m = _UNIT_NUMBER_RE.match(text)
    if m:
        try:
            num = float(m.group(1))
            unit = m.group(2).strip()
            if unit in _UNIT_TO_BASE:
                return num, unit
        except ValueError:
            pass
    return None, None


def _try_unit_conversion(student_raw: str, correct_raw: str) -> bool:
    """Compare answers after unit conversion. Returns True if equivalent."""
    s_num, s_unit = _extract_number_and_unit(student_raw)
    c_num, c_unit = _extract_number_and_unit(correct_raw)
    if s_num is None or c_num is None:
        return False
    if s_unit is None or c_unit is None:
        return False
    s_dim, s_factor = _UNIT_TO_BASE[s_unit]
    c_dim, c_factor = _UNIT_TO_BASE[c_unit]
    if s_dim != c_dim:
        return False
    s_base = s_num * s_factor
    c_base = c_num * c_factor
    return abs(s_base - c_base) < 1e-6


# ── Symbol ↔ word equivalence ─────────────────────────────────

_SYMBOL_TO_WORD = {
    "*": "умножение", "×": "умножение", "·": "умножение",
    "+": "сложение",
    "-": "вычитание", "−": "вычитание",
    "/": "деление", "÷": "деление",
}
_WORD_TO_SYMBOLS = {}
for _sym, _word in _SYMBOL_TO_WORD.items():
    _WORD_TO_SYMBOLS.setdefault(_word, set()).add(_sym)


# ── Main grading logic ────────────────────────────────────────

def check_answer_rule_based(
    student_answer: str,
    correct_answer: str,
    answer_type: str | None = None,
    *,
    allow_equation_scaling: bool = True,
) -> bool:
    """Rule-based check. Returns True if clearly correct."""
    sa = _normalise(student_answer)
    ca = _normalise(correct_answer)

    if not sa:
        return False

    # ── 0.5. Unit-aware gate ──
    # If both raw answers have recognised units, delegate entirely to
    # unit conversion so that "3см" vs "3кг" is NOT accepted.
    _s_num, _s_unit = _extract_number_and_unit(student_answer)
    _c_num, _c_unit = _extract_number_and_unit(correct_answer)
    if _s_unit is not None and _c_unit is not None:
        return _try_unit_conversion(student_answer, correct_answer)

    # ── 0. Symbol ↔ word equivalence (e.g. * == умножение) ──
    if sa in _SYMBOL_TO_WORD and ca == _SYMBOL_TO_WORD[sa]:
        return True
    if ca in _SYMBOL_TO_WORD and sa == _SYMBOL_TO_WORD[ca]:
        return True
    if sa in _WORD_TO_SYMBOLS and ca in _WORD_TO_SYMBOLS[sa]:
        return True
    if ca in _WORD_TO_SYMBOLS and sa in _WORD_TO_SYMBOLS[ca]:
        return True

    # ── 1. Exact string match after normalisation ──
    if sa == ca:
        return True

    # ── 2. Numeric comparison (works for all answer_types) ──
    sn = _try_as_number(sa)
    cn = _try_as_number(ca)
    if sn is not None and cn is not None:
        if abs(sn - cn) < 1e-6:
            return True

    # ── 3. Exact fraction comparison ──
    if answer_type in ("fraction", None):
        sf = _try_as_fraction(sa)
        cf = _try_as_fraction(ca)
        if sf is not None and cf is not None and sf == cf:
            return True

    # ── 4. Exact algebraic equivalence without eval/LLM ──
    algebraic = _compare_algebraic(
        student_answer,
        correct_answer,
        allow_equation_scaling=allow_equation_scaling,
    )
    if algebraic is True:
        return True

    # ── 5. Compact string comparison (all spaces removed, : → /) ──
    student_compact = _compact(student_answer)
    correct_compact = _compact(correct_answer)
    if student_compact == correct_compact:
        return True
    if student_compact.count("=") == correct_compact.count("=") == 1:
        student_left, student_right = student_compact.split("=", 1)
        correct_left, correct_right = correct_compact.split("=", 1)
        if (
            student_left
            and student_right
            and student_left == correct_right
            and student_right == correct_left
        ):
            return True

    # В strict step-mode уравнение уже прошло структурный checker выше.
    # Не интерпретируем десятичную запятую внутри него как разделитель списка:
    # иначе перестановка фрагментов могла превратить другой этап в «верный».
    if not allow_equation_scaling and "=" in ca:
        return False

    # ── 6. Multi-value comparison (;  or , separated) ──
    ca_raw = _normalise_keep_separators(correct_answer)
    sa_raw = _normalise_keep_separators(student_answer)
    multi = _compare_multi_value(sa_raw, ca_raw)
    if multi is not None:
        return multi

    # ── 7. Text-embedded number extraction ──
    # If correct answer has text + number, and student typed just the number
    if sn is not None and cn is None:
        extracted = _extract_number_from_text(ca)
        if extracted is not None and abs(sn - extracted) < 1e-6:
            return True
    # Reverse: student typed text, correct is just number
    if cn is not None and sn is None:
        extracted = _extract_number_from_text(sa)
        if extracted is not None and abs(cn - extracted) < 1e-6:
            return True

    return False


# ── Claude LLM fallback ──────────────────────────────────────

_CLAUDE_PROMPT = (
    "Ты проверяешь математическую задачу ученика 7-8 класса.\n\n"
    "Задача:\n{problem_text}\n\n"
    "Правильный ответ: {correct_answer}\n"
    "Ответ ученика: {student_answer}\n\n"
    "Ответ ученика математически эквивалентен правильному?\n"
    "Учитывай: разные записи (дроби/десятичные), знаки, порядок, "
    "округление, единицы измерения, эквивалентные выражения, "
    "символы операций (* = умножение, / = деление и т.п.).\n\n"
    "ВАЖНО: Первое слово ответа ОБЯЗАТЕЛЬНО YES или NO.\n"
    "Затем одно предложение-пояснение на русском."
)

_CLAUDE_TIMEOUT = 8.0


def _get_anthropic_client():
    """Lazy-init the async Anthropic client."""
    global _anthropic_client
    if _anthropic_client is None:
        try:
            import anthropic
            from core.config import settings
            if settings.anthropic_api_key:
                _anthropic_client = anthropic.AsyncAnthropic(
                    api_key=settings.anthropic_api_key
                )
        except ImportError:
            logger.warning("anthropic package not installed, LLM fallback disabled")
    return _anthropic_client


async def check_with_claude(
    student_answer: str, correct_answer: str, problem_text: str
) -> tuple[bool, str]:
    """Ask Claude whether the student's answer is equivalent.

    Returns (is_correct, explanation).
    Falls back to (False, "") on any error.
    """
    client = _get_anthropic_client()
    if client is None:
        return False, ""

    prompt = _CLAUDE_PROMPT.format(
        problem_text=problem_text[:500],
        correct_answer=correct_answer[:200],
        student_answer=student_answer[:200],
    )

    try:
        response = await asyncio.wait_for(
            client.messages.create(
                model="claude-haiku-4-5",
                max_tokens=150,
                messages=[{"role": "user", "content": prompt}],
            ),
            timeout=_CLAUDE_TIMEOUT,
        )
        text = response.content[0].text.strip()
        lines = text.split("\n")
        first_line = lines[0].strip().upper()
        explanation = "\n".join(lines[1:]).strip()

        if first_line.startswith("YES"):
            rest = lines[0].strip()[3:].strip().lstrip(".,:-").strip()
            full = f"{rest}\n{explanation}".strip() if rest else explanation
            return True, full or "Подтверждено AI"
        if first_line.startswith("NO"):
            rest = lines[0].strip()[2:].strip().lstrip(".,:-").strip()
            full = f"{rest}\n{explanation}".strip() if rest else explanation
            return False, full or "Ответ ученика не эквивалентен правильному"

        text_upper = text.upper()
        if "\nYES" in text_upper or text_upper.endswith("YES"):
            return True, text
        return False, text

    except asyncio.TimeoutError:
        logger.warning("Claude timeout (%.1fs)", _CLAUDE_TIMEOUT)
        return False, ""
    except (RuntimeError, ValueError, AttributeError, IndexError) as exc:
        logger.warning("Claude LLM check failed: %s", exc)
        return False, ""


# ── Public API ────────────────────────────────────────────────


def check_answer(
    student_answer: str, correct_answer: str, answer_type: str | None = None
) -> bool:
    """Synchronous rule-based check."""
    return check_answer_rule_based(student_answer, correct_answer, answer_type)


def _is_proof_free_equation(text: str) -> bool:
    """Находит запись, которая повторяет результат, но не показывает ход."""
    if text.count("=") != 1:
        return False
    left, right = (part.strip() for part in text.split("=", 1))
    if left.casefold() in {"ответ", "answer"}:
        return True
    try:
        return _expression_fingerprint(
            _parse_expression(_normalise_algebraic(left))
        ) == _expression_fingerprint(
            _parse_expression(_normalise_algebraic(right))
        )
    except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
        return _compact(left) == _compact(right)


def classify_step_evidence(
    student_answer: str, correct_answer: str, answer_type: str | None = None
) -> bool | None:
    """Классифицирует доказательство шага: верно, неверно или недостаточно.

    ``None`` означает, что запись нельзя безопасно использовать ни как
    положительное, ни как отрицательное mastery-evidence: OCR неполон,
    синтаксис не поддержан или вместо вычисления повторён готовый ответ.
    """
    def calculations(text: str) -> list[str]:
        return [
            part.strip()
            for part in re.split(
                r"\s*;\s*|\s+(?:и|and)\s+",
                text,
                flags=re.IGNORECASE,
            )
            if part.strip()
        ]

    # Сначала проверяем поддержку синтаксиса. Иначе точное текстовое совпадение
    # неподдерживаемой записи (например, ``√3600 = 60``) ложно станет proof.
    if not is_step_evidence_readable(
        student_answer
    ) or not is_step_evidence_readable(correct_answer):
        return None

    # Уравнение против скалярного эталона обязано доказать вычисление ниже.
    # Иначе тождество «75 = 75» превращается в ложное подтверждение хода решения.
    if (
        ("=" in student_answer) == ("=" in correct_answer)
        and check_answer_rule_based(
            student_answer,
            correct_answer,
            answer_type,
            allow_equation_scaling=False,
        )
    ):
        if _is_proof_free_equation(student_answer) or _is_proof_free_equation(
            correct_answer
        ):
            return None
        return True

    # В тетради ребёнок может уточнить единицу («500 г смеси»), а Vision —
    # опустить такое уточнение из эталона («80 г» вместо «80 г соли»).
    # Сравниваем математическую запись без короткой подписи, но только если
    # сама единица с обеих сторон совпадает буквально.
    def without_rhs_unit_label(text: str) -> tuple[str, str | None]:
        for unit in sorted(_UNIT_TO_BASE, key=len, reverse=True):
            pattern = re.compile(
                rf"(?<![A-Za-zА-Яа-яЁё])({re.escape(unit)})\s+"
                r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\s-]{0,39}$",
                flags=re.IGNORECASE,
            )
            match = pattern.search(text)
            if match is not None:
                return f"{text[:match.start()]}{match.group(1)}", unit.casefold()
        plain_unit = _UNITS_RE.search(text)
        if plain_unit is not None:
            return text, plain_unit.group(0).strip().casefold()
        return text, None

    student_math, student_unit = without_rhs_unit_label(student_answer)
    correct_math, correct_unit = without_rhs_unit_label(correct_answer)
    if (
        (student_math != student_answer or correct_math != correct_answer)
        and student_unit is not None
        and student_unit == correct_unit
        and check_answer_rule_based(
            student_math,
            correct_math,
            answer_type,
            allow_equation_scaling=False,
        )
    ):
        return True

    # Некоторые проверенные разборы хранят несколько скалярных результатов
    # одним шагом: «20 и 60». Сопоставляем каждый результат с отдельным
    # вычислением Vision, не полагаясь на порядок и не принимая тавтологии.
    expected_calculations = calculations(correct_answer)
    if "=" not in correct_answer and len(expected_calculations) > 1:
        observed_calculations = calculations(student_answer)
        if len(observed_calculations) != len(expected_calculations):
            return None

        classifications = [
            [classify_step_evidence(observed, expected, answer_type)
             for observed in observed_calculations]
            for expected in expected_calculations
        ]

        def has_complete_match(expected_index: int, used: set[int]) -> bool:
            if expected_index == len(expected_calculations):
                return True
            return any(
                classification is True
                and observed_index not in used
                and has_complete_match(expected_index + 1, used | {observed_index})
                for observed_index, classification in enumerate(
                    classifications[expected_index]
                )
            )

        if has_complete_match(0, set()):
            return True
        if any(
            classification is None
            for row in classifications
            for classification in row
        ):
            return None
        return False

    # Vision иногда сохраняет подпись и несколько эквивалентных вычислений:
    # «m соли = 20% · 300 г; 0,2 · 300 = 60 г». Для эталона-значения
    # принимаем запись только когда каждое числовое равенство даёт эталон,
    # а хотя бы одно равенство действительно содержит вычисление.
    if "=" not in correct_answer and "=" in student_answer:
        try:
            expected = _parse_polynomial(_normalise_algebraic(correct_answer))
        except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
            expected = None
        if expected is not None:
            evidence_valid = True
            saw_computation = False
            saw_named_assignment = False
            saw_evidence = False
            for calculation in calculations(student_answer):
                if "=" not in calculation:
                    evidence_valid = False
                    break
                parts = calculation.split("=")
                suffix: list[_Polynomial] = []
                parse_failure_index: int | None = None
                for index in range(len(parts) - 1, -1, -1):
                    normalised_part = _normalise_calculation_expression(parts[index])
                    # В записи «x = 40 : 0,8 = 50» первый символ — имя
                    # найденной величины, а не ещё одно числовое равенство.
                    # Пропускаем только одиночную переменную: выражение вроде
                    # «x + 1» по-прежнему обязано пройти математическую проверку.
                    if index == 0 and re.fullmatch(r"[a-z]", normalised_part):
                        if len(suffix) == 1:
                            saw_named_assignment = True
                        break
                    try:
                        suffix.append(_parse_polynomial(normalised_part))
                    except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
                        parse_failure_index = index
                        break
                if not suffix or any(value != expected for value in suffix):
                    evidence_valid = False
                    break
                if parse_failure_index not in {None, 0}:
                    evidence_valid = False
                    break
                if parse_failure_index == 0:
                    label = parts[0].strip()
                    if not label or re.search(r"[\d+\-*/%·:]", label):
                        evidence_valid = False
                        break
                if any(
                    re.search(
                        r"(?:\d|\))\s*(?:[+\-*/·:×÷])\s*(?:\d|\()",
                        _normalise_algebraic(part),
                    )
                    for part in parts
                ):
                    saw_computation = True
                saw_evidence = True
            if evidence_valid and saw_evidence:
                if saw_computation or saw_named_assignment:
                    return True
                # ``75 = 75`` и ``Ответ = 75`` читаются, но не доказывают
                # вычисление. Просим нормальное фото вместо штрафа mastery.
                return None
            return False

    # Если Vision вернул само вычисление, его структура уже была проверена выше.
    # Сравнение только правых частей снова превратило бы любое истинное равенство
    # с тем же итогом в ложное доказательство нужного шага.
    if "=" not in student_answer:
        return None if "=" in correct_answer else False

    observed_calculations = calculations(student_answer)
    expected_calculations = calculations(correct_answer)
    if (
        len(expected_calculations) < 2
        or any(item.count("=") != 1 for item in observed_calculations)
        or any(item.count("=") != 1 for item in expected_calculations)
    ):
        return False
    if len(observed_calculations) < len(expected_calculations):
        return None
    if len(observed_calculations) > len(expected_calculations):
        return False

    unmatched = set(range(len(observed_calculations)))
    for expected in expected_calculations:
        match = next(
            (
                index
                for index in unmatched
                if check_answer_rule_based(
                    observed_calculations[index],
                    expected,
                    answer_type,
                    allow_equation_scaling=False,
                )
            ),
            None,
        )
        if match is None:
            return False
        unmatched.remove(match)
    return not unmatched


def check_step_evidence(
    student_answer: str, correct_answer: str, answer_type: str | None = None
) -> bool:
    """Совместимый boolean-wrapper для guided/manual callers."""
    return classify_step_evidence(
        student_answer,
        correct_answer,
        answer_type,
    ) is True


_UNREADABLE_MATH_RE = re.compile(
    r"(?:\?|…|_{2,}|неразбор|не\s+видно|неясно|illegible|unreadable|unknown)",
    flags=re.IGNORECASE,
)


def is_step_evidence_readable(student_answer: str) -> bool:
    """Отличает проверяемую математическую запись от неполного OCR.

    Функция не оценивает правильность. Она лишь подтверждает, что каждый
    математический фрагмент можно безопасно разобрать; иначе фото должно
    вернуться как ``unsure`` и не менять mastery.
    """
    if not student_answer.strip() or _UNREADABLE_MATH_RE.search(student_answer):
        return False

    saw_math = False
    calculations = [
        part.strip()
        for part in re.split(
            r"\s*;\s*|\s+(?:и|and)\s+",
            student_answer,
            flags=re.IGNORECASE,
        )
        if part.strip()
    ]
    for calculation in calculations:
        parts = [part.strip() for part in calculation.split("=")]
        if not parts or any(not part for part in parts):
            return False
        for index, part in enumerate(parts):
            candidate = part
            for unit in sorted(_UNIT_TO_BASE, key=len, reverse=True):
                match = re.search(
                    rf"(?<![A-Za-zА-Яа-яЁё])({re.escape(unit)})\s+"
                    r"[A-Za-zА-Яа-яЁё][A-Za-zА-Яа-яЁё\s-]{0,39}$",
                    candidate,
                    flags=re.IGNORECASE,
                )
                if match is not None:
                    candidate = f"{candidate[:match.start()]}{match.group(1)}"
                    break
            try:
                # Для readability достаточно безопасно разобрать структуру.
                # Polynomial parser намеренно уже и отвергает валидные
                # рациональные выражения с переменной в знаменателе.
                _expression_fingerprint(
                    _parse_expression(_normalise_algebraic(candidate))
                )
                saw_math = True
            except (SyntaxError, TypeError, ValueError, ZeroDivisionError):
                # В «m соли = 0,2 · 300 = 60 г» первый фрагмент — подпись
                # величины. Подпись допустима только перед разобранным равенством.
                is_leading_label = (
                    index == 0
                    and len(parts) > 1
                    and not re.search(r"[\d+\-*/%·:×÷?]", part)
                )
                if not is_leading_label:
                    return False
    return saw_math


def is_step_reference_supported(correct_answer: str) -> bool:
    """Проверяет, что эталон шага пригоден для typed- и photo-проверки."""
    return is_step_evidence_readable(correct_answer) and not _is_proof_free_equation(
        correct_answer
    )


async def check_answer_smart(
    student_answer: str,
    correct_answer: str,
    problem_text: str,
    answer_type: str | None = None,
) -> tuple[bool, str]:
    """Rule-based check. Claude is invoked separately on dispute only."""
    is_correct = check_answer_rule_based(
        student_answer, correct_answer, answer_type
    )
    return is_correct, ""
