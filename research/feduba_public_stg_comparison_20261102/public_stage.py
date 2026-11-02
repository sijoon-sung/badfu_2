"""Execute the pinned author's STG AST, with three CPU ports and an I/O-only optimizer wrapper."""
import ast
import copy


def stage_tree(path):
    tree = ast.parse(path.read_text(encoding='utf-8'))
    fn = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'trigger_generate')
    branch = next(n for n in fn.body if isinstance(n, ast.If) and n.orelse).orelse
    # Exact numeric block: freeze parameters through final noise print. No imported missing helpers.
    body = [n for n in branch if 174 <= n.lineno <= 216]
    assert [n.lineno for n in body] == [174, 177, 178, 180, 181, 182, 183, 214, 215, 216]
    limiter = next(n for n in tree.body if isinstance(n, ast.FunctionDef) and n.name == 'limit_noise')
    original = ast.Module(body=copy.deepcopy(body), type_ignores=[])
    class Port(ast.NodeTransformer):
        cuda_count = 0
        optimizer_count = 0
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'cuda':
                assert not node.args and not node.keywords
                node.func.attr = 'cpu'; self.cuda_count += 1
            elif ast.unparse(node.func) == 'torch.optim.RAdam':
                node.func = ast.Name(id='audited_radam', ctx=ast.Load()); self.optimizer_count += 1
            return node
    port = Port(); adapted = port.visit(copy.deepcopy(original))
    assert port.cuda_count == 3 and port.optimizer_count == 1
    # Prove only declared call substitutions occurred; all original arithmetic and control flow remain.
    class Reverse(ast.NodeTransformer):
        def visit_Call(self, node):
            self.generic_visit(node)
            if isinstance(node.func, ast.Attribute) and node.func.attr == 'cpu' and node.lineno in [180, 188]:
                node.func.attr = 'cuda'
            elif isinstance(node.func, ast.Name) and node.func.id == 'audited_radam':
                node.func = ast.parse('torch.optim.RAdam', mode='eval').body
            return node
    assert ast.dump(Reverse().visit(copy.deepcopy(adapted)), include_attributes=False) == ast.dump(original, include_attributes=False)
    return ast.fix_missing_locations(adapted), ast.fix_missing_locations(ast.Module(body=[limiter], type_ignores=[]))
