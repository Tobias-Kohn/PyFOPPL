#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 16. Jan 2018, Tobias Kohn
# 16. Jan 2018, Tobias Kohn
#
class AnyType(object):

    def __hash__(self):
        return hash(('$type$', self.__class__.__name__))

    def __repr__(self):
        name = self.__class__.__name__
        if name.endswith("Type"):
            name = name[:-4]
        return "<{}>".format(name)

    def apply_binary(self, op: str, other):
        raise TypeError("incompatible types for operation '{}': '{}' and '{}'".format(op, self, other))

    def union(self, other):
        cls1 = self.__class__
        cls2 = other.__class__
        while cls1 is not AnyType and cls2 is not AnyType:
            if issubclass(cls1, cls2):
                return cls2()
            if issubclass(cls2, cls1):
                return cls1()
            cls1 = cls1.__base__
            cls2 = cls2.__base__
        return AnyType()

class FunctionType(AnyType):
    pass

class SimpleType(AnyType):

    def __new__(cls, *args, **kwargs):
        if hasattr(cls, '__singleton__') and isinstance(cls.__singleton__, cls):
            return cls.__singleton__
        return super(AnyType, cls).__new__(cls, *args)

    def __init__(self):
        self.__class__.__singleton__ = self

class SequenceType(AnyType):

    def __new__(cls, item_type, size, *args, **kwargs):
        if type(size) is not int or size < 0: size = None
        if not isinstance(item_type, AnyType) and issubclass(item_type, AnyType):
            item_type = item_type()
        field = '__{}_singletons__'.format(cls.__name__[:-4])
        if not hasattr(cls, field):
            setattr(cls, field, {})
        singletons = getattr(cls, field)
        if (item_type, size) in singletons:
            return singletons[item_type, size]
        return super(AnyType, cls).__new__(cls, *args)

    def __init__(self, item_type, size: int):
        if type(size) is not int or size < 0: size = None
        if not isinstance(item_type, AnyType) and issubclass(item_type, AnyType):
            item_type = item_type()
        field = '__{}_singletons__'.format(self.__class__.__name__[:-4])
        singletons = getattr(self.__class__, field)
        singletons[item_type, size] = self
        self.item_type = item_type
        self.size = size

    def __repr__(self):
        name = self.__class__.__name__
        if name.endswith("Type"):
            name = name[:-4]
        return "<{}[{}x{}]>".format(name, self.size if self.size else '?', self.item_type)

    def union(self, other):
        if isinstance(other, SequenceType):
            size = self.size if self.size == other.size else None
            item_type = self.item_type.union(other.item_type)
            if self.__class__ is other.__class__:
                return self.__class__(item_type, size)
            else:
                return SequenceType(item_type, size)
        return super(SequenceType, self).union(other)

class TupleType(AnyType):
    pass



class NumericType(SimpleType):

    def apply_binary(self, op: str, other):
        if isinstance(other, NumericType):
            return self.union(other)


class FloatType(NumericType):
    pass

class IntegerType(FloatType):
    pass

class BooleanType(IntegerType):
    pass

class StringType(SimpleType):
    pass

class ListType(SequenceType):

    @staticmethod
    def fromList(types):
        if len(types) > 0:
            for i in range(len(types)):
                if not isinstance(types[i], AnyType) and issubclass(types[i], AnyType):
                    types[i] = types[i]()
            item_type = types[0]
            for t in types[1:]:
                item_type = item_type.union(t)
        else:
            item_type = AnyType()
        return ListType(item_type, len(types))


class DistributionType(AnyType):
    pass



__primitive_types = {
    float: FloatType,
    int: IntegerType,
    str: StringType
}

def get_code_type_for_value(value):
    t = type(value)
    if t in __primitive_types:
        return __primitive_types[t]()
    if type(t) is list:
        return ListType.fromList([get_code_type_for_value(v) for v in value])
    return AnyType()

