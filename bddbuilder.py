from functools import wraps


def canonicalize(value):
    try:
        return tuple(map(canonicalize, value))
    except TypeError:
        return value


def cached(function):
    cache_name = 'cache_for_%s__' % (function.__name__,)

    @wraps(function)
    def accept(self, *args):
        try:
            cache = getattr(self, cache_name)
        except AttributeError:
            cache = {}
            setattr(self, cache_name, cache)
        key = canonicalize(args)
        try:
            return cache[key]
        except KeyError:
            pass
        result = function(self, *args)
        cache[key] = result
        return result
    return accept


class BDDBuilder(object):
    def __init__(self):
        self.__cache = {}
        self.__id_counter = 0

    def variable(self, i):
        return self.bdd(i, True, False)

    def bdd(self, choice, iftrue, iffalse):
        key = ("bdd", choice, iftrue, iffalse)
        try:
            return self.__cache[key]
        except KeyError:
            pass
        reducediftrue = self.reduce(iftrue, choice, True)
        reducediffalse = self.reduce(iffalse, choice, False)
        otherkey = ("bdd", choice, reducediftrue, reducediffalse)
        result = None
        try:
            result = self.__cache[otherkey]
        except KeyError:
            pass
        if result is None:
            if reducediftrue == reducediffalse:
                result = reducediftrue
            else:
                result = BDD(
                    self.__id_counter,
                    choice, reducediftrue, reducediffalse)
        for k in (key, otherkey):
            self.__cache[k] = result
        return result

    def _and(self, *terms):
        if not terms:
            return True
        if len(terms) == 1:
            return terms[0]
        if len(terms) == 2:
            return self.__binand(*terms)

        if False in terms:
            return False

        terms = [t for t in terms if t is not True]
        terms.sort(key=lambda x: (
            len(x.variables), sorted(x.variables), x.number))
        key = ('_and', tuple(terms))
        try:
            return self.__cache[key]
        except KeyError:
            pass
        result = True
        for t in terms:
            result = self.__binand(result, t)
            if result is False:
                break
        self.__cache[key] = result
        return result

    def __binand(self, x, y):
        key = ("_binand", x, y)
        keys = [key]
        try:
            return self.__cache[key]
        except KeyError:
            pass
        if x is False:
            result = False
        elif y is False:
            result = False
        elif x is True:
            result = y
        elif y is True:
            result = x
        else:
            assert isinstance(x, BDD)
            assert isinstance(y, BDD)
            if x is y:
                result = x
            else:
                keys.append(("_binand", y, x))
                if y.number < x.number:
                    x, y = y, x
                if x.choice == y.choice:
                    result = self.bdd(
                        x.choice,
                        self._and(x.iftrue, y.iftrue),
                        self._and(x.iffalse, y.iffalse),
                    )
                else:
                    if y.choice < x.choice:
                        x, y = y, x
                    result = self.bdd(
                        x.choice,
                        self.__binand(x.iftrue, y),
                        self.__binand(x.iffalse, y),
                    )
        for k in keys:
            self.__cache[k] = result
        return result

    @cached
    def pseudo_boolean_constraint(self, formula, lower_bound, upper_bound):
        formula = list(map(tuple, formula))
        if not formula:
            return lower_bound <= 0 <= upper_bound

        add_up = {}
        for c, t in formula:
            add_up[t] = add_up.setdefault(t, 0) + c
        formula = [
            (c, t) for t, c in add_up.items()
        ]

        formula.sort(
            key=lambda ct: (-abs(ct[0]), simplicity(ct[1]))
        )

        normalized = []
        forced = True
        for i in range(len(formula)):
            coefficient, term = formula[i]
            if coefficient == 0:
                continue
            if isinstance(term, bool):
                if term:
                    lower_bound -= coefficient
                    upper_bound -= coefficient
                continue
            elif coefficient < 0:
                coefficient = -coefficient
                term = self._not(term)
                lower_bound += coefficient
                upper_bound += coefficient
            if coefficient > upper_bound:
                forced = self._and(forced, self._not(term))
                if forced is False:
                    return False
            else:
                normalized.append((coefficient, term))
        if not normalized:
            return self._and(
                lower_bound <= 0 <= upper_bound,
                forced
            )
        formula = normalized
        total = sum(c for c, _ in formula)
        if total < lower_bound:
            return False
        if total <= upper_bound and lower_bound <= 0:
            return forced
        if isinstance(forced, BDD):
            normalized = []
            for coefficient, term in formula:
                restricted = self._and(term, forced)
                if simplicity(restricted) < simplicity(term):
                    if isinstance(restricted, bool):
                        if restricted:
                            lower_bound -= coefficient
                            upper_bound -= coefficient
                        continue
                    else:
                        term = restricted
                normalized.append((coefficient, term))
            formula = normalized
        if not normalized:
            return self._and(
                lower_bound <= 0 <= upper_bound,
                forced
            )
        for c, _ in formula:
            assert c > 0

        divide_by = gcd(
            abs(lower_bound), abs(upper_bound), *[c for c, _ in formula])

        assert divide_by >= 1

        if divide_by > 1:
            lower_bound //= divide_by
            upper_bound //= divide_by
            formula = [(c // divide_by, t) for c, t in formula]
        formula.sort(
            key=lambda ct: (-abs(ct[0]), simplicity(ct[1]))
        )
        return self._and(
            forced,
            self.__pbc_normalized_already(
                formula, lower_bound, upper_bound
            )
        )

    @cached
    def __pbc_normalized_already(self, formula, lower_bound, upper_bound):
        coefficient, term = formula[0]
        rest = formula[1:]
        return self.if_then_else(
            term,
            self.pseudo_boolean_constraint(
                rest, lower_bound - coefficient, upper_bound - coefficient),
            self.pseudo_boolean_constraint(
                rest, lower_bound, upper_bound)
        )

    def if_then_else(self, x, y, z):
        return self._or(
            self._and(x, y),
            self._and(self._not(x), z),
        )

    def _or(self, *terms):
        key = ("_or", tuple(terms))
        try:
            return self.__cache[key]
        except KeyError:
            pass
        result = self._not(self._and(*(map(self._not, terms))))
        self.__cache[key] = result
        return result

    def _not(self, x):
        if isinstance(x, bool):
            return not x

        key = ('_not', x)
        try:
            return self.__cache[key]
        except KeyError:
            pass
        result = self.bdd(x.choice, self._not(x.iftrue), self._not(x.iffalse))
        self.__cache[key] = result
        self.__cache[('_not', result)] = x
        return result

    @cached
    def _xor(self, x, y):
        return self._or(
            self._and(self._not(x), y),
            self._and(x, self._not(y)),
        )

    def reduce(self, bdd, variable, value):
        key = ("reduce", bdd, variable, value)
        try:
            return self.__cache[key]
        except KeyError:
            pass
        if isinstance(bdd, bool):
            result = bdd
        elif variable not in bdd.variables:
            result = bdd
        elif variable == bdd.choice:
            if value:
                result = bdd.iftrue
            else:
                result = bdd.iffalse
        else:
            result = self.bdd(
                bdd.choice,
                self.reduce(bdd.iftrue, variable, value),
                self.reduce(bdd.iffalse, variable, value),
            )
        if isinstance(result, BDD):
            assert variable not in result.variables
        self.__cache[key] = result
        return result


class BDD(object):
    def __init__(self, number, choice, iftrue, iffalse):
        self.number = number
        self.choice = choice
        self.iftrue = iftrue
        self.iffalse = iffalse
        variables = set()
        if isinstance(iftrue, BDD):
            assert choice < iftrue.choice
            variables.update(iftrue.variables)
        if isinstance(iffalse, BDD):
            assert choice < iffalse.choice
            variables.update(iffalse.variables)
        assert choice not in variables
        variables.add(choice)
        self.variables = frozenset(variables)

    @property
    def builder(self):
        return self.__builder()

    def __repr__(self):
        return "BDD(%r, %r, %r)" % (self.choice, self.iftrue, self.iffalse)

    def evaluate(self, assignment):
        current = self
        while isinstance(current, BDD):
            if assignment[current.choice]:
                current = current.iftrue
            else:
                current = current.iffalse
        return current


def simplicity(bdd):
    if isinstance(bdd, bool):
        return (0, bdd)
    else:
        return (
            1, len(bdd.variables), sorted(bdd.variables),
            bdd.number,
        )


def gcd(a, *bs):
    for b in bs:
        if a == 1:
            break
        while b != 0:
            t = b
            b = a % b
            a = t
    return a


class CNFMapper(object):
    def __init__(self):
        self.last_variable = 0
        self.cnf = []
        self.variables = set()

    def next_variable(self):
        self.last_variable += 1
        return self.last_variable

    @cached
    def remapped_variable(self, variable):
        assert variable not in self.variables
        self.variables.add(variable)
        result = self.next_variable()
        return result

    @cached
    def false_var(self):
        result = self.next_variable()
        self.cnf.append((-result,))
        return result

    @cached
    def true_var(self):
        result = self.next_variable()
        self.cnf.append((result,))
        return result

    @cached
    def variable_for_term(self, term):
        if term is True:
            return self.true_var()
        if term is False:
            return self.false_var()
        choice_var = self.remapped_variable(term.choice)
        if term.iftrue is True and term.iffalse is False:
            return choice_var
        if term.iftrue is False and term.iffalse is True:
            return -choice_var

        termvar = self.next_variable()
        truetermvar = self.variable_for_term(term.iftrue)
        falsetermvar = self.variable_for_term(term.iffalse)

        # Now we add cnf terms so that termvar = ite(choice_var, truetermvar,
        # falsetermvar).

        # ¬termvar v ite(choice_var, truetermvar, falsetermvar)
        self.cnf.append((-termvar, -choice_var, truetermvar))
        self.cnf.append((-termvar, choice_var, falsetermvar))

        # termvar v ¬ite(choice_var, truetermvar, falsetermvar)
        self.cnf.append((termvar, -choice_var, -truetermvar))
        self.cnf.append((termvar, choice_var, -falsetermvar))
        return termvar
