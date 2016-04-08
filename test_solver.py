from solver import Solver


def test_and_variables():
    solver = Solver()
    x = solver.variable('x')
    y = solver.variable('y')
    assert (x & y).solve() == {'x': True, 'y': True}


def test_linear_comparisions():
    solver = Solver()
    x = solver.variable('x')
    y = solver.variable('y')
    t = ((x + 9 * y) == 10).solve()
    assert t['y'] == t['x'] is True

    s = ((x + 9 * y) != 10).solve()
    assert not (s['x'] and s['y'])


def test_can_multiply_associatively():
    solver = Solver()
    x = solver.variable('x')
    assert ((x * 2) * 3 == x * 6).bdd is True


def test_equivalence_of_subtraction_and_negation():
    solver = Solver()
    x = solver.variable('x')
    assert (1 - x) == ~x == -1 * x + 1


def test_solve_lower_bounds():
    solver = Solver()
    ts = [solver.variable(i) for i in range(10)]
    (sum(ts) >= 5).solve()


def test_solve_ordering_between_variables():
    solver = Solver()
    x = solver.variable('x')
    y = solver.variable('y')
    t = (x < y).solve()
    assert t['x'] is False
    assert t['y'] is True
