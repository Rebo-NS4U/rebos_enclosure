"""Small, read-only helpers for assistant role skills; Python standard library only."""
import argparse
import ast
from decimal import Decimal, localcontext
import json
import platform
import re
import shutil


def calculate(expression):
    if len(expression) > 512:
        raise ValueError('Expression exceeds 512 characters')
    # Decimal literals only: exclude names, calls, powers, subscripts and strings.
    if not re.fullmatch(r'[0-9.\s()+*/-]+', expression):
        raise ValueError('Use decimal literals and + - * / parentheses only')
    tree = ast.parse(expression.strip(), mode='eval')
    if sum(1 for _ in ast.walk(tree)) > 128:
        raise ValueError('Expression is too complex')

    def visit(node):
        if isinstance(node, ast.Constant) and type(node.value) in (int, float):
            return Decimal(ast.get_source_segment(expression.strip(), node))
        if isinstance(node, ast.UnaryOp) and isinstance(node.op, (ast.UAdd, ast.USub)):
            value = visit(node.operand)
            return value if isinstance(node.op, ast.UAdd) else -value
        if isinstance(node, ast.BinOp):
            left, right = visit(node.left), visit(node.right)
            if isinstance(node.op, ast.Add):
                return left + right
            if isinstance(node.op, ast.Sub):
                return left - right
            if isinstance(node.op, ast.Mult):
                return left * right
            if isinstance(node.op, ast.Div):
                return left / right
        raise ValueError('Unsupported arithmetic syntax')

    with localcontext() as context:
        context.prec = 28
        return str(visit(tree.body))


def environment():
    # Deliberately exclude environment variables, hostnames, credentials and logs.
    return {'system': platform.system(), 'release': platform.release(),
            'tools': {name: shutil.which(name) for name in
                      ('bash', 'fish', 'systemctl', 'journalctl', 'niri', 'qs',
                       'qmllint', 'git', 'python3')}}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    sub = parser.add_subparsers(dest='command', required=True)
    sub.add_parser('environment')
    sub.add_parser('calculate').add_argument('expression')
    args = parser.parse_args()
    try:
        result = environment() if args.command == 'environment' else calculate(args.expression)
    except (ValueError, SyntaxError, ArithmeticError, RecursionError) as error:
        parser.exit(2, f'Cannot calculate: {error}\n')
    print(json.dumps(result) if isinstance(result, dict) else result)


if __name__ == '__main__':
    main()
