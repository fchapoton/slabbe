# -*- coding: utf-8 -*-
r"""
Simultaneous diophantine approximation

EXAMPLES::

    sage: from slabbe.diophantine_approximation import simultaneous_convergents
    sage: it = simultaneous_convergents([e, pi])
    sage: [next(it) for _ in range(10)]          # not tested (60s)
    [(3, 3, 1),                          oui 3
     (19, 22, 7),                        oui 6
     (1843, 2130, 678),                  oui 16
     (51892, 59973, 19090),              non
     (113018, 130618, 41577),            non
     (114861, 132748, 42255),            oui 22
     (166753, 192721, 61345),            non
     (446524, 516060, 164267),           oui 25
     (1174662, 1357589, 432134),         oui 26
     (3970510, 4588827, 1460669)]        oui 28

The relation with multidimensional continued fraction algorithms (the above
first 3 approximations appear in the convergents of ARP algorithm, but not the
4th neither the 5th)::

    sage: algo.n_matrix((e,pi,1), 3)
    [3 3 2]
    [3 4 2]
    [1 1 1]
    sage: algo.n_matrix((e,pi,1), 6)
    [33 19  8]
    [38 22  9]
    [12  7  3]
    sage: algo.n_matrix((e,pi,1), 16)
    [1631 2498 1843]
    [1885 2887 2130]
    [ 600  919  678]
    sage: algo.n_matrix((e,pi,1), 22)
    [114861 101941  64812]
    [132748 117816  74905]
    [ 42255  37502  23843]
    sage: algo.n_matrix((e,pi,1), 25)
    [446524 331663 842999]
    [516060 383312 974277]
    [164267 122012 310122]
    sage: algo.n_matrix((e,pi,1), 26)
    [1621186  331663 1174662]
    [1873649  383312 1357589]
    [ 596401  122012  432134]
    sage: algo.n_matrix((e,pi,1), 28)
    [3970510 2680987 1174662]
    [4588827 3098490 1357589]
    [1460669  986280  432134]

But these vectors could be computed from the precedent ones::

    sage: dirichlet_approx_dependance([e,pi], 8)     # long (1 min 10s)
      i   vi                         lin. rec.     remainder
    +---+--------------------------+-------------+-----------+
      0   (3, 3, 1)                  []            (3, 3, 1)
      1   (19, 22, 7)                [6]           (1, 4, 1)
      2   (1843, 2130, 678)          [96, 6]       (1, 0, 0)
      3   (51892, 59973, 19090)      [28, 15, 1]   (0, 0, 0)
      4   (113018, 130618, 41577)    [2, 5, 1]     (0, 0, 0)
      5   (114861, 132748, 42255)    [1, 0, 1]     (0, 0, 0)
      6   (166753, 192721, 61345)    [1, 0, 1]     (0, 0, 0)
      7   (446524, 516060, 164267)   [2, 0, 1]     (0, 0, 0)

AUTHORS:

- Sébastien Labbé, September 22, 2016
- Sébastien Labbé, October 10, 2016

TODO:

- Move this code to cython and see the speed improvement
- How many of the dirichlet approximations are found by the MCF algos?

"""
#*****************************************************************************
#       Copyright (C) 2016 Sebastien Labbe <slabqc@gmail.com>
#
#  Distributed under the terms of the GNU General Public License (GPL)
#  as published by the Free Software Foundation; either version 2 of
#  the License, or (at your option) any later version.
#                  http://www.gnu.org/licenses/
#*****************************************************************************
from sage.functions.other import floor
from sage.misc.functional import round
from sage.modules.free_module_element import vector

def frac(x):
    r"""
    Return the fractional part of real number x.

    Not always perfect...

    EXAMPLES::

        sage: from slabbe.diophantine_approximation import frac
        sage: frac(3.2)
        0.200000000000000
        sage: frac(-3.2)
        0.800000000000000
        sage: frac(pi)
        pi - 3
        sage: frac(pi).n()
        0.141592653589793

    This looks suspicious...::

        sage: frac(pi*10**15).n()
        0.000000000000000
    """
    return x - floor(x)

def distance_to_nearest_integer(x):
    raise NotImplementedError

