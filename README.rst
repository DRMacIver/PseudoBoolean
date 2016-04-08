Solving Pseudo-Boolean Constraints
==================================

Advance warning: You don't want to use this code. It's not really production
ready and `satispy <https://github.com/netom/satispy>`_ is probably the project
more likely to do what you want.

Anyway, this is some code for translating arbitrary boolean formulae into
something a SAT solver can work with. It works by converting them into a
`Binary Decision Diagram <https://en.wikipedia.org/wiki/Binary_decision_diagram>`_
and then translating the relevant bits of the BDD into `Conjunctive Normal Form
<https://en.wikipedia.org/wiki/Conjunctive_normal_form>`_ by introducing a
bunch of auxillary variables.

This code exists for two reasons:

1. I wanted to write it
2. I wanted something which would solve pseudo-boolean constraints (e.g.
   x + y + z >= 2), and it was easier to write my own than to modify satispy to
   support them.

It is probably full of bugs. I've tested bits of it but it isn't even close to
thoroughly tested. I haven't even used Hypothesis on it yet!

Anyway, as such it's in public if you want to look at it, and if you have a use
case for it feel free to talk to me about productionizing it, but you have
been warned.
