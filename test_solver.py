from solver import Solver, Unsatisfiable
from hypothesis import given, strategies as st, assume, example
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
    print(assignment)
    for i in range(len(ls)):
        assignment.setdefault(i, b)

    result = objective.evaluate(assignment)
    assert m <= result <= n


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
