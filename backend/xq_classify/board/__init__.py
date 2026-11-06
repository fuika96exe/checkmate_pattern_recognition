"""Public board interface: FEN parsing, legal moves, checks, attacks and square helpers.

Filled in phase 0 step 2 from the lab's pure-Python move generator.  Callers
outside the package use only the names exported here, never private helpers.
The active move generator is pure Python by default; another implementation
of the ``MoveGenerator`` protocol (the lab's pyffish adapter, for parity
tests) can be swapped in with ``use_backend``.
"""
