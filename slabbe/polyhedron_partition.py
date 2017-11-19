# -*- coding: utf-8 -*-
r"""
Polyhedron partition and induction

EXAMPLES:

A polyhedron partition::

    sage: from slabbe import PolyhedronPartition
    sage: h = 1/3
    sage: p = Polyhedron([(0,h),(0,1),(h,1)])
    sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
    sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
    sage: s = Polyhedron([(h,0), (1,0), (1,h)])
    sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
    sage: P.is_pairwise_disjoint()
    True
    sage: list(P)
    [(0, A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices),
     (1, A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 4 vertices),
     (2, A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 4 vertices),
     (3, A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices)]
    sage: G = P.plot()

Applying a rationnal rotation::

    sage: from slabbe import rotation_mod
    sage: u = rotation_mod(0, 2/3, 1, QQ)
    sage: Q = P.apply_transformation(u)
    sage: Q
    Polyhedron partition of 4 atoms

Inducing an irrationnal rotation on a subdomain::

    sage: z = polygen(QQ, 'z') #z = QQ['z'].0 # same as
    sage: K = NumberField(z**2-z-1, 'phi', embedding=RR(1.6))
    sage: phi = K.gen()
    sage: h = 1/phi^2
    sage: p = Polyhedron([(0,h),(0,1),(h,1)])
    sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
    sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
    sage: s = Polyhedron([(h,0), (1,0), (1,h)])
    sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s}, base_ring=K)
    sage: u = rotation_mod(0, 1/phi, 1, K)
    sage: u_inv = rotation_mod(0, 1/phi^2, 1, K)
    sage: ieq = [h, -1, 0]   # x0 <= h
    sage: P1,sub01 = P.induced_partition(u, u_inv, ieq)
    sage: P1
    Polyhedron partition of 7 atoms
    sage: sub01
    {0: [0, 2],
     1: [1, 2],
     2: [1, 3],
     3: [0, 2, 2],
     4: [1, 2, 2],
     5: [1, 3, 2],
     6: [1, 3, 3]}

AUTHORS:

- Sébastien Labbé, November 2017, initial version
"""
#*****************************************************************************
#       Copyright (C) 2017 Sébastien Labbé <slabqc@gmail.com>
#
#  Distributed under the terms of the GNU General Public License version 2 (GPLv2)
#
#  The full text of the GPLv2 is available at:
#
#                  http://www.gnu.org/licenses/
#*****************************************************************************
import itertools
from copy import copy
from sage.misc.cachefunc import cached_method
from sage.geometry.polyhedron.constructor import Polyhedron
from sage.plot.graphics import Graphics
from sage.plot.text import text

def rotation_mod(i, angle, mod, base_ring):
    r"""
    Return a rotation function acting on polyhedron.

    INPUT:

    - ``i`` -- integer, coordinate of the rotation
    - ``angle`` -- number, angle of rotation
    - ``mod`` -- number, modulo 
    - ``base_ring`` -- ring, base ring for the vertices of the polyhedron

    OUTPUT:

        a function defined on polyhedron

    EXAMPLES::

        sage: from slabbe import rotation_mod
        sage: z = polygen(QQ, 'z') #z = QQ['z'].0 # same as
        sage: K = NumberField(z**2-z-1, 'phi', embedding=RR(1.6))
        sage: phi = K.gen()
        sage: p = ((-phi + 2, phi - 1), (-phi + 2, 1), (phi - 1, 1))
        sage: p = Polyhedron(p, base_ring=K)

    A rotation modulo phi on the x coordinate::

        sage: t0 = rotation_mod(0, 1, phi, K)
        sage: t0(p).vertices()
        (A vertex at (-phi + 3, phi - 1),
         A vertex at (-phi + 3, 1),
         A vertex at (phi, 1))

    The inverse map::

        sage: t0_inv = rotation_mod(0, 1/phi, phi, K)
        sage: t0(p) == p
        False
        sage: t0_inv(t0(p)) == p
        True

    A rotation modulo 1 on the y coordinate::

        sage: t1 = rotation_mod(1, 1/phi^2, 1, K)
        sage: t1(p).vertices()
        (A vertex at (-phi + 2, 0),
         A vertex at (-phi + 2, -phi + 2),
         A vertex at (phi - 1, -phi + 2))
    """
    def trans(p):
        if all(v[i] <= mod-angle for v in p.vertices()):
            L = [tuple(vj+angle if j==i else vj 
                    for (j,vj) in enumerate(v))
                    for v in p.vertices()]
        else:
            L = [tuple(vj+angle-mod if j==i else vj 
                    for (j,vj) in enumerate(v))
                    for v in p.vertices()]
        return Polyhedron(L, base_ring=base_ring)
    return trans

