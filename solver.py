from minisat import minisat
from bddbuilder import BDDBuilder, CNFMapper
from expression import variable, Binary, is_arithmetic, Unary, Expression


class Solver(object):
    def __init__(self, backend=minisat):
        self.backend = backend
        self.builder = BDDBuilder()
        self.names_to_indices = {}
        self.indices_to_names = []
        self.compile_cache = {}

    def solve(self, variable):
        bdd = self.compile(variable)
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
        solution = self.backend(cnf)
        if solution is None:
            raise Unsatisfiable()
        relevant_variables = [
            (i, self.indices_to_names[i]) for i in bdd.variables]
        return {
            name: mapper.remapped_variable(index) in solution
            for index, name in relevant_variables
        }

    def compile(self, expression):
        if isinstance(expression, bool):
            return expression

        key = id(expression)
        try:
            return self.compile_cache[key]
        except KeyError:
            pass

        bld = self.builder

        if isinstance(expression, variable):
            try:
                i = self.names_to_indices[expression.name],
            except KeyError:
                i = len(self.names_to_indices)
                self.names_to_indices[expression.name] = i
                self.indices_to_names.append(expression.name)
            result = bld.variable(i)
        elif isinstance(expression, Unary):
            assert expression.operator == '~'
            result = bld._not(self.compile(expression.term))
        else:
            assert isinstance(expression, Binary), expression
            op = expression.operator

            if (
                is_arithmetic(expression.left) or
                is_arithmetic(expression.right)
            ):
                left = expression.left
                right = expression.right
                if op in ('==', '!=', '<=', '>=', '<', '>'):
                    if op == '!=':
                        result = bld._or(
                            self.compile(left < right),
                            self.compile(left > right),
                        )
                    else:
                        if isinstance(right, Expression):
                            left -= right
                            right = 0
                        flattened = self.__flatten_arithmetic(left)
                        low = sum(
                            min(0, c) for c, _ in flattened
                        )
                        high = sum(
                            max(0, c) for c, _ in flattened
                        )
                        if op == '==':
                            low = right
                            high = right
                        elif op == '<=':
                            high = right
                        elif op == '>=':
                            low = right
                        elif op == '<':
                            high = right - 1
                        elif op == '>':
                            low = right + 1
                        else:
                            assert False
                        result = bld.pseudo_boolean_constraint(
                            [(c, self.compile(t)) for c, t in flattened],
                            low, high
                        )
                else:
                    for v in (left, right):
                        if is_arithmetic(v):
                            raise ValueError(
                                "Cannot compile arithmetic expression %r" % (
                                    expression
                                ))
                    assert False
            else:
                left = self.compile(expression.left)
                right = self.compile(expression.right)
                if op == '&':
                    result = bld._and(left, right)
                elif op == '|':
                    result = bld._or(left, right)
                elif op in ('^', '!='):
                    result = bld._xor(left, right)
                elif op == '==':
                    result = bld._or(
                        bld._and(left, right),
                        bld._and(left, right),
                    )
                elif op == '<=':
                    result = bld._or(bld._not(left), right)
                elif op == '<':
                    result = bld._and(bld._not(left), right)
                elif op == '>=':
                    result = bld._or(bld._not(right), left)
                elif op == '>':
                    result = bld._and(bld._not(right), left)
                else:
                    assert is_arithmetic(expression)
                    raise ValueError(
                        "Cannot compile arithmetic expression %r" % (
                            expression))
        self.compile_cache[key] = result
        return result

    def __flatten_arithmetic(self, value):
        if not is_arithmetic(value):
            return [(1, value)]
        if isinstance(value, int):
            return [(value, True)]
        elif isinstance(value, Binary):
            if value.operator == '+':
                return self.__flatten_arithmetic(value.left) + \
                    self.__flatten_arithmetic(value.right)
            elif value.operator == '-':
                return self.__flatten_arithmetic(value.left) + [
                    (-c, t) for c, t in
                    self.__flatten_arithmetic(value.right)]
            elif value.operator == '*':
                left = value.left
                right = value.right
                if isinstance(right, int):
                    left, right = right, left
                assert isinstance(left, int)
                assert isinstance(right, Expression)
                return [(left * c, t) for c, t in self.__flatten_arithmetic(
                    right)]
            else:
                assert False
        elif isinstance(value, Unary):
            if value.operator == '+':
                return self.__flatten_arithmetic(value.term)
            elif value.operator == '-':
                return [(-c, t) for c, t in self.__flatten_arithmetic(
                    value.term
                )]
            else:
                assert False


class Unsatisfiable(Exception):
    pass
