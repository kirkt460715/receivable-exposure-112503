"""读取和核对业务资料包的表头、主键与引用。"""

import argparse
import json
from pathlib import Path


class BundleError(ValueError):
    """资料包结构不符合发布方的格式。"""


def load_bundle(directory):
    """返回各来源表的原始行，保留空值和来源顺序。"""
    directory = Path(directory)
    contract = json.loads((directory / 'contract.json').read_text(encoding='utf-8'))
    content = {}
    for table, spec in contract['tables'].items():
        rows = []
        keys = set()
        with (directory / (table + '.jsonl')).open(encoding='utf-8') as stream:
            for number, line in enumerate(stream, 1):
                try:
                    row = json.loads(line)
                except json.JSONDecodeError as error:
                    raise BundleError(f'{table} 第 {number} 行不是 JSON 对象') from error
                if not isinstance(row, dict) or row.keys() != spec['columns'].keys():
                    raise BundleError(f'{table} 第 {number} 行字段与字典不一致')
                key = tuple(row[field] for field in spec['key'])
                if any(not isinstance(value, (str, int)) or isinstance(value, bool) or value == '' for value in key):
                    raise BundleError(f'{table} 第 {number} 行主键为空或格式无效')
                if key in keys:
                    raise BundleError(f'{table} 第 {number} 行主键重复')
                keys.add(key)
                rows.append(row)
        content[table] = rows

    for table, spec in contract['tables'].items():
        for field, reference in spec['refs'].items():
            target, target_field = reference.split('.')
            index = {row[target_field] for row in content[target]}
            for number, row in enumerate(content[table], 1):
                value = row[field]
                if value is not None and value not in index:
                    raise BundleError(f'{table} 第 {number} 行引用 {field} 无对应记录')
    return content


def main():
    parser = argparse.ArgumentParser(description='核对资料包的输入格式和来源表行数')
    parser.add_argument('directory', type=Path, help='包含资料字典和各来源表的目录')
    args = parser.parse_args()
    try:
        content = load_bundle(args.directory)
    except (OSError, ValueError) as error:
        parser.exit(1, f'{error}\n')
    print(json.dumps({table: len(rows) for table, rows in content.items()}, ensure_ascii=False))


if __name__ == '__main__':
    main()
