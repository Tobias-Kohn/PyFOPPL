#
# (c) 2017, Tobias Kohn
#
# 21. Dec 2017
# 27. Dec 2017
#
from .foppl_ast import *
from .graphs import *
from .foppl_objects import Symbol
from .foppl_parser import parse
from .optimizers import Optimizer

class Scope(object):
    '''
    The scope is basically a stack of dictionaries, implemented as a simply
    linked list of Scope-classes. Functions and other symbols/values are
    stored in distinct dictionaries, and hence also have distinct namespaces.
    '''

    def __init__(self, prev=None):
        self.prev = prev
        self.symbols = {}
        self.functions = {}

    def find(self, name: str):
        if name in self.symbols:
            return self.symbols[name]
        elif self.prev:
            return self.prev.find(name)
        else:
            return None

    def find_function(self, name: str):
        if name in self.functions:
            return self.functions[name]
        elif self.prev:
            return self.prev.find_function(name)
        else:
            return None

    def add_value(self, name: str, value):
        self.symbols[name] = value

    def add_function(self, name: str, value):
        self.functions[name] = value

    @property
    def is_global_scope(self):
        return self.prev is None


class Condition(object):

    def __init__(self, cond, prev=None):
        self.cond = cond
        self.prev = prev

class Compiler(Walker):

    def __init__(self):
        self.__symbol_counter = 20000
        self.scope = Scope()
        self.optimizer = Optimizer(self)
        self.condition = None

    def resolve_symbol(self, name: str):
        return self.scope.find(name)

    def gen_symbol(self, prefix: str):
        self.__symbol_counter += 1
        return "{}{}".format(prefix, self.__symbol_counter)

    def begin_scope(self):
        self.scope = Scope(self.scope)

    def end_scope(self):
        if self.scope.is_global_scope:
            raise RuntimeError("cannot close global scope/namespace")
        self.scope = self.scope.prev

    def begin_condition(self, cond):
        self.condition = Condition(cond, self.condition)

    def end_condition(self):
        if self.condition:
            self.condition = self.condition.prev

    def current_condition(self):
        if self.condition:
            return self.condition.cond
        else:
            return None

    def optimize(self, node: Node):
        if node and self.optimizer:
            return node.walk(self.optimizer)
        return node

    def apply_function(self, function: AstFunction, args: list):
        assert isinstance(function, AstFunction)
        if len(function.params) != len(args):
            raise SyntaxError("wrong number of arguments for '{}'".format(function.name))
        self.begin_scope()
        try:
            for (name, value) in zip(function.params, args):
                if isinstance(name, Symbol):
                    name = name.name
                if isinstance(value, AstFunction):
                    self.scope.add_function(name, value)
                else:
                    self.scope.add_value(name, value.walk(self))
            result = function.body.walk(self)
        finally:
            self.end_scope()
        return result

    def visit_node(self, node: Node):
        raise NotImplementedError(type(node))
        # return Graph.EMPTY, "None"

    def visit_def(self, node: AstDef):
        if self.scope.is_global_scope:
            if isinstance(node.value, AstFunction):
                self.scope.add_function(node.name, node.value)
            else:
                self.scope.add_value(node.name, self.optimize(node.value).walk(self))
            return Graph.EMPTY, "None"
        else:
            raise SyntaxError("'def' must be on the global level")

    def visit_let(self, node: AstLet):
        self.begin_scope()
        try:
            for (name, value) in node.bindings:
                if isinstance(name, Symbol):
                    name = name.name
                if isinstance(value, AstFunction):
                    self.scope.add_function(name, value)
                else:
                    self.scope.add_value(name, self.optimize(value).walk(self))
            result = node.body.walk(self)
        finally:
            self.end_scope()
        return result

    def visit_body(self, node: AstBody):
        result_graph = Graph.EMPTY
        result_expr = "None"
        for item in node.body:
            g, e = item.walk(self)
            result_graph = result_graph.merge(g)
            result_expr = e
        return result_graph, result_expr

    def visit_symbol(self, node: AstSymbol):
        return self.scope.find(node.name)

    def visit_value(self, node: AstValue):
        return Graph.EMPTY, repr(node.value)

    def visit_binary(self, node: AstBinary):
        node = self.optimize(node)
        l_g, l_e = node.left.walk(self)
        r_g, r_e = node.right.walk(self)
        result = "({} {} {})".format(l_e, node.op, r_e)
        return l_g.merge(r_g), result

    def visit_unary(self, node: AstUnary):
        graph, expr = node.item.walk(self)
        return graph, "{}{}".format(node.op, expr)

    def visit_compare(self, node: AstCompare):
        node = self.optimize(node)
        l_g, l_e = node.left.walk(self)
        r_g, r_e = node.right.walk(self)
        result = "({} {} {})".format(l_e, node.op, r_e)
        return l_g.merge(r_g), result

    def visit_if(self, node: AstIf):
        # The optimizer might detect that the condition is static (can be determined at compile time), and
        # return just the if- or else-body, respectively. We only continue with this function if the node
        # is still an if-node after optimization.
        node = self.optimize(node)
        if not isinstance(node, AstIf):
            return node.walk(self)

        cond_name = self.gen_symbol('cond_')
        name = self.gen_symbol('c')

        cond_graph, cond = node.cond.walk(self)
        cur_cond = self.current_condition()
        if cur_cond:
            cond_graph.merge(Graph({cur_cond}, {(cur_cond, cond_name)}))

        self.begin_condition(cond_name)
        if_graph, if_body = node.if_body.walk(self)
        if node.else_body:
            else_graph, else_body = node.else_body.walk(self)
        else:
            else_graph, else_body = Graph.EMPTY, "None"
        self.end_condition()

        expr = "{} if {} else {}".format(if_body, cond_name, else_body)
        graph = cond_graph
        graph = graph.merge(Graph({cond_name}, set((v, cond_name) for v in graph.vertices), {cond_name: cond}))
        graph = graph.merge(if_graph.add_condition(cond_name))
        graph = graph.merge(else_graph.add_condition("not " + cond_name))
        graph = graph.merge(Graph({name}, set((v, name) for v in graph.vertices), {name: expr}))
        return graph, name

    def visit_sample(self, node: AstSample):
        dist = node.distribution
        name = self.gen_symbol('x')
        node.id = name
        graph, expr = dist.walk(self)
        graph = graph.merge(Graph({name}, set((v, name) for v in graph.vertices), {name: expr}))
        cond = self.current_condition()
        if cond:
            graph = graph.merge(Graph({cond}, {(cond, name)}))
        return graph, name

    def visit_observe(self, node: AstObserve):
        dist = node.distribution
        name = self.gen_symbol('y')
        node.id = name
        graph, expr = dist.walk(self)
        _, obs_expr = node.value.walk(self)
        graph = graph.merge(Graph({name}, set((v, name) for v in graph.vertices), {name: expr}, {name: obs_expr}))
        cond = self.current_condition()
        if cond:
            graph = graph.merge(Graph({cond}, {(cond, name)}))
        return graph, name

    def visit_distribution(self, node: AstDistribution):
        return node.repr_with_args(self)

    def visit_vector(self, node: AstVector):
        items = []
        graph = Graph.EMPTY
        for item in node.get_children():
            g, expr = item.walk(self)
            graph = graph.merge(g)
            items.append(expr)
        return graph, "[{}]".format(", ".join(items))

    def visit_functioncall(self, node: AstFunctionCall):
        func = node.function
        if type(func) is str:
            func = self.scope.find_function(func)
        if isinstance(func, AstFunction):
            return self.apply_function(func, node.args)
        else:
            raise SyntaxError("'%s' is not a function".format(node.function))

    def visit_call_get(self, node: AstFunctionCall):
        args = node.args
        if len(args) == 2:
            seq_graph, seq_expr = args[0].walk(self)
            idx_graph, idx_expr = args[1].walk(self)
            return seq_graph.merge(idx_graph), "{}[int({})]".format(seq_expr, idx_expr)
        else:
            raise SyntaxError("'get' expects exactly two arguments")

    def visit_call_rest(self, node: AstFunctionCall):
        args = node.args
        if len(args) == 1:
            graph, expr = args[0].walk(self)
            return graph, "{}[1:]".format(expr)
        else:
            raise SyntaxError("'rest' expects exactly one argument")


def compile(source):
    ast = parse(source)
    compiler = Compiler()
    return compiler.walk(ast)
