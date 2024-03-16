#!/usr/bin/env python3

"""
database.py

A series of functions to leverage the (node, edge) schema of
json-based nodes, and edges with optional json properties,
using an atomic transaction wrapper function.

"""

import json
import pathlib
from functools import lru_cache
import libsql_experimental as libsql  # type: ignore
from jinja2 import Environment, BaseLoader, select_autoescape


@lru_cache(maxsize=None)
def read_sql(sql_file):
    with open(pathlib.Path(__file__).parent.resolve() / "sql" / sql_file) as f:
        return f.read()


class SqlTemplateLoader(BaseLoader):
    def get_source(self, environment, template):
        return read_sql(template), template, True


env = Environment(loader=SqlTemplateLoader(), autoescape=select_autoescape())

clause_template = env.get_template("search-where.template")
search_template = env.get_template("search-node.template")
traverse_template = env.get_template("traverse.template")


def atomic(db_url, auth_token, cursor_exec_fn):
    connection = None
    try:
        connection = libsql.connect(database=db_url, auth_token=auth_token)
        cursor = connection.cursor()
        cursor.execute("PRAGMA foreign_keys = TRUE;")
        results = cursor_exec_fn(cursor)
        connection.commit()
    finally:
        if connection:
            pass
    return results


def initialize(db_url, auth_token, schema_file="schema.sql"):
    def _init(cursor):
        schema_sql = read_sql(schema_file)
        sql_commands = schema_sql.split(";")
        for command in sql_commands:
            if command.strip():
                cursor.execute(command)

    return atomic(db_url, auth_token, _init)


def _set_id(identifier, data):
    if identifier is not None:
        data["id"] = identifier
    return data


def _insert_node(cursor, identifier, data):
    cursor.execute(
        read_sql("insert-node.sql"), (json.dumps(_set_id(identifier, data)),)
    )


def add_node(data, identifier=None):
    def _add_node(cursor):
        _insert_node(cursor, identifier, data)

    return _add_node


def add_nodes(nodes, ids):
    def _add_nodes(cursor):
        cursor.executemany(
            read_sql("insert-node.sql"),
            [
                (x,)
                for x in map(
                    lambda node: json.dumps(_set_id(node[0], node[1])), zip(ids, nodes)
                )
            ],
        )

    return _add_nodes


def _upsert_node(cursor, identifier, data):
    current_data = find_node(identifier)(cursor)
    if not current_data:
        # no prior record exists, so regular insert
        _insert_node(cursor, identifier, data)
    else:
        # merge the current and new data and update
        updated_data = {**current_data, **data}
        cursor.execute(
            read_sql("update-node.sql"),
            (
                json.dumps(_set_id(identifier, updated_data)),
                identifier,
            ),
        )


def upsert_node(identifier, data):
    def _upsert(cursor):
        _upsert_node(cursor, identifier, data)

    return _upsert


def upsert_nodes(nodes, ids):
    def _upsert(cursor):
        for id, node in zip(ids, nodes):
            _upsert_node(cursor, id, node)

    return _upsert


def connect_nodes(source_id, target_id, properties={}):
    def _connect_nodes(cursor):
        cursor.execute(
            read_sql("insert-edge.sql"),
            (
                source_id,
                target_id,
                json.dumps(properties),
            ),
        )

    return _connect_nodes


def connect_many_nodes(sources, targets, properties):
    def _connect_nodes(cursor):
        cursor.executemany(
            read_sql("insert-edge.sql"),
            [
                (
                    x[0],
                    x[1],
                    json.dumps(x[2]),
                )
                for x in zip(sources, targets, properties)
            ],
        )

    return _connect_nodes


def remove_node(identifier):
    def _remove_node(cursor):
        cursor.execute(
            read_sql("delete-edge.sql"),
            (
                identifier,
                identifier,
            ),
        )
        cursor.execute(read_sql("delete-node.sql"), (identifier,))

    return _remove_node


