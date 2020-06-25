__all__ = ('match', 'case', '_')

from types import FunctionType
from dis import get_instructions
from contextvars import ContextVar
var = ContextVar('match')

class match:
    def __init__(self, value):
        self.value = value

    def __enter__(self):
        self.token = var.set(self.value)

    def __exit__(self, exc_type, exc_value, traceback):
        var.reset(self.token)

def make_cell():
    a : "cell"
    return (lambda: a).__closure__[0]

class Ignore:

    def __eq__(self, other):
        return True

    def __repr__(self):
        return "_"

_ = Ignore()

class Const:
    def __init__(self, value):
        self.value = value

    def __match__(self, other):
        return self.value == other

    def __len__(self):
        return len(self.value)

    def __repr__(self):
        return repr(self.value)

    def __bool__(self):
        return True

    def items(self):
        for k, v in self.value.items():
            yield k, Const(v)

class Var:
    def __init__(self, cell):
        self.cell = cell

    @property
    def value(self):
        return self.cell.cell_contents

    def __match__(self, other):
        if self:
            return self.cell.cell_contents == other
        else:
            self.cell.cell_contents = other
            return True

    def __bool__(self):
        return not is_empty(self.cell)

    def __len__(self):
        return len(self.cell.cell_contents)

    def __repr__(self):
        return repr(self.cell)

    def items(self):
        for k, v in self.value.items():
            yield k, Const(v)

class Tuple:
    def __init__(self, *elems):
        self.elems = elems

    def __match__(self, other):
        if not isinstance(other, tuple):
            return False

        if len(self.elems) != len(other):
            return False

        for e, v in zip(self.elems, other):
            if not e.__match__(v):
                return False
        return True

    def __len__(self):
        return len(self.elems)

    def __repr__(self):
        return repr(self.elems)

class List:
    def __init__(self, *elems):
        self.elems = elems

    def __match__(self, other):
        if not isinstance(other, list):
            return False

        if len(self.elems) != len(other):
            return False

        for e, v in zip(self.elems, other):
            if not e.__match__(v):
                return False
        return True

    def __len__(self):
        return len(self.elems)

    def __repr__(self):
        return repr(self.elems)

class TupleUnpack:
    def __init__(self, *elems):
        var = [e for e in elems if isinstance(e, Var) and not e]
        assert len(var) <= 1
        if len(var) == 1:
            self.var = var[0]
            index = elems.index(self.var)
            self.head = elems[:index]
            self.tail = elems[index+1:]
        else:
            self.head = elems
            self.var = Tuple()
            self.tail = ()

    def __match__(self, other):
        if not isinstance(other, tuple):
            return False

        h = sum(map(len, self.head))
        t = sum(map(len, self.tail))

        if len(other) < h + t:
            return False

        offset = 0
        for e in self.head:
            next_offset = offset + len(e)
            if not e.__match__(other[offset:next_offset]):
                return False
            offset = next_offset

        if not self.var.__match__(other[offset:-t]):
            return False

        offset = -t
        for e in self.tail:
            next_offset = offset + len(e) or None
            if not e.__match__(other[offset:next_offset]):
                return False
            offset = next_offset

        return True


class ListUnpack:
    def __init__(self, *elems):
        elems = [Const(list(e.value)) if isinstance(e, Const) else e for e in elems]
        var = [e for e in elems if isinstance(e, Var) and not e]
        assert len(var) <= 1
        if len(var) == 1:
            self.var = var[0]
            index = elems.index(self.var)
            self.head = elems[:index]
            self.tail = elems[index+1:]
        else:
            self.head = elems
            self.var = List()
            self.tail = ()

    def __match__(self, other):
        if not isinstance(other, list):
            return False

        h = sum(map(len, self.head))
        t = sum(map(len, self.tail))

        if len(other) < h + t:
            return False

        offset = 0
        for e in self.head:
            next_offset = offset + len(e)
            if not e.__match__(other[offset:next_offset]):
                return False
            offset = next_offset

        if not self.var.__match__(other[offset:-t]):
            return False

        offset = -t
        for e in self.tail:
            next_offset = offset + len(e) or None
            if not e.__match__(other[offset:next_offset]):
                return False
            offset = next_offset

        return True


def Set(*elems):
    assert len([e for e in elems if isinstance(e, Var) and not e]) == 0
    return Const({e.value for e in elems})

class _SetUnpack:
    def __init__(self, elems, var):
        self.elems = elems
        self.var = var

    def __match__(self, other):
        return (((self.elems & other) == self.elems) and
                self.var.__match__(other - self.elems))

def SetUnpack(*elems):
    var = [e for e in elems if isinstance(e, Var) and not e]
    assert len(var) <= 1
    if len(var):
        var = var[0]
        index = elems.index(var)
        elems = elems[:index] + elems[index+1:]
        return _SetUnpack({v for e in elems for v in e.value}, var)
    else:
        return Set(*(v for e in elems for v in e.value))

class Map:
    def __init__(self, *elems):
        self.elems = elems

    def __match__(self, other):
        if not isinstance(other, dict):
            return False
        other = dict(other)
        for k, v in self.elems:
            if k not in other:
                return False
            if not v.__match__(other[k]):
                return False
        for k, _ in self.elems:
            del other[k]
        return len(other) == 0

    def items(self):
        return self.elems

