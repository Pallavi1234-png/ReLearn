"""Parsing helpers: turn messy student text (unicode, ^, sqrt, implicit multiplication)
into SymPy objects. Everything here fails soft (returns None) so bad input never crashes the API."""
import re
import string
from fractions import Fraction

import sympy as sp
from sympy.parsing.sympy_parser import (parse_expr, standard_transformations,
                                        implicit_multiplication_application, convert_xor)

_TRANS = standard_transformations + (implicit_multiplication_application, convert_xor)
_LOCAL = {c: sp.Symbol(c) for c in string.ascii_letters}
_LOCAL.update({"sqrt": sp.sqrt, "Abs": sp.Abs})
x = sp.Symbol("x")

_SUP = {"⁰": "0", "¹": "1", "²": "2", "³": "3", "⁴": "4", "⁵": "5", "⁶": "6", "⁷": "7", "⁸": "8", "⁹": "9"}
_SUB = {"₀": "0", "₁": "1", "₂": "2", "₃": "3", "₄": "4", "₅": "5", "₆": "6", "₇": "7", "₈": "8", "₉": "9"}


def normalize(s):
    if s is None:
        return ""
    s = str(s)
    for a, b in (("−", "-"), ("–", "-"), ("—", "-"), ("×", "*"), ("·", "*"), ("÷", "/"), ("₹", ""), ("≠", "!=")):
        s = s.replace(a, b)
    s = re.sub("[" + "".join(_SUP) + "]+", lambda m: "^" + "".join(_SUP[c] for c in m.group()), s)
    s = re.sub("[" + "".join(_SUB) + "]+", lambda m: "".join(_SUB[c] for c in m.group()), s)
    s = re.sub(r"√\s*\(", "sqrt(", s)
    s = re.sub(r"√\s*(\d+(?:\.\d+)?|[a-zA-Z])", r"sqrt(\1)", s)
    s = re.sub(r"(\d|\))\s*(sqrt)", r"\1*\2", s)
    s = re.sub(r"\|\s*([^|]+?)\s*\|", r"Abs(\1)", s)
    return s.strip()


def parse_expr_safe(text):
    t = normalize(text).strip().rstrip(".,;")
    if not t or len(t) > 200 or re.search(r"[A-Za-z]{4,}", t.replace("sqrt", "").replace("Abs", "")):
        return None
    try:
        return parse_expr(t, local_dict=dict(_LOCAL), transformations=_TRANS, evaluate=True)
    except Exception:
        return None


def parse_struct(text):
    """Like parse_expr_safe but keeps structure (6(x+2) stays a product, not 6x+12)."""
    t = normalize(text).strip().rstrip(".,;")
    if not t or len(t) > 200 or re.search(r"[A-Za-z]{4,}", t.replace("sqrt", "").replace("Abs", "")):
        return None
    try:
        return parse_expr(t, local_dict=dict(_LOCAL), transformations=_TRANS, evaluate=False)
    except Exception:
        return None


def parse_equation(text):
    """Return (lhs, rhs) sympy exprs when text is a single equation, else None."""
    t = normalize(text)
    if t.count("=") != 1 or "!=" in t or "<=" in t or ">=" in t:
        return None
    l, r = t.split("=")
    L, R = parse_expr_safe(l), parse_expr_safe(r)
    if L is None or R is None:
        return None
    return L, R


def eq_poly(eq):
    return sp.expand(eq[0] - eq[1])


def solution_set(poly):
    fs = list(poly.free_symbols)
    if len(fs) != 1:
        return None
    try:
        return set(sp.nsimplify(s) for s in sp.solve(poly, fs[0]))
    except Exception:
        return None


def sets_equal(A, B):
    A, B = list(A), list(B)
    if len(A) != len(B):
        return False
    used = set()
    for a in A:
        for j, b in enumerate(B):
            if j not in used and sp.simplify(a - b) == 0:
                used.add(j)
                break
        else:
            return False
    return True


def equations_equivalent(e1, e2):
    p1, p2 = eq_poly(e1), eq_poly(e2)
    if sp.simplify(p1 - p2) == 0 or sp.simplify(p1 + p2) == 0:
        return True
    s1, s2 = solution_set(p1), solution_set(p2)
    if s1 is not None and s2 is not None:
        return sets_equal(s1, s2)
    try:
        ratio = sp.simplify(p1 / p2)
        return bool(ratio.is_number and ratio != 0)
    except Exception:
        return False


def root_set(text):
    """Parse 'x=2, 3' / 'x=2 or x=-4' / 'x = -2 ± √5' / '2 and 3' into a set of sympy numbers."""
    t = normalize(text)
    t = re.sub(r"\b[a-zA-Z]\s*=\s*", "", t)
    parts = [p.strip() for p in re.split(r",|\bor\b|\band\b|;", t) if p.strip()]
    out = []
    for p in parts:
        p = p.rstrip(".")
        if "±" in p:
            a, b = p.split("±", 1)
            A = parse_expr_safe(a) if a.strip() else sp.Integer(0)
            B = parse_expr_safe(b)
            if A is None or B is None:
                return None
            out += [sp.nsimplify(A + B), sp.nsimplify(A - B)]
        else:
            v = parse_expr_safe(p)
            if v is None or not v.is_number:
                return None
            out.append(sp.nsimplify(v))
    uniq = []
    for v in out:
        if not any(sp.simplify(v - u) == 0 for u in uniq):
            uniq.append(v)
    return set(uniq) if uniq else None


_NUM = re.compile(r"-?\d+(?:/\d+)?(?:\.\d+)?")


def numbers_in(text):
    vals = []
    for m in _NUM.findall(normalize(text)):
        try:
            vals.append(Fraction(m))
        except Exception:
            pass
    return vals


def last_number(text):
    n = numbers_in(text)
    return n[-1] if n else None


def extract_equation(question_text):
    """Find the equation embedded in a question sentence."""
    t = normalize(question_text)
    toks = t.replace("?", " ").split()
    ok = re.compile(r"^[0-9a-z\+\-\*/\^\(\)\.=]+$")
    runs, cur = [], []
    for tok in toks:
        tk = tok.rstrip(",.;")
        is_math = bool(ok.match(tk)) and (len(tk) == 1 or re.search(r"[0-9\+\-\*/\^\(\)=]", tk))
        if is_math:
            cur.append(tk)
        else:
            if cur:
                runs.append(cur)
            cur = []
    if cur:
        runs.append(cur)
    for run in runs:
        s = " ".join(run)
        if "=" in s:
            return s
    return None


def poly_coeffs(eq_text):
    eq = parse_equation(eq_text) if eq_text else None
    if not eq:
        return None
    p = eq_poly(eq)
    try:
        P = sp.Poly(p, x)
    except Exception:
        return None
    if P.degree() != 2:
        return None
    a, b, c = P.all_coeffs()
    return a, b, c


def is_fully_factored(expr):
    if expr is None or expr.is_Add:
        return False
    for f in sp.Mul.make_args(expr):
        base = f.base if f.is_Pow else f
        if base.is_Add:
            content, facs = sp.factor_list(base)
            if abs(content) != 1 or len(facs) != 1 or facs[0][1] != 1:
                return False
    return True