def remove_nodes(identifiers):
    def _remove_node(cursor):
        cursor.executemany(
            read_sql("delete-edge.sql"),
            [
                (
                    identifier,
                    identifier,
                )
                for identifier in identifiers
            ],
        )
        cursor.executemany(
            read_sql("delete-node.sql"), [(identifier,) for identifier in identifiers]
        )

    return _remove_node


def _generate_clause(key, predicate=None, joiner=None, tree=False, tree_with_key=False):
    """Given at minimum a key in the body json, generate a query clause
    which can be bound to a corresponding value at point of execution"""

    if predicate is None:
        predicate = "="  # can also be 'LIKE', '>', '<'
    if joiner is None:
        joiner = ""  # 'AND', 'OR', 'NOT'

    if tree:
        if tree_with_key:
            return clause_template.render(
                and_or=joiner, key=key, tree=tree, predicate=predicate
            )
        else:
            return clause_template.render(and_or=joiner, tree=tree, predicate=predicate)

    return clause_template.render(
        and_or=joiner, key=key, predicate=predicate, key_value=True
    )


def _generate_query(where_clauses, result_column=None, key=None, tree=False):
    """Generate the search query, selecting either the id or the body,
    adding the json_tree function and optionally the key, as needed"""

    if result_column is None:
        result_column = "body"  # can also be 'id'

    if tree:
        if key:
            return search_template.render(
                result_column=result_column,
                tree=tree,
                key=key,
                search_clauses=where_clauses,
            )
        else:
            return search_template.render(
                result_column=result_column, tree=tree, search_clauses=where_clauses
            )

    return search_template.render(
        result_column=result_column, search_clauses=where_clauses
    )


def find_node(identifier):
    def _find_node(cursor):
        query = _generate_query([clause_template.render(id_lookup=True)])
        result = cursor.execute(query, (identifier,)).fetchone()
        return {} if not result else json.loads(result[0])

    return _find_node


def _parse_search_results(results, idx=0):
    return [json.loads(item[idx]) for item in results]


def find_nodes(where_clauses, bindings, tree_query=False, key=None):
    def _find_nodes(cursor):
        query = _generate_query(where_clauses, key=key, tree=tree_query)
        return _parse_search_results(cursor.execute(query, bindings).fetchall())

    return _find_nodes


def find_neighbors(with_bodies=False):
    return traverse_template.render(
        with_bodies=with_bodies, inbound=True, outbound=True
    )


def find_outbound_neighbors(with_bodies=False):
    return traverse_template.render(with_bodies=with_bodies, outbound=True)


def find_inbound_neighbors(with_bodies=False):
    return traverse_template.render(with_bodies=with_bodies, inbound=True)


def traverse(
    db_url, auth_token, src, tgt=None, neighbors_fn=find_neighbors, with_bodies=False
):
    def _traverse(cursor):
        path = []
        target = json.dumps(tgt)
        rows = cursor.execute(neighbors_fn(with_bodies=with_bodies), (src,)).fetchall()
        for row in rows:
            if row:
                if with_bodies:
                    identifier, obj, _ = row
                    path.append(row)
                    if identifier == target and obj == "()":
                        break
                else:
                    identifier = row[0]
                    if identifier not in path:
                        path.append(identifier)
                        if identifier == target:
                            break
        return path

    return atomic(db_url, auth_token, _traverse)


def connections_in():
    return read_sql("search-edges-inbound.sql")


def connections_out():
    return read_sql("search-edges-outbound.sql")


def get_connections_one_way(identifier, direction=connections_in):
    def _get_connections(cursor):
        return cursor.execute(direction(), (identifier,)).fetchall()

    return _get_connections


def get_connections(identifier):
    def _get_connections(cursor):
        return cursor.execute(
            read_sql("search-edges.sql"),
            (
                identifier,
                identifier,
            ),
        ).fetchall()

    return _get_connections
