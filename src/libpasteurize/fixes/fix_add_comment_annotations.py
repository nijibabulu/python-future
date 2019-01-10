u"""
Fixer to add python 2 comment-style function annotations
"""
from lib2to3 import fixer_base
from lib2to3.pgen2 import token
from lib2to3.fixer_util import Leaf
from lib2to3.fixer_util import syms


def param_without_annotations(node):
    return node.children[0]


def process_value(value):
    if ',' in value:
        return ', '
    else:
        return value


def parse_node(node):
    if node.type == token.NAME:
        return node.value, [u"Any"]
    elif node.type == syms.tname:
        return node.children[0].value, \
               [''.join(process_value(l.value)
                        for l in node.children[-1].leaves())]
    else:
        return "", []


def retrieve_type(node):
    name, type_list = parse_node(node)
    # obey convention: if it is the first argument and is named self or cls,
    # do not annotate the type
    if node.parent.children.index(node) == 0 and (
            name == "self" or name == "cls"):
        return []
    else:
        return type_list


def handle_tname_or_name(node):
    if node.type == syms.tname:
        node.replace(param_without_annotations(node))


def handle_typedargslist(node):
    replace_params = []
    for child in node.children:
        replace_params += retrieve_type(child)
    children = list(node.children)
    for child in children:
        handle_tname_or_name(child)
    return replace_params


class FixAddCommentAnnotations(fixer_base.BaseFix):
    # TODO: add capability to detect variable annotations

    BM_compatible = True

    PATTERN = u"""
              funcdef< 'def' any params=parameters< '(' [any] ')' > ['->' ret=any] ':' body=any >
              """

    def transform(self, node, results):
        u"""
        This replaces function type annotations with a commented version.
        """
        params = results.get(u"params")
        body = results.get(u"body")
        ret = results.get(u"ret")
        if params is not None and body is not None:
            ret_type = u"Any"
            types = []
            for child in params.children:
                if child.type == syms.typedargslist:
                    types = handle_typedargslist(child)
                elif child.type == syms.tname:
                    types = retrieve_type(child)
                    handle_tname_or_name(child)
            if ret is not None:
                assert ret.prev_sibling.type == token.RARROW, u"invalid return annotation"
                ret_type = ret.value
                ret.prev_sibling.remove()
                ret.remove()
            type_sig = "# type: ({}) -> {}".format(", ".join(types), ret_type)
            type_sig_comment = Leaf(token.COMMENT, type_sig)

            # print(len(body))
            indents = [l for l in body.leaves() if l.type == token.INDENT]
            if not len(indents):
                indent_node = Leaf(token.INDENT, "    ")
                body.insert_child(0, indent_node)
                body.insert_child(0, Leaf(token.NEWLINE, "\n"))
            else:
                indent_node = indents[0]
            body.insert_child(0, type_sig_comment)
            body.insert_child(0, indent_node)
            body.insert_child(0, Leaf(token.NEWLINE, "\n"))
