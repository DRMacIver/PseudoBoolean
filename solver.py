from minisat import minisat
from bddbuilder import BDDBuilder, CNFMapper
from weakref import ref as weakref


class Solver(object):
    def __init__(self, backend=minisat):
        self.backend = backend
        self.builder = BDDBuilder()
        self.variables_by_name = {}
        self.variables_by_index = []

    def variable(self, name):
        try:
            return self.variables_by_name[name]
        except KeyError:
            pass
        result = Variable(self, name, len(self.variables_by_name))
        self.variables_by_name[name] = result
        self.variables_by_index.append(result)
        assert len(self.variables_by_name) == len(self.variables_by_index)
        return result


class Formula(object):
    def __init__(self, solver):
        self.__solver = weakref(solver)
        self.__bdd = None

    @property
    def solver(self):
        return self.__solver()

    @property
    def builder(self):
        return self.solver.builder

    def __and__(self, other):
        if other is True:
            return self
        if other is False:
            return False
        return And(self, other)

    @property
    def bdd(self):
        if self.__bdd is None:
            self.__bdd = self._calc_bdd()
        return self.__bdd

    def _bracketed(self):
        return "(%s)" % (self.__repr__(),)

    def __invert__(self):
        return Not(self)

    def __mul__(self, other):
        return to_expression(self.solver, self).__mul__(other)

    def __rmul__(self, other):
        return to_expression(self.solver, self).__rmul__(other)

    def __add__(self, other):
        return to_expression(self.solver, self).__add__(other)

    def __radd__(self, other):
        return to_expression(self.solver, self).__radd__(other)

    def __sub__(self, other):
        return to_expression(self.solver, self).__sub__(other)

    def __rsub__(self, other):
        return to_expression(self.solver, self).__rsub__(other)

    def solve(self):
        bdd = self.bdd
        if bdd is True:
            return {}
        if bdd is False:
            raise Unsatisfiable()
        mapper = CNFMapper()
        for v in bdd.variables:
            mapper.remapped_variable(v)
        termvar = mapper.variable_for_term(bdd)
        cnf = list(mapper.cnf)
        cnf.append((termvar,))
        solution = self.solver.backend(cnf)
        if solution is None:
            raise Unsatisfiable()
        relevant_variables = [
            self.solver.variables_by_index[i] for i in bdd.variables]
        return {
            v.name: mapper.remapped_variable(v.index) in solution
            for v in relevant_variables
        }


class Variable(Formula):
    def __init__(self, solver, name, index):
        super(Variable, self).__init__(solver)
        self.name = name
        self.index = index

    def _calc_bdd(self):
        return self.builder.variable(self.index)

    def __repr__(self):
        return "variable(%r)" % (self.name,)

    def _bracketed(self):
        return self.__repr__()

    def __bool__(self):
        return self.bdd is True


class And(Formula):
    def __init__(self, left, right):
        assert left.solver is right.solver
        super(And, self).__init__(left.solver)
        self.left = left
        self.right = right

    def _calc_bdd(self):
        return self.builder._and(self.left.bdd, self.right.bdd)

    def __repr__(self):
        return "%s & %s" % (self.left._bracketed(), self.right._bracketed())


class Not(Formula):
    def __init__(self, base):
        Formula.__init__(self, base.solver)
        self.base = base

    def _calc_bdd(self):
        return self.builder._not(self.base.bdd)

    def __repr__(self):
        return "¬%s" % (self.base.bracketed,)

    def _bracketed(self):
        return self.__repr__()


class IfThenElse(Formula):
    def __init__(self, choice, iftrue, iffalse):
        assert choice.solver == iftrue.solver == iffalse.solver
        super(IfThenElse, self).__init__(choice.solver)
        self.choice = choice
        self.iftrue = iftrue
        self.iffalse = iffalse

    def _calc_bdd(self):
        return self.builder.if_then_else(
            self.choice.bdd, self.iftrue.bdd, self.iffalse.bdd
        )

    def __repr__(self):
        return "if %s then %s else %s" % (
            self.choice._bracketed(), self.iftrue._bracketed(),
            self.iffalse._bracketed()
        )


class LinearConstraint(Formula):
    def __init__(
        self, solver, coefficients_and_terms, lower_bound, upper_bound
    ):
        super(LinearConstraint, self).__init__(solver)
        assert isinstance(lower_bound, int)
        assert isinstance(upper_bound, int)
        self.coefficients_and_terms = tuple(map(tuple, coefficients_and_terms))
        self.lower_bound = lower_bound
        self.upper_bound = upper_bound

    def _calc_bdd(self):
        return self.builder.pseudo_boolean_constraint(
            [(c, t.bdd) for c, t in self.coefficients_and_terms],
            self.lower_bound, self.upper_bound
        )

    def __repr__(self):
        return "%r <= %s <= %r" % (
            self.lower_bound,
            ' + '.join(
                '%s * %s' % (c, t._bracketed())
                for c, t in self.coefficients_and_terms),
            self.upper_bound,
        )


def to_expression(solver, value):
    if isinstance(value, Formula):
        assert value.solver is solver
        return LinearExpression(value.solver, {value: 1}, 0)
    elif isinstance(value, LinearExpression):
        return value
    else:
        assert isinstance(value, int)
        return LinearExpression(solver, {}, value)


class LinearExpression(object):
    def __init__(self, solver, terms_to_coefficients, offset):
        self.solver = solver
        self.offset = offset
        self.terms_to_coefficients = dict(terms_to_coefficients)
        self.upper_bound = sum(
            max(0, v) for v in self.terms_to_coefficients.values()
        )
        self.lower_bound = sum(
            min(0, v) for v in self.terms_to_coefficients.values()
        )

    def __add__(self, other):
        other = to_expression(self.solver, other)
        base = dict(self.terms_to_coefficients)
        for k, v in other.terms_to_coefficients.items():
            base[k] = base.setdefault(k, 0) + v
        return LinearExpression(self.solver, base, self.offset + other.offset)

    def __sub__(self, other):
        return self + (other * -1)

    def __rsub__(self, other):
        return (-1 * other) + self

    def __radd__(self, other):
        return self.__add__(other)

    def __mul__(self, other):
        if not isinstance(other, int):
            raise TypeError("Can only multiple expressions by integers")
        return LinearExpression(self.solver, {
            k: v * other for k, v in self.terms_to_coefficients.items()
        }, self.offset * other)

    def __rmul__(self, other):
        return self.__mul__(other)

    def __eq__(self, other):
        if isinstance(other, int):
            return LinearConstraint(
                self.solver,
                [(c, v) for v, c in self.terms_to_coefficients.items()],
                other, other
            )
        return self - other == 0

    def __ne__(self, other):
        res = self.__eq__(other)
        if isinstance(res, bool):
            return not res
        else:
            return ~res


class Unsatisfiable(Exception):
    pass
