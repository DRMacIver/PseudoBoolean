from selfopt import ExpressionOptimizer


def test_associativity_of_and():
    opt = ExpressionOptimizer()
    x = opt.variable(0)
    y = opt.variable(1)
    z = opt.variable(2)

    x_yz = opt._and(x, opt._and(y, z))
    xy_z = opt._and(opt._and(x, y), z)
    assert opt.equiv(x_yz, xy_z)
