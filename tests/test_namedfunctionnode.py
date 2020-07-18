import operator
import unittest

import fungraph

def _add_xy(x, y):
    return x + y

class TestNamedFunctionNode(unittest.TestCase):
    def test_constructor(self):
        return fungraph.named("name", lambda: None)

    def test_simple_named_graph(self):
        node = fungraph.named("add", operator.add, 1, 2)
        self.assertEqual(node.compute(), 3)
        self.assertEqual(node.name, "add")
        return

    def test_retrieve_by_name(self):
        node = fungraph.named("add", operator.add,
                              fungraph.named("a", lambda: 1),
                              fungraph.named("b", lambda: 2),
                              )
        a = node["a"]
        b = node["b"]
        self.assertEqual(a.compute(), 1)
        self.assertEqual(b.compute(), 2)
        self.assertEqual(a.name, "a")
        self.assertEqual(b.name, "b")
        return

    def test_retrieve_by_wrong_name_raises_keyerror(self):
        node = fungraph.named("add", operator.add,
                              fungraph.named("a", lambda: 1),
                              fungraph.named("b", lambda: 2),
                              )
        with self.assertRaises(KeyError):
            node["c"]
        return

    def test_mixed_named_unnamed_graph(self):
        node = fungraph.fun(operator.add,
                            fungraph.fun(lambda: 1),
                            fungraph.named("b", lambda: 2),
                            )
        b = node["b"]
        self.assertEqual(node.compute(), 3)
        self.assertEqual(b.compute(), 2)
        self.assertEqual(b.name, "b")
        return

    def test_nameclash_with_named(self):
        node = fungraph.fun(operator.add,
                            fungraph.named("x", lambda: 1),
                            fungraph.named("x", lambda: 2),
                            )
        x = node["x"]
        # return first found result
        self.assertEqual(node.compute(), 3)
        self.assertEqual(x.compute(), 1)
        self.assertEqual(x.name, "x")
        return

    def test_nameclash_with_kwargument(self):
        node = fungraph.fun(_add_xy,
                            x=fungraph.named("y", lambda: 1),
                            y=fungraph.named("x", lambda: 2),
                            )
        x = node["x"]
        # prefer arguments over named
        self.assertEqual(node.compute(), 3)
        self.assertEqual(x.compute(), 1)
        self.assertEqual(x.name, "y")
        return

    def test_nameclash_with_kwargument_explicit(self):
        node = fungraph.fun(_add_xy,
                            x=fungraph.named("y", lambda: 1),
                            y=fungraph.named("x", lambda: 2),
                            )
        x = node[fungraph.Name("x")]
        y = node[fungraph.KeywordArgument("x")]
        # prefer arguments over named
        self.assertEqual(x.compute(), 2)
        self.assertEqual(x.name, "x")
        self.assertEqual(y.compute(), 1)
        self.assertEqual(y.name, "y")
        return

    def test_retrieve_by_path(self):
        node = fungraph.named("add", operator.add,
                              fungraph.named("mul1", operator.mul, fungraph.named("one", lambda: 1), fungraph.named("two", lambda: 2)),
                              fungraph.named("mul2", operator.mul, fungraph.named("three", lambda: 3), fungraph.named("four", lambda: 4)),
                              )
        one = node["mul1/one"]
        two = node["mul1/two"]
        three = node["mul2/three"]
        four = node["mul2/four"]
        self.assertEqual(one.compute(), 1)
        self.assertEqual(two.compute(), 2)
        self.assertEqual(three.compute(), 3)
        self.assertEqual(four.compute(), 4)
        return