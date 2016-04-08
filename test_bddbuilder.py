from bddbuilder import BDDBuilder, CNFMapper, BDD
from minisat import minisat
import pytest
from hypothesis import given, strategies as st, assume, example


def test_normalize_and():
    builder = BDDBuilder()
    x = builder.variable(0)
    y = builder.variable(1)
    z = builder.variable(2)

    xyz1 = builder._and(builder._and(x, y), z)
    xyz2 = builder._and(x, builder._and(y, z))
    xyz3 = builder._and(x, y, z)
    assert xyz1 == xyz2
    assert xyz1 == xyz3


def test_single_variable_reduction():
    builder = BDDBuilder()
    x = builder.variable(0)
    assert builder.reduce(x, 0, True) is True
    assert builder.reduce(x, 0, False) is False


def test_and_reduction():
    builder = BDDBuilder()
    x = builder.variable(0)
    y = builder.variable(1)
    xandy = builder._and(x, y)
    assert builder.reduce(xandy, 0, True) is y
    assert builder.reduce(xandy, 1, True) is x


def test_and_is_distinct():
    builder = BDDBuilder()
    x = builder.variable(0)
    y = builder.variable(1)
    assert builder._and(x, y) != x
    assert builder._and(x, y) != y


@pytest.mark.parametrize('i', range(3))
def test_reduce_and(i):
    builder = BDDBuilder()
    x = builder._and(*[builder.variable(i) for i in range(3)])
    assert builder.reduce(x, i, False) is False


def test_unary_pbc():
    builder = BDDBuilder()
    x = builder.variable(0)
    assert builder.pseudo_boolean_constraint([(1, x)], 0, 1) is True
    assert builder.pseudo_boolean_constraint([(2, x)], 0, 1) is builder._not(x)


def test_binary_pbc():
    builder = BDDBuilder()
    x = builder.variable(0)
    y = builder.variable(1)
    xandy = builder.pseudo_boolean_constraint(
        [(1, x), (1, y)], 2, 3
    )
    assert xandy == builder._and(x, y)
    xory = builder.pseudo_boolean_constraint(
        [(1, x), (1, y)], 1, 2
    )
    assert xory == builder._or(x, y)
    z = builder.pseudo_boolean_constraint(
        [(1, x), (1, y)], 0, 1
    )
    assert z == builder._not(builder._and(x, y))


@pytest.mark.parametrize('n', range(1, 10))
def test_simple_pbc(n):
    builder = BDDBuilder()
    ts = [builder.variable(i) for i in range(n)]
    formula = [(1, t) for t in ts]

    assert builder.pseudo_boolean_constraint(formula, 0, n) is True
    assert builder.pseudo_boolean_constraint(formula, 1, n) == builder._or(
        *ts
    )
    assert builder.pseudo_boolean_constraint(
        formula, 0, n - 1) == builder._not(builder._and(*ts))


@example(ls=[2, 1], m=2, n=3)
@given(
    st.lists(st.integers().filter(bool), min_size=1),
    st.integers(), st.integers())
def test_solutions_to_linear_constraints_satisfy_them(ls, m, n):
    assume(m <= n)
    builder = BDDBuilder()
    bdd = builder.pseudo_boolean_constraint(
        [(c, builder.variable(i)) for i, c in enumerate(ls)], m, n
    )
    assume(isinstance(bdd, BDD))
    mapper = CNFMapper()
    termvar = mapper.variable_for_term(bdd)
    cnf = list(mapper.cnf)
    cnf.append((termvar,))
    solution = minisat(cnf)
    assume(solution is not None)
    assignment = {
        v: mapper.remapped_variable(v) in solution
        for v in bdd.variables
    }
    assert bdd.evaluate(assignment)
    score = sum(
        s for i, s in enumerate(ls) if i in bdd.variables and assignment[i]
    )
    assert m <= score <= n


def test_strict_equality_ruling_out_one_variable():
    builder = BDDBuilder()
    v0 = builder.variable(0)
    v1 = builder.variable(1)
    pbc = builder.pseudo_boolean_constraint([(2, v0), (1, v1)], 1, 1)
    assert pbc == builder._and(builder._not(v0), v1)