def simultaneous_diophantine_approximation(v, Q, start=1, verbose=False):
    r"""
    Return a simultaneous diophantine approximation of vector ``v`` at distance
    ``1/Q``.

    INPUT:

    - ``v`` -- list of real numbers
    - ``Q`` -- real number, Q>1
    - ``start`` -- integer (default: ``1``), starting value to check
    - ``verbose`` -- boolean (default: ``False``)

    OUTPUT:

    - A tuple (u, R) where u=(p_1, ..., p_n, q) is a vector, q is an
      integer, R is a real number such that coordinates of vector p/q are
      at most 1/R from the coordinates of v.

    EXAMPLES::

        sage: from slabbe.diophantine_approximation import simultaneous_diophantine_approximation
        sage: simultaneous_diophantine_approximation([e,pi], 2)
        (3, 3, 1), 3.54964677830384)
        sage: simultaneous_diophantine_approximation([e,pi], 4)
        (19, 22, 7), 35.7490143326079)
        sage: simultaneous_diophantine_approximation([e,pi], 35)
        (19, 22, 7), 35.7490143326079)
        sage: simultaneous_diophantine_approximation([e,pi], 36)
        (1843, 2130, 678), 203.239442934072)
        sage: simultaneous_diophantine_approximation([e,pi], 203)   # long time (1s)
        (1843, 2130, 678), 203.239442934072)

    We can start the next computation at step 678::

        sage: simultaneous_diophantine_approximation([e,pi], 204, start=678) # not tested (25s)
        (51892, 59973, 19090), 266.167750949912)

    TESTS::

        sage: simultaneous_diophantine_approximation([1,e,pi], 1)
        Traceback (most recent call last):
        ...
        ValueError: argument Q(=1) must be > 1
    """
    if not Q > 1:
        raise ValueError("argument Q(={}) must be > 1".format(Q))
    v = vector(v)
    d = len(v)
    Qinv = 1. / Q
    un_moins_Qinv = 1 - Qinv
    for q in range(start, Q**d):
        q_v = q*v
        frac_q_v = map(frac, q_v)
        if verbose:
            print q,[a.n() for a in frac_q_v]
        if all(a <= Qinv or un_moins_Qinv <= a for a in frac_q_v):
            p = map(round, q_v)
            p.append(q)
            error = max((a if a < .5 else 1-a) for a in frac_q_v)
            return vector(p), ~error.n()
    else:
        raise RuntimeError('Did not find diophantine approximation of vector '
                'v={} with parameter Q={}'.format(v, Q))

def simultaneous_convergents(v):  
    r"""
    Return the sequence of convergents to a vector of real number according to
    Dirichlet theorem on simultaneous approximations.

    INPUT:

    - ``v`` -- list of real numbers

    OUTPUT:

    - iterator

    EXAMPLES::

        sage: from slabbe.diophantine_approximation import simultaneous_convergents
        sage: it = simultaneous_convergents([e, pi])
        sage: next(it)
        (3, 3, 1)
        sage: next(it)
        (19, 22, 7)
        sage: next(it)          # long time (1s)
        (1843, 2130, 678)
        sage: next(it)          # not tested (26s)
        (51892, 59973, 19090)
        sage: next(it)          # not tested (30s)
        (113018, 130618, 41577)

    Correspondance with continued fraction when d=1::

        sage: it = simultaneous_convergents([e])
        sage: [next(it) for _ in range(10)]
        [(3, 1),
         (8, 3),
         (11, 4),
         (19, 7),
         (87, 32),
         (106, 39),
         (193, 71),
         (1264, 465),
         (1457, 536),
         (2721, 1001)]
        sage: continued_fraction(e).convergents()[:11].list()
        [2, 3, 8/3, 11/4, 19/7, 87/32, 106/39, 193/71, 1264/465, 1457/536, 2721/1001]
    """
    Q = 2
    start = 1
    while True:
        u,Q = simultaneous_diophantine_approximation(v, Q, start)
        yield u
        Q = floor(Q) + 1
        start = u[-1]

