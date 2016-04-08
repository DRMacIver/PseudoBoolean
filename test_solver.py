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
