from solver import Solver, Unsatisfiable
from hypothesis import given, strategies as st, assume, example, settings
from expression import variable


def test_and_variables():
    solver = Solver()
    x = variable('x')
    y = variable('y')
    assert solver.solve(x & y) == {'x': True, 'y': True}


def test_linear_comparisions():
    solver = Solver()
    x = variable('x')
    y = variable('y')
    t = solver.solve((x + 9 * y) == 10)
    assert t['y'] == t['x'] is True

    s = solver.solve((x + 9 * y) != 10)
    assert not (s['x'] and s['y'])


def test_can_multiply_associatively():
    solver = Solver()
    x = variable('x')
    assert solver.compile((x * 2) * 3 == x * 6) is True


def test_solve_lower_bounds():
    solver = Solver()
    ts = [variable(i) for i in range(10)]
    solver.solve(sum(ts) >= 5)


def test_solve_ordering_between_variables():
    solver = Solver()
    x = variable('x')
    y = variable('y')
    t = solver.solve(x < y)
    assert t['x'] is False
    assert t['y'] is True


@example(ls=[2, 1], m=1)
@given(st.lists(st.integers(), min_size=1), st.integers())
def test_equalities_give_pseudo_boolean_constraints(ls, m):
    solver = Solver()
    variables = [variable(i) for i in range(len(ls))]
    objective = sum(l * v for l, v in zip(ls, variables))
    constraint = solver.compile(objective == m)
    pseudo_boolean = solver.builder.pseudo_boolean_constraint(
        [(l, solver.compile(v)) for l, v in zip(ls, variables)], m, m)
    assert constraint == pseudo_boolean


@example(ls=[2, 1], m=1)
@given(st.lists(st.integers(), min_size=1), st.integers())
def test_lower_bound_gives_pseudo_boolean_constraint(ls, m):
    solver = Solver()
    variables = [variable(i) for i in range(len(ls))]
    objective = sum(l * v for l, v in zip(ls, variables))
    constraint = solver.compile(objective >= m)
    pseudo_boolean = solver.builder.pseudo_boolean_constraint(
        [(l, solver.compile(v)) for l, v in zip(ls, variables)], m,
        sum(map(abs, ls)))
    assert constraint == pseudo_boolean


@example(ls=[2, -3], m=0)
@example(ls=[2, 1], m=1)
@given(st.lists(st.integers(), min_size=1), st.integers())
def test_upper_bound_gives_pseudo_boolean_constraint(ls, m):
    solver = Solver()
    variables = [variable(i) for i in range(len(ls))]
    objective = sum(l * v for l, v in zip(ls, variables))
    constraint = solver.compile(objective <= m)
    pseudo_boolean = solver.builder.pseudo_boolean_constraint(
        [(l, solver.compile(v)) for l, v in zip(ls, variables)],
        -sum(map(abs, ls)), m)
    assert constraint == pseudo_boolean


@example(ls=[2, 1], m=1, n=1)
@given(st.lists(st.integers(), min_size=1), st.integers(), st.integers())
def test_intervals_give_pseudo_boolean_constraints(ls, m, n):
    assume(m <= n)
    solver = Solver()
    variables = [variable(i) for i in range(len(ls))]
    objective = sum(l * v for l, v in zip(ls, variables))
    constraint = solver.compile((objective >= m) & (objective <= n))
    pseudo_boolean = solver.builder.pseudo_boolean_constraint(
        [(l, solver.compile(v)) for l, v in zip(ls, variables)], m, n)
    assert constraint == pseudo_boolean


@example(ls=[-2, 2, 3], m=1, n=1, b=False)
@given(
    st.lists(st.integers().filter(bool), min_size=1),
    st.integers(), st.integers(), st.booleans())
def test_solutions_to_linear_constraints_satisfy_them(ls, m, n, b):
    assume(m <= n)
    solver = Solver()
    objective = sum(
        l * variable(i) for i, l in enumerate(ls)
    )
    constraint = (objective >= m) & (objective <= n)
    try:
        assignment = solver.solve(constraint)
    except Unsatisfiable:
        assume(False)
    for i in range(len(ls)):
        assignment.setdefault(i, b)

    result = objective.evaluate(assignment)
    assert m <= result <= n


@example(ls=[1], m=1, b=False)
@given(
    st.lists(st.integers().filter(bool), min_size=1),
    st.integers(), st.booleans())
def test_solutions_to_one_way_linear_constraints_satisfy_them(ls, m, b):
    solver = Solver()
    objective = sum(
        l * variable(i) for i, l in enumerate(ls)
    )
    constraint = m <= objective
    try:
        assignment = solver.solve(constraint)
    except Unsatisfiable:
        assume(False)

    for i in range(len(ls)):
        assignment.setdefault(i, b)

    assert m <= objective.evaluate(assignment)
