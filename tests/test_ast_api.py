"""The AST is also used as a library to print Apple Events as AppleScript
(e.g. https://github.com/pberba/AEMonitor builds CommandCall/BinaryOp/...
nodes directly and calls `.to_source()`). Keep that usage working."""

from applescript_decompiler.ast import (
    BinaryOp,
    BinaryOpKind,
    CommandCall,
    Keyword,
    ListLiteral,
    NumberLiteral,
    RecordField,
    RecordLiteral,
    StringLiteral,
    VariableRef,
)


def indexed(cls, key, container=None):
    node = BinaryOp(op=BinaryOpKind.GET_INDEXED, left=Keyword(cls), right=key)
    if container is None:
        return node
    return BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=node, right=container)


def test_app_command_with_specifier():
    ref = BinaryOp(
        op=BinaryOpKind.GET_PROPERTY,
        left=Keyword("nmxt"),
        right=indexed("docf", StringLiteral("a.png"), indexed("cfol", StringLiteral("Downloads"), Keyword("sdsk"))),
    )
    src = CommandCall(target=VariableRef(name="Finder"), command_name="coregetd", arguments=[ref]).to_source()
    assert src == '(tell application "Finder" coregetd (name extension of (document file "a.png" of (folder "Downloads" of startup disk))))'


def test_app_name_with_space_is_not_quoted_as_identifier():
    ref = BinaryOp(op=BinaryOpKind.GET_PROPERTY, left=Keyword("pnam"), right=Keyword("pcap"))
    src = CommandCall(target=VariableRef(name="System Events"), command_name="coregetd", arguments=[ref]).to_source()
    assert src == '(tell application "System Events" coregetd (name of application process))'


def test_flat_arguments_records_lists_and_strings():
    args = [
        StringLiteral('say "hi" …'),
        Keyword("btns"),
        ListLiteral([StringLiteral("OK")]),
        Keyword("givu"),
        NumberLiteral(5),
    ]
    src = CommandCall(target=VariableRef(name="osascript"), command_name="sysodlog", arguments=args).to_source()
    assert src == '(tell application "osascript" display dialog "say \\"hi\\" …" buttons {"OK"} giving up after 5)'

    rec = RecordLiteral(fields=[RecordField(label=Keyword("disp"), value=NumberLiteral(1))])
    src = CommandCall(target=VariableRef(name="UNKNOWN"), command_name="aevtoapp", arguments=[rec]).to_source()
    assert src == '(tell application "UNKNOWN" run {disp: 1})'


def test_enum_values_are_stable():
    # values printed in node reprs; existing members keep their numbers
    assert BinaryOpKind.GET_INDEXED.value == 16
    assert BinaryOpKind.GET_PROPERTY.value == 17
    assert BinaryOpKind.OR.value == 22
