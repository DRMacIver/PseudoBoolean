
from tempfile import mkstemp
import os
import subprocess


def minisat(clauses):
    # Returns None if unsatisfiable, else the set of variables that should be
    # assigned True.
    if not clauses:
        return []

    for clause in clauses:
        if 0 in clause:
            raise ValueError("Illegal clause %r" % (clause,))

    n_variables = max(max(abs(c) for c in cs) for cs in clauses)
    n_clauses = len(clauses)

    satfilename = outfilename = None

    try:
        satfd, satfilename = mkstemp(suffix='.sat')
        outfd, outfilename = mkstemp(suffix='.out')
        os.close(outfd)
        satfile = os.fdopen(satfd, mode='w')

        satfile.write(
            'p cnf %d %d\n' % (n_variables, n_clauses)
        )
        for c in clauses:
            satfile.write(
                '%s 0\n' % (' '.join(map(str, c)),)
            )
        satfile.close()
        try:
            subprocess.check_output([
                "minisat", "-mem-lim=500", satfilename, outfilename,
            ])
            return None
        except subprocess.CalledProcessError as e:
            # Due to reasons, apparently an exit code of 10 signifies SAT
            if e.returncode == 20:
                return None
            if e.returncode != 10:
                raise
        with open(outfilename, 'r') as o:
            l1, l2 = o.readlines()
        assert l1.strip() == 'SAT'
        result = list(map(int, l2.strip().split()))
        term = result.pop()
        assert term == 0
        assert 0 not in result
        assert all(abs(i) <= n_variables for i in result)
        return {t for t in result if t > 0}
    finally:
        for f in (satfilename, outfilename):
            if f is not None:
                os.unlink(f)
