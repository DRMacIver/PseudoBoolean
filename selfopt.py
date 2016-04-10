from weakref import WeakKeyDictionary, ref as weakref
from minisat import minisat


class ExpressionOptimizer(object):
    def __init__(self):
        self.__canonicalization_table = WeakKeyDictionary()
        self.__decision_tree = [frozenset(), [FALSE], [TRUE]]

    def variable(self, number):
        return self.canonicalize(Variable(number))

    def _not(self, expression):
        expression = self.canonicalize(expression)
        if expression is TRUE:
            return FALSE
        if expression is FALSE:
            return TRUE
        if isinstance(expression, Not):
            return expression.expression
        return self.canonicalize(Not(expression))

    def _and(self, left, right):
        left = self.canonicalize(left)
        right = self.canonicalize(right)
        if left is FALSE or right is FALSE:
            return FALSE
        if left is TRUE:
            return right
        if right is TRUE:
            return left
        if left is right:
            return left
        return self.canonicalize(And(left, right))

    def equiv(self, left, right):
        x = self.canonicalize(left)
        y = self.canonicalize(right)
        return x.reroot() is y.reroot()

    def canonicalize(self, value):
        value = toterm(value)
        if isinstance(value, _Constant):
            return value
        result = None
        try:
            result = self.__canonicalization_table[value]()
        except KeyError:
            pass
        if result is None:
            if isinstance(value, Variable):
                result = value
            elif isinstance(value, Not):
                child = self.canonicalise(value.expression)
                if isinstance(child, Not):
                    result = child.expression
                elif child is TRUE:
                    result = False
                elif child is FALSE:
                    result = True
                elif child is value.expression:
                    result = value
                else:
                    result = Not(child)
            else:
                assert isinstance(value, And)
                left = self.canonicalize(value.left)
                right = self.canonicalize(value.right)
                if left is value.left and right is value.right:
                    result = value
                elif left is FALSE or right is FALSE:
                    result = FALSE
                elif left is TRUE:
                    result = right
                elif right is TRUE:
                    result = left
                else:
                    result = And(left, right)
        else:
            if result.root is None and not result.canonical:
                # Now the hard part happens
                node = self.__decision_tree
                while len(node) == 3:
                    assignment, iffalse, iftrue = node
                    if value.evaluate(assignment):
                        node = iftrue
                    else:
                        node = iffalse
                assert len(node) == 1
                candidate = node[0]
                assert value != candidate
                experiment = distinguish(candidate, value)
                if experiment is not None:
                    value.canonical = True
                    table = {}
                    valresult = value.evaluate(experiment, table)
                    canresult = candidate.evaluate(experiment, table)
                    assert valresult != canresult
                    node[0] = experiment
                    if valresult:
                        node.append([candidate])
                        node.append([value])
                    else:
                        node.append([value])
                        node.append([candidate])
                else:
                    # Are equivalent
                    if value < candidate:
                        candidate.root = value
                        candidate.canonical = False
                        value.canonical = True
                        node[0] = value
                        self.__canonicalization_table[
                            value] = weakref(value)
                        result = value
                    else:
                        value.root = candidate
                        result = candidate
        result = result.reroot()
        assert result.root is None
        self.__canonicalization_table[value] = weakref(result)
        return result


class Term(object):
    root = None
    canonical = False

    def evaluate(self, assignment, table=None):
        if table is None:
            table = {}
        try:
            return table[self]
        except KeyError:
            pass
        if not assignment or self.minvar > max(assignment):
            result = self.onfalse
        else:
            result = self._evaluate(assignment, table)
        table[self] = result
        return result

    def reroot(self):
        reroot = []
        current = self
        while current.root is not None:
            reroot.append(current)
            current = current.root
            assert current not in reroot
        for r in reroot:
            r.root = current
        return current

    def __le__(self, other):
        return self.cmp(other) <= 0

    def __lt__(self, other):
        return self.cmp(other) < 0

    def __ge__(self, other):
        return self.cmp(other) >= 0

    def __gt__(self, other):
        return self.cmp(other) > 0

    def cmp(self, other):
        return self.cmp_with_table(other, {})

    def cmp_with_table(self, other, table):
        if isinstance(self, _Constant):
            if isinstance(other, _Constant):
                return other.value - self.value
            else:
                return True
        if isinstance(self, Variable):
            if isinstance(other, Variable):
                return other.number - self.number
            else:
                return True
        self.add_to_table(table)
        other.add_to_table(table)
        cs = len(table[self])
        co = len(table[other])
        if cs != co:
            return co - cs
        if isinstance(self, Not):
            if isinstance(other, Not):
                return self.expression.cmp_with_table(other.expression, table)
            else:
                return -1
        assert isinstance(self, And)
        if isinstance(other, And):
            cl = self.left.cmp_with_table(other.left, table)
            if cl != 0:
                return cl
            return self.right.cmp_with_table(other.right, table)

        else:
            return 1


