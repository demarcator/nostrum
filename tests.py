from unittest import TestCase
from nostrum import *


class S:
    def __init__(self, *args, **kwargs):
        self.args = args
        self.kwargs = kwargs

    def __match__(self, other):
        from nostrum import Tuple, Map
        args = Tuple(*self.args)
        kwargs = Map(*self.kwargs.items())
        return (isinstance(other, S) and
                args.__match__(other.args) and
                kwargs.__match__(other.kwargs))

class Regex:

    def __init__(self, expr, *args):
        import re
        self.expr = re.compile(expr.value)
        self.args = args

    def __match__(self, other):
        m = self.expr.match(other)
        if not m:
            return False
        for a, v in zip(self.args, m.groups()):
            if not a.__match__(v):
                return False
        return True


class Test(TestCase):

    def test_load_global(self):
        with match(1):
            if case(lambda: _):
                pass
            else:
                self.fail()

    def test_load_const(self):
        with match(1):
            if case(lambda: 1):
                pass
            else:
                self.fail()

        with match(1):
            if case(lambda: 2):
                self.fail()
            else:
                pass

    def test_load_deref(self):
        a : "match"
        with match(0):
            if case(lambda: a, when=lambda: a):
                self.fail()

        with match(1):
            if case(lambda: a):
                self.assertEqual(a, 1)
            else:
                self.fail()

        with match(2):
            if case(lambda: a):
                self.fail()
            else:
                self.assertEqual(a, 1)

    def test_build_tuple(self):
        a: "match"
        b: "match"
        with match((1,2)):
            if case(lambda: (a,a)):
                self.fail()
            elif case(lambda: (a,b)):
                self.assertEqual(a, 1)
                self.assertEqual(b, 2)
            else:
                self.fail()

    def test_build_tuple_unpack(self):
        a: "match"
        b: "match"
        with match((1,)):
            if case(lambda: (1, *a, 3)):
                self.fail()

        with match((1,2,3)):
            if case(lambda: (1, *a, 3)):
                self.assertEqual(a, (2,))
            else:
                self.fail()

        with match((1,2,3)):
            if case(lambda: (1, *a, *b, 3)):
                self.assertEqual(b, ())
            else:
                self.fail()

    def test_build_list(self):
        a: "match"
        b: "match"
        with match([1,2]):
            if case(lambda: [a,a]):
                self.fail()
            elif case(lambda: [a,b]):
                self.assertEqual(a, 1)
                self.assertEqual(b, 2)
            else:
                self.fail()

    def test_build_list_unpack(self):
        a: "match"
        b: "match"
        with match([1]):
            if case(lambda: [1, *a, 3]):
                self.fail()

        with match([1,2,3]):
            if case(lambda: [1, *a, 3]):
                self.assertEqual(a, [2,])
            else:
                self.fail()

        with match([1,2,3]):
            if case(lambda: [1, *a, *b, 3]):
                self.assertEqual(b, [])
            else:
                self.fail()

    def test_build_set(self):
        a = 2
        b = 3
        with match({1,2,3}):
            if case(lambda: {1}):
                self.fail()
            if case(lambda: {1,a,b}):
                pass
            else:
                self.fail()

    def test_build_set_unpack(self):
        a : "match"
        b : "match"
        with match({1}):
            if case(lambda: {1,*a,3}):
                self.fail()

        with match({1,2,3}):
            if case(lambda: {1,*a,3}):
                self.assertEqual(a, {2})
            else:
                self.fail()

        with match({1,2,3}):
            if case(lambda: {1,*a, *b}):
                self.assertEqual(b, {3})
            else:
                self.fail()

    def test_build_map(self):
        a : "match"
        with match({1:2}):
            if case(lambda: {1:3}):
                self.fail()
            elif case(lambda: {1:a}):
                self.assertEqual(a, 2)
            else:
                self.fail()

    def test_build_const_key_map(self):
        a : "match"
        with match({1:2,2:3}):
            if case(lambda: {1:2,2:4}):
                self.fail()
            elif case(lambda: {1:a, 2:a}):
                self.fail()
            elif case(lambda: {1:2, 2:a}):
                self.assertEqual(a, 3)
            else:
                self.fail()

    def test_build_map_unpack(self):
        a : "match"
        b : "match"
        with match({1:2,2:3}):
            if case(lambda: {1:3, **a}):
                self.fail()
            elif case(lambda: {1:2, **a}):
                self.assertEqual(a, {2:3})
            else:
                self.fail()

        with match({1:2,2:3,3:4}):
            if case(lambda: {1:2, **a}):
                self.fail()
            if case(lambda: {1:2, **a, **b}):
                self.assertEqual(b, {3:4})
            else:
                self.fail()


    def test_call_function(self):
        a : "match"
        with match(S(1,2)):
            if case(lambda: S(a,a)):
                self.fail()
            elif case(lambda: S(1,a)):
                self.assertEqual(a,2)
            else:
                self.fail()

    def test_call_function_kw(self):
        a : "match"
        with match(S(1, x=2)):
            if case(lambda: S(a, x=a)):
                self.fail()
            elif case(lambda: S(1,x=a)):
                self.assertEqual(a,2)
            else:
                self.fail()

    def test_call_function_ex(self):
        a = {"a":1}
        b = {"b":1}
        with match(S(1,2,3,a=1,b=1)):
            if case(lambda: S(1,2,3, *a, **a, **b)):
                self.fail()
            elif case(lambda: S(1,2,3, **a, **b)):
                pass
            else:
                self.fail()

    def test_regex(self):
        y : "match"
        m : "match"
        d : "match"
        with match("2020-02-20"):
            if case(lambda: Regex(r"(\d+)-(\d+)-(\d+)", y, m, d)):
                self.assertEqual(y, '2020')
                self.assertEqual(m, '02')
                self.assertEqual(d, '20')
            else:
                self.fail()