def dirichlet_approx_dependance(v, n, verbose=False):
    r"""
    INPUT:

    - ``v`` -- list of real numbers
    - ``n`` -- integer, number of iterations
    - ``verbose`` -- bool (default: ``False``),

    OUTPUT:

    - table of linear combinaisons of dirichlet approximations in terms of
      previous dirichlet approximations

    EXAMPLES::

        sage: dirichlet_approx_dependance([e,pi], 4)
          i   vi                      lin. rec.     remainder
        +---+-----------------------+-------------+-----------+
          0   (3, 3, 1)               []            (3, 3, 1)
          1   (19, 22, 7)             [6]           (1, 4, 1)
          2   (1843, 2130, 678)       [96, 6]       (1, 0, 0)
          3   (51892, 59973, 19090)   [28, 15, 1]   (0, 0, 0)

    The last 3 seems enough::

        sage: dirichlet_approx_dependance([e,pi], 8)     # long (1 min 10s)
          i   vi                         lin. rec.     remainder
        +---+--------------------------+-------------+-----------+
          0   (3, 3, 1)                  []            (3, 3, 1)
          1   (19, 22, 7)                [6]           (1, 4, 1)
          2   (1843, 2130, 678)          [96, 6]       (1, 0, 0)
          3   (51892, 59973, 19090)      [28, 15, 1]   (0, 0, 0)
          4   (113018, 130618, 41577)    [2, 5, 1]     (0, 0, 0)
          5   (114861, 132748, 42255)    [1, 0, 1]     (0, 0, 0)
          6   (166753, 192721, 61345)    [1, 0, 1]     (0, 0, 0)
          7   (446524, 516060, 164267)   [2, 0, 1]     (0, 0, 0)

    But not in this case::

        sage: dirichlet_approx_dependance([pi,sqrt(3)], 12)   # long (25s)
          i    vi                       lin. rec.            remainder
        +----+------------------------+--------------------+-----------+
          0    (3, 2, 1)                []                   (3, 2, 1)
          1    (22, 12, 7)              [6]                  (4, 0, 1)
          2    (176, 97, 56)            [8, 0]               (0, 1, 0)
          3    (223, 123, 71)           [1, 2, 1]            (0, 0, 0)
          4    (399, 220, 127)          [1, 1]               (0, 0, 0)
          5    (1442, 795, 459)         [3, 1, 0, 1]         (0, 0, 0)
          6    (6390, 3523, 2034)       [4, 1, 1]            (0, 0, 0)
          7    (26603, 14667, 8468)     [4, 0, 2, 1, 0, 1]   (0, 0, 0)
          8    (32993, 18190, 10502)    [1, 1]               (0, 0, 0)
          9    (40825, 22508, 12995)    [1, 0, 1, 1]         (0, 0, 0)
          10   (73818, 40698, 23497)    [1, 1]               (0, 0, 0)
          11   (114643, 63206, 36492)   [1, 1]               (0, 0, 0)

    The v4 is not a lin. comb. of the previous four::

        sage: dirichlet_approx_dependance([e,pi,sqrt(3)], 5)     # long (44s)
          i   vi                                lin. rec.        remainder
        +---+---------------------------------+----------------+--------------+
          0   (3, 3, 2, 1)                      []               (3, 3, 2, 1)
          1   (19, 22, 12, 7)                   [6]              (1, 4, 0, 1)
          2   (193, 223, 123, 71)               [10, 1]          (0, 0, 1, 0)
          3   (5529, 6390, 3523, 2034)          [28, 6, 3]       (2, 5, 1, 1)
          4   (163067, 188461, 103904, 59989)   [29, 14, 1, 1]   (2, 4, 1, 1)
    """
    L = []
    it = simultaneous_convergents(v)
    rows = []
    for i in range(n):
        vi = next(it)
        t = vi
        M = []
        for u in reversed(L):
            m = floor(min(a/b for a,b in zip(t,u)))
            M.append(m)
            t -= m*u
            if t == 0:
                if verbose:
                    c = ','.join("v{}".format(len(L)-j) for j in range(len(M)))
                    print "v{} = {} = <{}>.<{}>".format(i, vi, M, c)
                break
        else:
            if verbose:
                print "v{} = {} = <{}>.<v{}, ..., v0> + {}".format(i, vi, M, i-1, t)
        L.append(vi)
        row = [i, vi, M, t]
        rows.append(row)
    header_row = ['i', 'vi', 'lin. rec.', 'remainder']
    return table(rows=rows, header_row=header_row)

