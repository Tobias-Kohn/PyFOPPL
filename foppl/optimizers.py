#
# (c) 2017, Tobias Kohn
#
# 24. Dec 2017
# 24. Dec 2017
#
from .foppl_ast import *

class Optimizer(Walker):

    __binary_ops = {
        '+': lambda x, y: x + y,
        '-': lambda x, y: x - y,
        '*': lambda x, y: x * y,
        '/': lambda x, y: x / y
    }

    def __init__(self, compiler=None):
        self.compiler = compiler

    def visit_node(self, node: Node):
        return node

    def visit_binary(self, node: AstBinary):
        left = node.left.walk(self)
        right = node.right.walk(self)
        if isinstance(left, AstValue) and isinstance(right, AstValue):
            if node.op in self.__binary_ops:
                return AstValue(self.__binary_ops[node.op](left.value, right.value))
        return node

    def visit_body(self, node: AstBody):
        items = [n.walk(self) for n in node.body]
        if len(items) == 1:
            return items[0]
        else:
            return AstBody(items)

    def visit_call_get(self, node: AstFunctionCall):
        if len(node.args) == 2:
            vector = node.args[0].walk(self)
            index = node.args[1].walk(self)
            if isinstance(vector, AstValue) and isinstance(index, AstValue):
                return AstValue(vector.value[int(index.value)])
            return AstFunctionCall(node.function, [vector, index])
        return node

    def visit_call_rest(self, node: AstFunctionCall):
        if len(node.args) == 1:
            vector = node.args[0].walk(self)
            if isinstance(vector, AstValue):
                return AstValue(vector.value[1:])
            return AstFunctionCall(node.function, vector)
        return node

    def visit_symbol(self, node: AstSymbol):
        if self.compiler:
            result = self.compiler.resolve_symbol(node.name)
            if result:
                return result
        return node

    def visit_unary(self, node: AstUnary):
        item = node.item.walk(self)
        if node.op == '+':
            return item
        if isinstance(item, AstValue):
            if node.op == '-':
                return AstValue(-item.value)
        elif isinstance(item, AstUnary):
            if item.op == '-' and node.op == '-':
                return item.item
        return node

    def visit_vector(self, node: AstVector):
        children = [child.walk(self) for child in node.get_children()]
        if all(isinstance(child, AstValue) for child in children):
            return AstValue([child.value for child in children])
        return node