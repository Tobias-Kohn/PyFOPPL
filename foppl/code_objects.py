#
# This file is part of PyFOPPL, an implementation of a First Order Probabilistic Programming Language in Python.
#
# License: MIT (see LICENSE.txt)
#
# 16. Jan 2018, Tobias Kohn
# 16. Jan 2018, Tobias Kohn
#
from .code_types import *

class CodeObject(object):

    code_type = AnyType()

##############################################################################

class CodeDistribution(CodeObject):

    def __init__(self, name, args):
        self.name = name
        self.args = args
        self.code_type = DistributionType()

    def __repr__(self):
        return "dist.{}({})".format(self.name, ', '.join([repr(a) for a in self.args]))


class CodeFunctionCall(CodeObject):

    def __init__(self, name, args):
        self.name = name
        self.args = args

    def __repr__(self):
        return "{}({})".format(self.name, ', '.join([repr(a) for a in self.args]))


class CodeValue(CodeObject):

    def __init__(self, value):
        self.value = value
        self.code_type = get_code_type_for_value(value)

    def __repr__(self):
        return repr(self.value)
