"""
Combine two linguistic terms.

a and b are functions of two sets of the same domain.

Since these combinators are used directly in the Set class to implement logic operations,
the most obvious use of this module is when subclassing Set to make use of specific combinators
for special circumstances.

Most functions also SHOULD support an arbitrary  number of arguments so they can be used in
other contexts than just fuzzy sets. HOWEVER, mind that the primary set of arguments always are functors and
there is always only one secondary argument - the value to be evaluated.

## Example

    def bounded_sum(*guncs):
        funcs = list(guncs)

        def op(x, y):
            return x + y - x * y

        def F(z):
            return reduce(op, (f(z) for f in funcs))

        return F

This function is initialized with any number of membership functions ("guncs")
which are then turned into a fixed list and numba.njit-ed in the future.

> f = bounded_sum(R(0, 10), R(5, 15), S(0, 10))

would return the inner F function and prepare everything for operation in an initialization phase.
Now ready for operational phase, when called with a value like `f(5)`,
the inner function applies all specified functions to this value
and combines these membership-values via the inner op function, reducing it all to a single value in [0,1].
"""

from collections.abc import Callable
from functools import reduce

from numpy import multiply

try:
    from numba import njit
except ImportError:

    def njit(func):
        return func


def MIN(*guncs) -> Callable:
    """Classic AND variant."""
    funcs = list(guncs)

    def F(z):
        return min(f(z) for f in funcs)

    return F


def MAX(*guncs):
    """Classic OR variant."""
    funcs = list(guncs)

    def F(z):
        return max(f(z) for f in funcs)

    return F


def product(*guncs):
    """AND variant."""
    funcs = list(guncs)

    def F(z):
        return reduce(multiply, (f(z) for f in funcs))

    return F


def bounded_sum(*guncs):
    """OR variant."""
    funcs = list(guncs)

    def op(x, y):
        return x + y - x * y

    def F(z):
        return reduce(op, (f(z) for f in funcs))

    return F


def lukasiewicz_AND(*guncs):
    """AND variant."""
    funcs = list(guncs)

    def op(x, y):
        return min(1, x + y)

    def F(z):
        return reduce(op, (f(z) for f in funcs))

    return F


def lukasiewicz_OR(*guncs):
    """OR variant."""

    funcs = list(guncs)

    def op(x, y):
        return max(0, x + y - 1)

    def F(z):
        return reduce(op, (f(z) for f in funcs))

    return F


def einstein_product(*guncs):
    """AND variant."""
    funcs = list(guncs)

    def op(x, y):
        return (x * y) / (2 - (x + y - x * y))

    def F(z):
        return reduce(op, (f(z) for f in funcs))

    return F


def einstein_sum(*guncs):
    """OR variant."""
    funcs = list(guncs)

    def op(x, y):
        return (x + y) / (1 + x * y)

    def F(z):
        return reduce(op, (f(z) for f in funcs))

    return F


def hamacher_product(*guncs):
    """AND variant.

    (xy) / (x + y - xy) for x, y != 0
    0 otherwise
    """
    funcs = list(guncs)

    def op(x, y):
        return (x * y) / (x + y - x * y) if x != 0 and y != 0 else 0

    def F(x):
        return reduce(op, (f(x) for f in funcs))

    return F


def hamacher_sum(*guncs):
    """OR variant.

    (x + y - 2xy) / (1 - xy) for x,y != 1
    1 otherwise
    """
    funcs = list(guncs)

    def op(x, y):
        return (x + y - 2 * x * y) / (1 - x * y) if x != 1 or y != 1 else 1

    def F(z):
        return reduce(op, (f(z) for f in funcs))

    return F


def lambda_op(h):
    """A 'compensatoric' operator, combining AND with OR by a weighing factor l.

    This complicates matters a little, since all normal combinators only take functions
    as parameters so we parametrize this with l in a pre-init step.
    """
    assert 0 <= h <= 1, breakpoint()

# sourcery skip: use-function-docstrings
    def E(*guncs):
        funcs = list(guncs)

        def op(x, y):
            return h * (x * y) + (1 - h) * (x + y - x * y)

        def F(z):
            return reduce(op, (f(z) for f in funcs))

        return F

    return E


def gamma_op(g):
    """Combine AND with OR by a weighing factor g.

    This is called a 'compensatoric' operator.

    g (gamma-factor)
        0 < g < 1 (g == 0 -> AND; g == 1 -> OR)

    Same problem as with lambda_op, since all combinators only take functions as arguments,
    so we parametrize this with g in a pre-init step.
    """
    assert 0 <= g <= 1

    def E(*guncs):
        funcs = list(guncs)

        def op(x, y):
            return (x * y) ** (1 - g) * ((1 - x) * (1 - y)) ** g

        def F(z):
            return reduce(op, (f(z) for f in funcs))

        return F

    return E


def simple_disjoint_sum(*guncs):
    """Simple fuzzy XOR operation.
    Someone fancy a math proof?

    Basic idea:
    (A AND ~B) OR (~A AND B)

    >>> xor = simple_disjoint_sum(noop(), noop())
    >>> xor(0)
    0
    >>> xor(1)
    0
    >>> xor(0.5)
    0.5
    >>> xor(0.3) == round(xor(0.7), 2)
    True

    Attempt for expansion without proof:
    x = 0.5
    y = 1
    (x and ~y) or (~x and b)

    max(min(0.5, 0), min(0.5, 1)) == 0.5

    ----

    x = 0
    y = 0.5
    z = 1

    (A AND ~B AND ~C) OR (B AND ~A AND ~C) OR (C AND ~B AND ~A)
    max(min(0,0.5,0), min(0.5,1,0), min(1,0.5,1)) == 0.5
    """

    funcs = list(guncs)

    def F(z):
        # Reminder how it works for 2 args
        # x, y = a(z), b(z)
        # return max(min(x, 1-y), min(1-x, y))

        M = {
            f(z) for f in funcs
        }  # a set of all membership values over all given functions to be iterated over
        # we need to go over each value in the set, calc min(x, inverse(rest)), from that calc max
        # for x in args:
        # print(x, [1-y for y in args-set([x])])

        # FYI: this works because M-set([x]) returns a new set without x, which we use to construct a new set
        # with inverted values - however, if M only has one value,
        # which is the case if all given values are equal - we have to handle an empty generator expression,
        # which the "or (1-x,)" does.
        # Lastly, the *(...) is needed because min only takes one single iterator, so we need to unzip.
        return max(min((x, *({1 - y for y in M - set([x])} or (1 - x,)))) for x in M)

    return F
