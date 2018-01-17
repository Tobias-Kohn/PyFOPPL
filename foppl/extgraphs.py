#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 20. Dec 2017, Tobias Kohn
# 17. Jan 2018, Tobias Kohn
#

_LAMBDA_PATTERN_ = "lambda state: {}"

class GraphNode(object):
    """
    """

    __symbol_counter__ = 30000

    @classmethod
    def __gen_symbol__(cls, prefix:str):
        cls.__base__.__symbol_counter__ += 1
        return "{}{}".format(prefix, cls.__base__.__symbol_counter__)

    def update(self, state: dict):
        result = self.evaluate(state)
        state[self.name] = result
        return result


class ConditionNode(GraphNode):
    """
    Condition
    """

    def __init__(self, *, name:str=None, condition=None, ancestors:set=None, op:str='?', function=None):
        from .code_objects import CodeCompare, CodeValue
        if name is None:
            name = self.__class__.__gen_symbol__('cond_')
        if ancestors is None:
            ancestors = set()
        if function:
            if op == '?':
                op = '>='
            if condition is None:
                condition = CodeCompare(function, op, CodeValue(0))
        self.name = name
        self.ancestors = ancestors
        self.op = op
        self.condition = condition
        self.function = function
        self.code = _LAMBDA_PATTERN_.format(condition.to_py() if condition else "None")
        self.function_code = _LAMBDA_PATTERN_.format(function.to_py() if function else "None")
        self.evaluate = eval(self.code)
        self.evaluate_function = eval(self.function_code)

    def __repr__(self):
        if self.function:
            result = "{f} {o} 0\n\tFunction: {f}".format(f=repr(self.function), o=self.op)
        elif self.condition:
                result = repr(self.condition)
        else:
            result = "???"
        ancestors = ', '.join([v.name for v in self.ancestors])
        return "{}:\n\tAncestors: {}\n\tCondition: {}\n\tCode: {}\n\tFunc-Code: {}".format(self.name, ancestors, result,
                                                                          self.code, self.function_code)

    def update(self, state: dict):
        if self.function:
            f_result = self.evaluate_function(state)
            result = f_result >= 0
            state[self.name + ".function"] = f_result
        else:
            result = self.evaluate(state)
        state[self.name] = result
        return result


class DataNode(GraphNode):
    """
    Data
    """

    def __init__(self, *, name:str=None, data):
        if name is None:
            name = self.__class__.__gen_symbol__('data_')
        self.name = name
        self.data = data
        self.ancestors = set()
        self.code = _LAMBDA_PATTERN_.format(repr(self.data))
        self.evaluate = eval(self.code)

    def __repr__(self):
        return "{} = {}".format(self.name, repr(self.data))


class Parameter(GraphNode):
    """
    A parameter
    """

    def __init__(self, *, name:str=None):
        if name is None:
            name = self.__class__.__gen_symbol__('param_')
        self.name = name
        self.ancestors = set()
        self.code = _LAMBDA_PATTERN_.format(0)
        self.evaluate = eval(self.code)

    def __repr__(self):
        return "{}".format(self.name)


class Vertex(GraphNode):
    """
    A vertex in the graph
    """

    def __init__(self, *, name:str=None, ancestors:set=None, data:set=None, distribution=None, observation=None,
                 ancestor_graph=None, conditions:list=None):
        if name is None:
            name = self.__class__.__gen_symbol__('y' if observation else 'x')
        if ancestor_graph:
            if ancestors:
                ancestors = ancestors.union(ancestor_graph.vertices)
            else:
                ancestors = ancestor_graph.vertices
        if ancestors is None:
            ancestors = set()
        if data is None:
            data = set()
        if conditions is None:
            conditions = []
        self.name = name
        self.ancestors = ancestors
        self.data = data
        self.distribution = distribution
        self.observation = observation
        self.conditions = conditions
        self.distribution_name = distribution.name
        self.code = _LAMBDA_PATTERN_.format(self.distribution.to_py())
        self.evaluate = eval(self.code)

    def __repr__(self):
        result = "{}:\n" \
                 "\tAncestors: {}\n" \
                 "\tDistribution: {}\n".format(self.name,
                                               ', '.join(sorted([v.name for v in self.ancestors])),
                                               repr(self.distribution))
        if len(self.conditions) > 0:
            result += "\tConditions: {}\n".format(', '.join(["{} == {}".format(c.name, v) for c, v in self.conditions]))
        if self.observation:
            result += "\tObservation: {}\n".format(repr(self.observation))
        result += "\tCode: {}\n".format(self.code)
        return result


class Graph(object):
    """
    The graph
    """

    EMPTY = None

    def __init__(self, vertices:set, data:dict=None):
        if data is None:
            data = {}
        self.vertices = vertices
        self.data = data
        arcs = []
        conditions = []
        for v in vertices:
            for a in v.ancestors:
                arcs.append((a, v))
            for c, _ in v.conditions:
                conditions.append(c)
        self.arcs = set(arcs)
        self.conditions = set(conditions)

    def __repr__(self):
        V = "Vertices V:\n  " + '  '.join(sorted([repr(v) for v in self.vertices]))
        if len(self.arcs) > 0:
            A = "Arcs A:\n  " + ', '.join(['({}, {})'.format(u.name, v.name) for (u, v) in self.arcs]) + "\n"
        else:
            A = "Arcs A: -\n"
        if len(self.conditions) > 0:
            C = "Conditions C:\n  " +'\n  '.join(sorted([repr(v) for v in self.conditions])) + "\n"
        else:
            C = "Conditions C: -\n"
        if len(self.data) > 0:
            D = "Data D:\n  " + '\n  '.join(['{}: {}'.format(u, repr(self.data[u].data)) for u in self.data])
        else:
            D = "Data D: -\n"
        return "\n".join([V, A, C, D])

    @property
    def is_empty(self):
        """
        Returns `True` if the graph is empty (contains no vertices).
        """
        return len(self.vertices) == 0

    def merge(self, other):
        """
        Merges this graph with another graph and returns the result. The original graphs are not modified, but
        a new object is instead created and returned.

        :param other: The second graph to merge with the current one.
        :return:      A new graph-object.
        """
        if other:
            return Graph(set.union(self.vertices, other.vertices), data={**self.data, **other.data})
        else:
            return self

Graph.EMPTY = Graph(vertices=set())


def merge(*graphs):
    result = Graph.EMPTY
    for g in graphs:
        result = result.merge(g)
    return result
