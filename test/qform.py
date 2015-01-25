from __future__ import division

import sys
import fractions
from fractions import Fraction
import decimal
from decimal import Decimal
from types import NoneType

decimal.getcontext().prec = 50

__all__ = ["qform", "qstr", "output", "prec", "reps", "test"]


def qform(self, preserve = False):
    if hasattr(self, 'qform'):
        return self.qform()

    # form types:
    #        "i", "j", "f" - partial scalar atoms
    #   "S", "s" - scalar expression
    #   "V", "v" - list expression
    #    ^.   ^---- doesn't need brackets
    #     `-------- needs brackets as left argument

    # gathers:
    #   *             -> "s"/"S"
    #   ["i"/"j"/"f"] -> "v"
    #   [*]           -> "v"/"V"

    def encode_vector(forms, types):
        if any([t not in ("i", "j", "f") for t in types]):
            raise Exception()
        q = " ".join(forms)
        if "f" in types:
            if "." not in q and "0n" not in forms:
                q += "."
        elif "j" in types:
            q += "j"
        return q

    def encode_item(f, t):
        if t in ("i", "j", "f"):
            return encode_vector([f], [t])
        return f

    def rational(n):
        if isinstance(n, (int, long)):
            return n, 1
        if isinstance(n, Fraction):
            return n.numerator, n.denominator

    def number_form(n):
        if rational(n):
            p, q = rational(n)
            if q == 1:
                if abs(n) < 2**31-1:
                    return str(n), "i"
                if abs(n) < 2**63-1:
                    return str(n), "j"
            else:
                forms, types = zip(*map(number_form, (p, q)))
                if all([t in ("i", "j") for t in types]):
                    return "%".join(map(encode_item, forms, types)), "S"
            return number_form(p / Decimal(q))

        if isinstance(n, Decimal):
            q = abs(n).log10().quantize(1, rounding=decimal.ROUND_FLOOR)
            q = n.quantize(10 ** (q - 20)).as_tuple()
            l = len(q.digits) + q.exponent
            q = "-" * q.sign + \
                ''.join(map(str, q.digits[:max(0, l)])) + \
                "." + "0" * max(0, -l) + \
                ''.join(map(str, q.digits[max(0, l):]))
            return q.rstrip("0").rstrip("."), "f"

        if n is None:
            return "0n", "f"

        raise Exception()

    def common_denominator(f):
        def lcm(a, b):
            return a * b // fractions.gcd(a, b)

        def find(f, d):
            for e in f:
                if isinstance(e, Fraction):
                    d = lcm(d, e.denominator)
                elif isinstance(e, (list, tuple)):
                    d = find(e, d)
                elif not isinstance(e, (int, long)):
                    raise Exception()
            return d
        d = find(f, 1)

        def extract(f):
            l = []
            for e in f:
                if isinstance(e, (list, tuple)):
                    l.append(extract(e))
                else:
                    n = Fraction(e) * d
                    if n.denominator != 1:
                        raise Exception()
                    l.append(n.numerator)
            return l
        return extract(f), d

    def list_form(self):
        if len(self) == 0:
            return "()", "v"

        if len(self) == 1 or all([e == self[0] for e in self]):
            f, t = value_form(self[0])
            if t in ("v", "V"):
                q = "enlist " + f
            else:
                q = encode_item(f, t)
            if len(self) != 1 or t not in ("v", "V"):
                q = str(len(self)) + "#" + q
            return q, "V"

        forms, types = zip(*map(value_form, self))
        if all([t in ("i", "j", "f") for t in types]):
            return encode_vector(forms, types), "v"

        q = "(%s)" % ";".join(map(encode_item, forms, types))
        if not preserve:
            f, d = common_denominator(self)
            if d != 1:
                f, t = list_form(f)
                if t == "V":
                    f = "(%s)" % f
                cdq = f + "%" + encode_item(*number_form(d))
                if len(cdq) < len(q):
                    return cdq, "V"

        return q, "v"

    def value_form(self):
        if rational(self) or isinstance(self, (Decimal, NoneType)):
            return number_form(self)
        if isinstance(self, (list, tuple)):
            return list_form(self)
        raise Exception()

    return encode_item(*value_form(self))


class qstr:
    def __init__(self, qform):
        self._qform = qform

    def qform(self):
        return self._qform


output_file = None

def output(s):
    (output_file or sys.stdout).write((s + "\n").decode("ascii"))

def prec(prec):
    output("    prec:%s;" % prec)

def reps(reps):
    output("    reps:%d;" % reps)

def test(name, *args, **kwargs):
    args, result = map(qform, args[:-1]), qform(args[-1])

    if "[" in name:
        call = ";%s]" % ";".join(args)
    elif len(args) == 1:
        call = " %s" % args[0]
    else:
        call = "[%s]" % ";".join(args)

    comment = kwargs.get("comment", "")
    if comment:
        comment = " / %s" % comment

    output('    test[".qml.%s%s";"%s"];%s' % (name, call, result, comment))
