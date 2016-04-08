class Expression(object):
    arithmetic = False

    def __bracketed__(self):
        return "(%s)" % (repr(self),)

    def __eq__(self, other):
        return Binary('==', self, other)

    def __ne__(self, other):
        return Binary('!=', self, other)

    def __le__(self, other):
        return Binary('<=', self, other)

    def __lt__(self, other):
        return Binary('<', self, other)

    def __ge__(self, other):
        return Binary('>=', self, other)

    def __gt__(self, other):
        return Binary('>', self, other)

    def __add__(self, other):
        return Binary('+', self, other)

    def __radd__(self, other):
        return Binary('+', other, self)

    def __sub__(self, other):
        return Binary('-', self, other)

    def __rsub__(self, other):
        return Binary('-', other, self)

    def __mul__(self, other):
        return Binary('*', self, other)

    def __rmul__(self, other):
        return Binary('*', other, self)

    def __and__(self, other):
        return Binary('&', self, other)

    def __rand__(self, other):
        return Binary('&', other, self)

    def __or__(self, other):
        return Binary('|', self, other)

    def __ror__(self, other):
        return Binary('|', other, self)

    def __xor__(self, other):
        return Binary('^', self, other)

    def __rxor__(self, other):
        return Binary('^', other, self)

    def __neg__(self):
        return Unary('-', self)

    def __pos__(self):
        return Unary('+', self)

    def __invert__(self):
        return Unary('~', self)

    def evaluate(self, assignment, table=None):
        if table is None:
            table = {}
        try:
            return table[id(self)]
        except KeyError:
            pass
        result = self._evaluate(assignment, table)
        table[id(self)] = result
        return result


class variable(Expression):
    def __init__(self, name):
        self.name = name

    def __repr__(self):
        return 'variable(%s)' % (repr(self.name),)

    def __bracketed__(self):
        return self.__repr__()

    def _evaluate(self, assignment, table):
        return assignment[self.name]


def is_arithmetic(value):
    if isinstance(value, Expression):
        return value.arithmetic
    if isinstance(value, bool):
        return False
    return True


def bracketed_repr(value):
    if isinstance(value, Expression):
        return value.__bracketed__()
    else:
        return repr(value)


def evaluate(value, assignment, table):
    if isinstance(value, Expression):
        return value.evaluate(assignment, table)
    else:
        return value


class Binary(Expression):
    def __init__(self, operator, left, right):
        for v in (left, right):
            if not isinstance(v, (int, Expression)):
                raise TypeError("Unsupported value %r of type %s" % (
                    v, type(v).__name__,
                ))
            if is_arithmetic(v) and operator in ('&', '|', '^'):
                raise ValueError((
                    "Boolean operators not supported on arithmetic "
                    "expression %r") % (v,))
        if operator == '*' and isinstance(left, Expression) and isinstance(
            right, Expression
        ):
            raise ValueError("Cannot multiply two expressions together")
        self.left = left
        self.right = right
        self.operator = operator

    def _evaluate(self, assignment, table):
        lv = evaluate(self.left, assignment, table)
        rv = evaluate(self.left, assignment, table)
        if self.operator == '+':
            return lv + rv
        elif self.operator == '-':
            return lv - rv
        elif self.operator == '*':
            return lv * rv
        elif self.operator == '^':
            return lv ^ rv
        elif self.operator == '&':
            return lv & rv
        elif self.operator == '|':
            return lv | rv
        elif self.operator == '==':
            return lv == rv
        elif self.operator == '!=':
            return lv != rv
        elif self.operator == '<':
            return lv < rv
        elif self.operator == '>':
            return lv > rv
        elif self.operator == '<=':
            return lv <= rv
        elif self.operator == '>=':
            return lv >= rv
        else:
            assert False

    @property
    def arithmetic(self):
        return self.operator in (
            '+', '*', '-'
        )

    def __repr__(self):
        return "%s %s %s" % (
            bracketed_repr(self.left), self.operator,
            bracketed_repr(self.right))


class Unary(Expression):
    def __init__(self, operator, term):
        self.operator = operator
        self.term = term
        if is_arithmetic(term) and operator == '~':
            raise ValueError(
                "Cannot perform logical negation on expression %r" % (term,))

    @property
    def arithmetic(self):
        return self.operator != '~'

    def __repr__(self):
        return "%s%s" % (self.operator, bracketed_repr(self.term))

    def __bracketed__(self):
        return self.__repr__()

    def _evaluate(self, assignment, table):
        base = self.term.evaluate(self.term)
        if self.operator == '-':
            return -base
        elif self.operator == '~':
            return not base
        elif self.operator == '+':
            return +base