class _MapUnpack:
    def __init__(self, elems, var):
        self.elems = elems
        self.var = var

    def __match__(self, other):
        if not isinstance(other, dict):
            return False
        other = dict(other)
        for k, v in self.elems:
            if k not in other:
                return False
            if not v.__match__(other[k]):
                return False
        for k, _ in self.elems:
            del other[k]
        return self.var.__match__(other)

def MapUnpack(*elems):
    var = [e for e in elems if isinstance(e, Var) and not e]
    assert len(var) <= 1
    if len(var):
        var = var[0]
        index = elems.index(var)
        elems = elems[:index] + elems[index+1:]
        return _MapUnpack([(k,v) for e in elems for (k,v) in e.items()], var)
    else:
        return Map(*((k,v) for e in elems for (k,v) in e.items()))

def construct_pattern(pattern):
    stack = []
    for inst in get_instructions(pattern):
        if inst.opname == 'LOAD_CONST':
            stack.append(Const(inst.argval))
        elif inst.opname == 'LOAD_GLOBAL':
            stack.append(Const(pattern.__globals__[inst.argval]))
        elif inst.opname == 'LOAD_DEREF':
            stack.append(Var(pattern.__closure__[inst.arg]))
        elif inst.opname == 'BUILD_TUPLE':
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(Tuple(*elems))
        elif inst.opname in ('BUILD_TUPLE_UNPACK', 'BUILD_TUPLE_UNPACK_WITH_CALL') :
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(TupleUnpack(*elems))
        elif inst.opname == 'BUILD_LIST':
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(List(*elems))
        elif inst.opname == 'BUILD_LIST_UNPACK':
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(ListUnpack(*elems))
        elif inst.opname == 'BUILD_SET':
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(Set(*elems))
        elif inst.opname == 'BUILD_SET_UNPACK':
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(SetUnpack(*elems))
        elif inst.opname == 'BUILD_MAP':
            stack, elems = stack[:-inst.arg*2], stack[-inst.arg*2:]
            elems = [(k.value, v) for k, v in zip(elems[::2], elems[1::2])]
            stack.append(Map(*elems))
        elif inst.opname == 'BUILD_CONST_KEY_MAP':
            stack, elems, top = stack[:-inst.arg-1], stack[-inst.arg-1:-1], stack[-1]
            elems = zip(top.value, elems)
            stack.append(Map(*elems))
        elif inst.opname in ('BUILD_MAP_UNPACK', 'BUILD_MAP_UNPACK_WITH_CALL'):
            stack, elems = stack[:-inst.arg], stack[-inst.arg:]
            stack.append(MapUnpack(*elems))
        elif inst.opname == 'CALL_FUNCTION':
            stack, f, elems = stack[:-inst.arg-1], stack[-inst.arg-1], stack[-inst.arg:]
            stack.append(__case__(f.value, Tuple(*elems)))
        elif inst.opname == 'CALL_FUNCTION_KW':
            stack, f, elems, keys = stack[:-inst.arg-2], stack[-inst.arg-2], stack[-inst.arg-1:-1], stack[-1]
            l = len(keys.value)
            stack.append(__case__(f.value, Tuple(*elems[:-l]), Map(*zip(keys.value, elems[-l:]))))
        elif inst.opname == 'CALL_FUNCTION_EX':
            stack, f, args, kwargs = stack[:-3], stack[-3], stack[-2], stack[-1]
            stack.append(__case__(f.value, args, kwargs))
        elif inst.opname == 'RETURN_VALUE':
            return stack[0]
        else:
            raise NotImplementedError

def is_empty(cell):
    try:
        cell.cell_contents
        return False
    except ValueError:
        return True

def replace_empty_cells(f, replace):
    return FunctionType(
        f.__code__,
        f.__globals__,
        f.__name__,
        f.__defaults__,
        tuple(replace(cell) if is_empty(cell) else cell for cell in f.__closure__ or ()))

def __case__(f, args, kwargs={}):
    if hasattr(f, '__case__'):
        return f.__case__(args, kwargs)
    if isinstance(args, Tuple):
        args = args.elems
    elif isinstance(args, TupleUnpack):
        assert isinstance(args.var, Tuple)
        args = tuple(e for e in args.head for v in e.value)
    elif isinstance(args, Const):
        args = tuple(Const(v) for v in args.value)

    return f(*args, **dict(kwargs.items()))


def case(*patterns, when=None):
    for pattern in patterns:
        closure = pattern.__closure__ or ()
        pattern = replace_empty_cells(pattern, lambda _: make_cell())

        if not construct_pattern(pattern).__match__(var.get()):
            continue

        if when is not None:
            if not replace_empty_cells(when, lambda cell: pattern.__closure__[closure.index(cell)] if cell in closure else cell)():
                continue

        for i, cell in enumerate(closure):
            new_cell = pattern.__closure__[i]
            if cell is new_cell:
                continue
            cell.cell_contents = new_cell.cell_contents
        return True
    return False