def find_unused_key(d, sequence):
    r"""
    Return the first key in sequence which is not in d.
    
    EXAMPLES::

        sage: from slabbe.polyhedron_partition import find_unused_key
        sage: d = {3:32, 0:21, 1:4, 5:5}
        sage: find_unused_key(d, NN)
        2
        sage: d[2] = 1234
        sage: find_unused_key(d, NN)
        4
        sage: d[4] = 1234
        sage: find_unused_key(d, NN)
        6
    """
    for a in sequence:
        if a not in d:
            return a

class PolyhedronPartition(object):
    r"""
    Return a partition into polyhedron.

    INPUT:

    - ``atoms`` -- list or dict of polyhedron
    - ``base_ring`` -- base ring (default: ``None``) of the vertices

    EXAMPLES::

        sage: from slabbe import PolyhedronPartition
        sage: h = 1/2
        sage: p = Polyhedron([(0,h),(0,1),(h,1)])
        sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
        sage: r = Polyhedron([(h,0), (1,0), (1,h)])
        sage: P = PolyhedronPartition([p,q,r])
        sage: P
        Polyhedron partition of 3 atoms

    ::

        sage: P.is_pairwise_disjoint()
        True
        sage: P.volume()
        1
        sage: G = P.plot()

    From a dict::

        sage: PolyhedronPartition(dict(a=p,b=q,c=r))
        Polyhedron partition of 3 atoms
    """
    def __init__(self, atoms, base_ring=None):
        r"""
        See class for documentation.

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
        """
        if isinstance(atoms, list):
            self._atoms = dict(enumerate(atoms))
        elif isinstance(atoms, dict):
            self._atoms = atoms
        else:
            raise TypeError('atoms (={}) must be a list or a'
                    ' dict'.format(atoms))
        if base_ring is None:
            if len(self) == 0:
                from sage.rings.integer_ring import ZZ
                base_ring == ZZ
            else:
                base_ring = next(iter(self))[1].base_ring()
        self._base_ring = base_ring

    def __iter__(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: next(iter(P))
            (0,
             A 2-dimensional polyhedron in QQ^2 defined as the convex hull
             of 3 vertices)
        """
        return iter(self._atoms.items())

    def atoms(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.atoms()
            [A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices,
             A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 6 vertices,
             A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices]
        """
        return self._atoms.values()

    def base_ring(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.base_ring()
            Rational Field
        """
        return self._base_ring

    def __getitem__(self, i):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P[0]
            A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices
            sage: P[0].vertices()
            (A vertex at (0, 1), A vertex at (0, 1/2), A vertex at (1/2, 1))
        """
        return self._atoms[i]

    @cached_method
    def cached_atoms_set(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.cached_atoms_set()
            {A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices,
             A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 3 vertices,
             A 2-dimensional polyhedron in QQ^2 defined as the convex hull of 6 vertices}
        """
        return set(self.atoms())

    def __eq__(self, other):
        r"""
        Return whether two partitions are the same.

        The coding is not considered.

        INPUT:

        - ``other`` -- a partition

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: Q = PolyhedronPartition([p,q])
            sage: R = PolyhedronPartition({'asd':q, 'yo':r, 'foo':p})
            sage: P == P
            True
            sage: P == Q
            False
            sage: P == R
            True
        """
        return (isinstance(other, PolyhedronPartition) and
                self.cached_atoms_set() == other.cached_atoms_set())

    def __contains__(self, p):
        r"""
        INPUT:

        - ``p`` -- a polyhedron

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: p in P
            True

        ::

            sage: Q = PolyhedronPartition([p,q])
            sage: r in Q
            False
        """
        return p in self.cached_atoms_set()

    def __len__(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: len(P)
            3
        """
        return len(self._atoms)

    def __repr__(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: PolyhedronPartition([p,q,r])
            Polyhedron partition of 3 atoms
        """
        return "Polyhedron partition of {} atoms".format(len(self))

    def __rmul__(self, factor):
        r"""
        Returns the partition of the induced transformation on the domain.

        INPUT:

        - ``factor`` -- number

        OUTPUT:

            a polyhedron partition

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: 4 * P
            Polyhedron partition of 3 atoms
            sage: -4 * P
            Polyhedron partition of 3 atoms

        TESTS::

            sage: (4.5 * P).base_ring()
            Real Double Field
        """
        return PolyhedronPartition({key:factor*p for (key,p) in self})

    def __neg__(self):
        r"""
        Returns the miror image of the partition.

        OUTPUT:

            a polyhedron partition

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: -P
            Polyhedron partition of 3 atoms
        """
        return PolyhedronPartition({key:-p for (key,p) in self})

    def rename_keys(self, d):
        r"""
        Return a polyhedron partition whose keys are the images under a map.
        
        INPUT:

        - ``d`` -- dict, injective function old key -> new key

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: d = {0:'b', 1:'a', 2:'z'}
            sage: Q = P.rename_keys(d)
            sage: Q
            Polyhedron partition of 3 atoms
            sage: [key for key,p in Q]
            ['a', 'b', 'z']
        """
        if len(set(d.values())) < len(d):
            raise ValueError('input d(={}) is not injective'.format(d))
        return PolyhedronPartition({d[key]:p for (key,p) in self})

    def keys_permutation(self, other):
        r"""
        Return a permutation of the keys for self to look like other.

        INPUT:

        - ``other`` -- a polyhedron partition

        OUTPUT:

            dict, key -> key

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({4:p, 1:q, 2:r})
            sage: Q = PolyhedronPartition({0:p, 5:q})
            sage: d = P.keys_permutation(Q)
            sage: d
            {1: 5, 2: 1, 4: 0}
            sage: P.rename_keys(d)
            Polyhedron partition of 3 atoms
        """
        if not isinstance(other, PolyhedronPartition):
            raise TypeError("other (of type={}) must a polyhedron"
                    " partition".format(type(other)))
        d = {}
        atoms_not_in_other = []
        for self_key,p in self:
            if p in other:
                other_key = other.code(p)
                d[self_key] = other_key
            else:
                atoms_not_in_other.append((self_key,p))
        forbidden_keys = set(other._atoms.keys())
        for self_key,p in atoms_not_in_other:
            new_key = find_unused_key(forbidden_keys, itertools.count())
            d[self_key] = new_key
            forbidden_keys.add(new_key)
        return d

    def translation(self, displacement):
        """
        Return the translated partition of polyhedron.

        INPUT:

        - ``displacement`` -- a displacement vector or a list/tuple of
          coordinates that determines a displacement vector.

        OUTPUT:

        The translated partition.

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.translation((1,1))
            Polyhedron partition of 3 atoms
        """
        return PolyhedronPartition({key:p.translation(displacement) for (key,p) in self})

    def volume(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.volume()
            1

        TESTS::

            sage: PolyhedronPartition([], base_ring=ZZ).volume()
            0
        """
        return sum(p.volume() for p in self.atoms())

    def plot(self):
        r"""
        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.plot()
            Graphics object consisting of 21 graphics primitives
        """
        G = Graphics()
        for i,p in self:
            G += p.plot(fill='white') 
            G += text(i, p.center())
        return G

    def is_pairwise_disjoint(self):
        r"""
        Return whether atoms of the partition are pairwise disjoint.

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition([p,q,r])
            sage: P.is_pairwise_disjoint()
            True
        """
        for (i,j) in itertools.permutations(self._atoms.keys(), 2):
            p = self[i]
            q = self[j]
            volume = p.intersection(q).volume()
            if volume > 0:
                raise ValueError('Intersection of self[{}](={}) and self[{}](={}) is not'
                     ' of zero volume (={})'.format(i, p.vertices(), j,
                         q.vertices(), volume))
        return True

    def merge_atoms(self, d, split_label_function=None):
        r"""
        Return the polyhedron partition obtained by
        merging two atoms having the same image under the dictionnary.

        INPUT:

        - ``d`` -- dict
        - ``split_label_function`` -- function (default:``None``), when two
          atoms have the same image ``V`` under the dictionary, but it is
          impossible to merge them because their convex hull contains more
          than the two, this function is called on the label ``V`` with
          integer argument ``n`` to give a list of ``n`` new labels. When
          ``None`` the default behavior is to use ``Va``, ``Vb``, ``Vc``,
          etc.

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (1,1), (1,h), (h,0)])
            sage: r = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r})
            sage: P.merge_atoms({0:4, 1:4, 2:5})
            Polyhedron partition of 2 atoms
            sage: P.merge_atoms({0:4, 1:5, 2:4})
            Polyhedron partition of 3 atoms
        """
        from collections import defaultdict
        from sage.misc.misc import exists

        if split_label_function is None:
            def split_label_function(V, n):
                AZ = 'abcdefghijklmnopqrstuvwyxzABCDEFGHIJKLMNOPQRSTUVWYXZ'
                return ['{}{}'.format(V, AZ[i]) for i in range(n)]

        def can_merge(t):
            p,q = t
            r = Polyhedron(p.vertices()+q.vertices(), base_ring=p.base_ring())
            return r.volume() == p.volume()+q.volume()

        to_merge = defaultdict(list)
        for key,val in d.items():
            to_merge[val].append(key)

        final_atoms = {}
        for val,keys in to_merge.items():
            atoms = set(self[key] for key in keys)
            answer,t = exists(itertools.permutations(atoms, 2), can_merge)
            while answer:
                p,q = t
                r = Polyhedron(p.vertices()+q.vertices(), base_ring=p.base_ring())
                atoms.remove(p)
                atoms.remove(q)
                atoms.add(r)
                answer,t = exists(itertools.permutations(atoms, 2), can_merge)
            if len(atoms) == 1:
                final_atoms[val] = atoms.pop()
            else:
                new_vals = split_label_function(val, len(atoms))
                for atom,val in zip(atoms,new_vals):
                    final_atoms[val] = atom

        return PolyhedronPartition(final_atoms)

    def apply_transformation(self, trans):
        r"""
        INPUT:

        - ``trans`` -- a function: polyhedron -> polyhedron

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition, rotation_mod
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: u = rotation_mod(0, 2/3, 1, QQ)
            sage: Q = P.apply_transformation(u)
            sage: Q
            Polyhedron partition of 4 atoms

        ::

            sage: u = rotation_mod(0, 2/3, 1, QQ)
            sage: u_inv = rotation_mod(0, 1/3, 1, QQ)
            sage: R = P.apply_transformation(u).apply_transformation(u_inv)
            sage: P == R
            True
        """
        d = {}
        for key,p in self:
            trans_p = trans(p)
            assert p.volume() == trans_p.volume()
            d[key] = trans_p
        return PolyhedronPartition(d)

    def code(self, p):
        r"""
        Returns in which atom the polyhedron lives in.

        INPUT:

        - ``p`` -- a polyhedron

        OUTPUT:

            integer (for the i-th atom)

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: P.code(p)
            0
            sage: P.code(q)
            1
            sage: t = Polyhedron([(0, 8/9), (0, 1), (1/9, 1)])
            sage: P.code(t)
            0

        TESTS::

            sage: t = Polyhedron([(0, 1/9), (0, 1), (1/9, 1)])
            sage: P.code(t)
            Traceback (most recent call last):
            ...
            ValueError: polyhedron p whose vertices are (A vertex at (0,
            1), A vertex at (0, 1/9), A vertex at (1/9, 1)) lies in no atom
        """
        if not hasattr(p, 'vertices'):
            raise TypeError('p (={}) must be a polyhedron'.format(p))
        L = [i for i,atom in self if p <= atom]
        if len(L) == 1:
            return L[0]
        elif len(L) > 1:
            raise ValueError("polyhedron p whose vertices are {} lies "
                    "in more than one atoms (={})".format(p.vertices(), L))
        elif len(L) == 0:
            raise ValueError("polyhedron p whose vertices are {} lies "
                    "in no atom".format(p.vertices()))


    def refine_by_hyperplane(self, ieq):
        r"""
        Refine the partition with the two half spaces of each side of an
        hyperplane.

        INPUT:

        - ``ieq`` -- list, an inequality. An entry equal to "[-1,7,3,4]"
          represents the inequality 7x_1+3x_2+4x_3>= 1.

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq = [-4, 5, 1]
            sage: P.refine_by_hyperplane(ieq)
            Polyhedron partition of 6 atoms
        """
        half = Polyhedron(ieqs=[ieq])
        half_partition = PolyhedronPartition([half])
        other_half = Polyhedron(ieqs=[[-a for a in ieq]])
        other_half_partition = PolyhedronPartition([other_half])
        A = self.refinement(half_partition)
        B = self.refinement(other_half_partition)
        return PolyhedronPartition(A.atoms()+B.atoms())

    def refinement(self, other):
        r"""
        Return the polyhedron partition obtained by the intersection of the
        atoms of self with the atoms of other.

        Only atoms of positive volume are kept.

        INPUT:

        - ``other`` -- a polyhedron partition

        OUTPUT:

            a polyhedron partition

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition, rotation_mod
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: g = 1/5
            sage: t1 = Polyhedron([(g,g), (g,1-g), (1-g,g) ])
            sage: t2 = Polyhedron([(g,1-g), (1-g,g), (1-g,1-g)])
            sage: Q = PolyhedronPartition([t1,t2])
            sage: P.refinement(Q)
            Polyhedron partition of 8 atoms
        """
        if not isinstance(other, PolyhedronPartition):
            raise TypeError("other (of type={}) must a polyhedron"
                    " partition".format(type(other)))
        L = []
        for (p,q) in itertools.product(self.atoms(), other.atoms()):
            p_q = p.intersection(q)
            if p_q.volume() > 0:
                L.append(p_q)
        return PolyhedronPartition(L)
        
    def induced_out_partition(self, trans, ieq):
        r"""
        Returns the output partition obtained as the induction of the given
        transformation on the domain given by an inequality.

        Note: the output partition corresponds to the arrival partition in
        the domain, not the initial one.

        INPUT:

        - ``trans`` -- a function: polyhedron -> polyhedron
        - ``ieq`` -- list, an inequality. An entry equal to "[-1,7,3,4]"
          represents the inequality 7x_1+3x_2+4x_3>= 1.

        OUTPUT:

            dict of polyhedron partitions with keys giving the return time

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition, rotation_mod
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: u = rotation_mod(0, 1/3, 1, QQ)
            sage: ieq = [h, -1, 0]   # x0 <= h
            sage: P.induced_out_partition(u, ieq)
            {3: Polyhedron partition of 4 atoms}

        ::

            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq2 = [1/2, -1, 0]   # x0 <= 1/2
            sage: d = P.induced_out_partition(u, ieq2)
            sage: d
            {1: Polyhedron partition of 2 atoms,
             2: Polyhedron partition of 3 atoms,
             3: Polyhedron partition of 4 atoms}
            sage: Q = PolyhedronPartition(d[1].atoms()+d[2].atoms()+d[3].atoms())
            sage: Q.is_pairwise_disjoint()
            True

        ::

            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq3 = [-1/2, 1, 0]   # x0 >= 1/2
            sage: P.induced_out_partition(u, ieq3)
            {2: Polyhedron partition of 3 atoms, 3: Polyhedron partition of 4 atoms}

        It is an error if the induced region is empty::

            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq4 = [-1/2, -1, 0]   # x0 <= -1/2
            sage: P.induced_out_partition(u, ieq4)
            Traceback (most recent call last):
            ...
            ValueError: Inequality An inequality (-2, 0) x - 1 >= 0 does
            not intersect P (=Polyhedron partition of 4 atoms)

        The whole domain::

            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq5 = [1/2, 1, 0]   # x0 >= -1/2
            sage: P.induced_out_partition(u, ieq5)
            {1: Polyhedron partition of 4 atoms}

        An irrational rotation::

            sage: z = polygen(QQ, 'z') #z = QQ['z'].0 # same as
            sage: K = NumberField(z**2-z-1, 'phi', embedding=RR(1.6))
            sage: phi = K.gen()
            sage: h = 1/phi^2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s}, base_ring=K)
            sage: u = rotation_mod(0, 1/phi, 1, K)
            sage: ieq = [phi^-4, -1, 0]   # x0 <= phi^-4
            sage: d = P.induced_out_partition(u, ieq)
            sage: d
            {5: Polyhedron partition of 6 atoms,
             8: Polyhedron partition of 9 atoms}
        """
        # good side of the hyperplane
        half = Polyhedron(ieqs=[ieq])
        half_part = PolyhedronPartition([half])
        # the other side of the hyperplane
        other_half = Polyhedron(ieqs=[[-a for a in ieq]])
        other_half_part = PolyhedronPartition([other_half])
        # initial refinement
        P = self.refinement(half_part)
        if len(P) == 0:
            raise ValueError("Inequality {} does not intersect P "
                    "(={})".format(half.inequalities()[0], self))
        level = 1
        ans = {}
        P = P.apply_transformation(trans)
        while len(P):
            P_returned = P.refinement(half_part)
            if P_returned:
                ans[level] = P_returned
            # for what is remaining we do:
            P = P.refinement(other_half_part)
            P = P.refinement(self)
            P = P.apply_transformation(trans)
            level += 1
        return ans

    def induced_in_partition(self, trans, trans_inv, ieq):
        r"""
        Returns the partition of the induced transformation on the domain.
        given by an inequality.

        INPUT:

        - ``trans`` -- a function: polyhedron -> polyhedron
        - ``trans_inv`` -- a function: polyhedron -> polyhedron
        - ``ieq`` -- list, an inequality. An entry equal to "[-1,7,3,4]"
          represents the inequality 7x_1+3x_2+4x_3>= 1.

        OUTPUT:

            dict of polyhedron partitions with keys giving the return time

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition, rotation_mod
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: u = rotation_mod(0, 1/3, 1, QQ)
            sage: u_inv = rotation_mod(0, 2/3, 1, QQ)
            sage: ieq = [h, -1, 0]   # x0 <= h
            sage: P.induced_in_partition(u, u_inv, ieq)
            {3: Polyhedron partition of 4 atoms}

        ::

            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq2 = [1/2, -1, 0]   # x0 <= 1/2
            sage: d = P.induced_in_partition(u, u_inv, ieq2)
            sage: d
            {1: Polyhedron partition of 2 atoms,
             2: Polyhedron partition of 3 atoms,
             3: Polyhedron partition of 4 atoms}
        """
        out_partition = self.induced_out_partition(trans, ieq)
        in_partition = {}
        for i,P in out_partition.items():
            for _ in range(i):
                P = P.apply_transformation(trans_inv)
            in_partition[i] = P
        return in_partition

    def induced_partition(self, trans, trans_inv, ieq):
        r"""
        Returns the partition of the induced transformation on the domain.

        INPUT:

        - ``trans`` -- a function: polyhedron -> polyhedron
        - ``trans_inv`` -- a function: polyhedron -> polyhedron
        - ``ieq`` -- a polyhedron

        OUTPUT:

            - a polyhedron partition
            - dict, a substitution

        EXAMPLES::

            sage: from slabbe import PolyhedronPartition, rotation_mod
            sage: h = 1/3
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: u = rotation_mod(0, 1/3, 1, QQ)
            sage: u_inv = rotation_mod(0, 2/3, 1, QQ)
            sage: ieq = [h, -1, 0]   # x0 <= h
            sage: Q,sub = P.induced_partition(u, u_inv, ieq)
            sage: Q
            Polyhedron partition of 4 atoms
            sage: sub
            {0: [0, 2, 2], 1: [1, 2, 2], 2: [1, 2, 3], 3: [1, 3, 3]}

        ::

            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s})
            sage: ieq2 = [1/2, -1, 0]   # x0 <= 1/2
            sage: Q,sub = P.induced_partition(u, u_inv, ieq2)
            sage: Q
            Polyhedron partition of 9 atoms
            sage: sub
            {0: [0],
             1: [1],
             2: [2, 2],
             3: [2, 3],
             4: [3, 3],
             5: [0, 2, 2],
             6: [1, 2, 2],
             7: [1, 2, 3],
             8: [1, 3, 3]}

        Irrationnal rotations::

            sage: z = polygen(QQ, 'z') #z = QQ['z'].0 # same as
            sage: K = NumberField(z**2-z-1, 'phi', embedding=RR(1.6))
            sage: phi = K.gen()
            sage: h = 1/phi^2
            sage: p = Polyhedron([(0,h),(0,1),(h,1)])
            sage: q = Polyhedron([(0,0), (0,h), (h,1), (h,0)])
            sage: r = Polyhedron([(h,1), (1,1), (1,h), (h,0)])
            sage: s = Polyhedron([(h,0), (1,0), (1,h)])
            sage: P = PolyhedronPartition({0:p, 1:q, 2:r, 3:s}, base_ring=K)
            sage: u = rotation_mod(0, 1/phi, 1, K)
            sage: u_inv = rotation_mod(0, 1/phi^2, 1, K)
            sage: ieq = [h, -1, 0]   # x0 <= h
            sage: P1,sub01 = P.induced_partition(u, u_inv, ieq)
            sage: P1
            Polyhedron partition of 7 atoms
            sage: sub01
            {0: [0, 2],
             1: [1, 2],
             2: [1, 3],
             3: [0, 2, 2],
             4: [1, 2, 2],
             5: [1, 3, 2],
             6: [1, 3, 3]}

        We do the induction on a smaller domain::

            sage: ieq2 = [1/phi^3, -1, 0]   # x0 <= h
            sage: P2,sub02 = P.induced_partition(u, u_inv, ieq2)
            sage: P2
            Polyhedron partition of 10 atoms
            sage: sub02
            {0: [0, 2, 2],
             1: [1, 2, 2],
             2: [1, 3, 2],
             3: [1, 3, 3],
             4: [0, 2, 0, 2, 2],
             5: [0, 2, 1, 2, 2],
             6: [1, 2, 1, 2, 2],
             7: [1, 2, 1, 3, 2],
             8: [1, 3, 1, 3, 2],
             9: [1, 3, 1, 3, 3]}
        
        We check that inductions commute::

            sage: u1 = rotation_mod(0, phi^-3, phi^-2, K)
            sage: u1_inv = rotation_mod(0, phi^-4, phi^-2, K)
            sage: P2_alt,sub12 = P1.induced_partition(u1, u1_inv, ieq2)
            sage: P2_alt
            Polyhedron partition of 10 atoms
            sage: P2_alt == P2
            True

        Up to a permutation of the alphabet, ``sub02`` and ``sub01*sub12``
        are equal::

            sage: s01 = WordMorphism(sub01)
            sage: s12 = WordMorphism(sub12)
            sage: s02 = WordMorphism(sub02)
            sage: s02
            WordMorphism: 0->022, 1->122, 2->132, 3->133, 4->02022, 5->02122, 6->12122, 7->12132, 8->13132, 9->13133
            sage: s01*s12 == s02
            True

        By chance, the above is true, but in general, we have::

            sage: perm = WordMorphism(P2.keys_permutation(P2_alt))
            sage: perm
            WordMorphism: 0->0, 1->1, 2->2, 3->3, 4->4, 5->5, 6->6, 7->7, 8->8, 9->9
            sage: s01*s12*perm == s02
            True
        """
        in_partition = self.induced_in_partition(trans, trans_inv, ieq)

        # preprocess the in_partition to recognize atoms which are in self
        # and reuse the same coding letter for them
        d = {}
        return_time_dict = {}
        new_atoms = []
        for return_time,P in in_partition.items():
            for garbage_key,p in P:
                if p in self:
                    key = self.code(p)
                    d[key] = p
                    return_time_dict[key] = return_time
                else:
                    new_atoms.append((return_time,p))
        for return_time,p in new_atoms:
            key = find_unused_key(d, itertools.count())
            d[key] = p
            return_time_dict[key] = return_time

        # construct the return words and substitution
        substitution = {}
        for key,p in d.items():
            return_time = return_time_dict[key]
            p_copy = copy(p)
            w = []
            for _ in range(return_time):
                w.append(self.code(p))
                p = trans(p)
            substitution[key] = w

        return PolyhedronPartition(d), substitution

