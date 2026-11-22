from . import register
from ..runtimeobjects import parse_value


@register(18)
def load_utd(table, id, _):
    t = ord(table.loader.read(1))
    size = table.loader.read_u32()
    table.loader.stack.push(parse_value(t, table.loader.read(size)))