class _Constant(Term):
    canonical = True

    def __init__(self, value):
        self.value = value

    def __repr__(self):
        return repr(self.value).upper()

    @property
    def onfalse(self):
        return self.value

    @property
    def minvar(self):
        return -1

    def _evaluate(self, assignment, table):
        return self.value

    def add_to_table(self, table):
        if self in table:
            return
        table[self] = frozenset()


TRUE = _Constant(True)
FALSE = _Constant(False)


def toterm(value):
    if isinstance(value, bool):
        if value:
            return TRUE
        else:
            return FALSE
    assert isinstance(value, Term)
    return value


class Variable(Term):
    def __init__(self, number):
        assert isinstance(number, int)
        assert number >= 0
        self.number = number

    def __repr__(self):
        return "Variable(%d)" % (self.number,)

    @property
    def onfalse(self):
        return False

    @property
    def minvar(self):
        return self.number

    def __eq__(self, other):
        if self is other:
            return True
        return isinstance(other, Variable) and self.number == other.number

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        return hash(self.number)

    def _evaluate(self, assignment, table):
        return self.number in assignment

    def add_to_table(self, table):
        if self in table:
            return
        table[self] = frozenset()


class Not(Term):
    def __init__(self, expression):
        assert not isinstance(expression, (Not, _Constant))
        self.expression = expression

    def __repr__(self):
        return "Not(%r)" % (self.expression,)

    @property
    def minvar(self):
        return self.expression.minvar

    @property
    def onfalse(self):
        return not self.expression.onfalse

    def _evaluate(self, assignment, table):
        return not self.expression.evaluate(assignment, table)

    def __eq__(self, other):
        if self is other:
            return True
        return isinstance(other, Not) and self.expression == other.expression

    def __ne__(self, other):
        if self is other:
            return True
        return not self.__eq__(other)

    def __hash__(self):
        return ~hash(self.expression)

    def add_to_table(self, table):
        if self in table:
            return
        self.expression.add_to_table(table)
        table[self] = frozenset([self.expression]) | table[self.expression]


class And(Term):
    def __init__(self, left, right):
        for l in (left, right):
            assert not isinstance(l, _Constant)
        assert left != right
        self.left = left
        self.right = right
        self.minvar = min(self.left.minvar, self.right.minvar)
        self.onfalse = self.left.onfalse and self.right.onfalse
        self.__hash = None

    def __repr__(self):
        return "And(%r, %r)" % (self.left, self.right)

    def __eq__(self, other):
        return isinstance(other, And) and self.left == other.left and \
            self.right == other.right

    def __ne__(self, other):
        return not self.__eq__(other)

    def __hash__(self):
        if self.__hash is None:
            self.__hash = hash((self.left, self.right))
        return self.__hash

    def _evaluate(self, assignment, table):
        return self.left.evaluate(assignment, table) and self.right.evaluate(
            assignment, table)

    def add_to_table(self, table):
        if self in table:
            return
        l = self.left
        r = self.right
        l.add_to_table(table)
        r.add_to_table(table)
        table[self] = frozenset({l, r}) | table[l] | table[r]


def distinguish(x, y):
    builder = CNFBuilder()
    xvar = builder.var_for_term(x)
    yvar = builder.var_for_term(y)
    cnf = builder.cnf
    cnf.append((xvar, yvar))
    cnf.append((-xvar, -yvar))
    solution = minisat(cnf)
    if solution is None:
        return None
    assignment = {
        k for k, v in builder.vars_to_vars.items()
        if v in solution
    }
    if x.evaluate(assignment):
        assert xvar in solution
    if y.evaluate(assignment):
        assert yvar in solution
    return assignment


class CNFBuilder(object):
    def __init__(self):
        self.vars_to_vars = {}
        self.cache = {}
        self.lastvar = 0
        self.cnf = []

    def nextvar(self):
        self.lastvar += 1
        return self.lastvar

    def var_for_term(self, term):
        try:
            return self.cache[term]
        except KeyError:
            pass
        if term is FALSE:
            result = -self.var_for_term(TRUE)
        elif term is TRUE:
            result = self.nextvar()
            self.cnf.append((result,))
        else:
            if term.root is not None:
                r = term.reroot()
                assert r != term
                result = self.var_for_term(r)
                self.cache[term] == result
                return result
            if isinstance(term, Not):
                result = -self.var_for_term(term.expression)
            else:
                if isinstance(term, Variable):
                    result = self.nextvar()
                    self.vars_to_vars[term.number] = result
                else:
                    assert isinstance(term, And)
                    leftvar = self.var_for_term(term.left)
                    rightvar = self.var_for_term(term.right)
                    result = self.nextvar()
                    self.cnf.append((
                        leftvar, -result
                    ))
                    self.cnf.append((
                        rightvar, -result
                    ))
                    self.cnf.append((
                        result, -leftvar, -rightvar
                    ))
        self.cache[term] = result
        return result
