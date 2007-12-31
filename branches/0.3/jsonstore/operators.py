import operator
import re


class Operator(object):
    pass


def OperatorFactory(op, func):
    class NewOperator(Operator):
        def __init__(self, value):
            self.value = value
            self.params = [value]

        def __call__(self, item):
            return func(item, self.value)

        def __str__(self):
            return "%s ?" % op

    return NewOperator

Equal = OperatorFactory('=', operator.eq)
NotEqual = OperatorFactory('!=', operator.ne)
GreaterThan = OperatorFactory('>', operator.gt)
LessThan = OperatorFactory('<', operator.lt)
GreaterEqual = OperatorFactory('>=', operator.ge)
LessEqual = OperatorFactory('<=', operator.le)


class Between(Operator):
    def __init__(self, start, end):
        self.start = start
        self.end = end
        self.params = self.start, self.end

    def __call__(self, item):
        return self.start <= item < self.end

    def __str__(self):
        return "BETWEEN ? AND ?"


class In(Operator):
    def __init__(self, *args):
        self.params = args

    def __call__(self, item):
        return item in self.params

    def __str__(self):
        return "IN (%s)" % ','.join('?' for arg in self.params)


class Like(Operator):
    def __init__(self, value):
        self.params = [value]
        # Naive conversion from LIKE syntax to REGEXP; does not account
        # for escaped ``%`` and ``_``.
        pattern = re.escape(value).replace(r'\%', '.*').replace(r'\_', '.')
        self.regexp = re.compile(pattern)

    def __call__(self, item):
        return self.regexp.match(item) is not None

    def __str__(self):
        return "LIKE ?"
    

class RegExp(Operator):
    def __init__(self, value):
        self.params = [value]
        self.regexp = re.compile(value)

    def __call__(self, item):
        return self.regexp.match(item) is not None

    def __str__(self):
        return "REGEXP ?"
