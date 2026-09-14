"""Direct coverage of the comment-preserving TOML editor."""

import tomllib

import pytest

from ai_dlc.toml_edit import (
    comment_suffix,
    is_escaped,
    set_table_value,
    structural_lines,
    table_path,
    table_paths,
)


@pytest.mark.parametrize(
    "value,expected",
    [
        ("", ""),
        ('"a"', ""),
        ('"a"  # note', "  # note"),
        ('"a" \t# note # more', " \t# note # more"),
        ('"a # not a comment"', ""),
        ("'a # not a comment' # real", " # real"),
        ('"escaped \\" # still string" # real', " # real"),
        ('"trailing backslash \\\\" # real', " # real"),
        ("# whole line", "# whole line"),
        ('"unterminated # never closes', ""),
    ],
)
def test_comment_suffix_ignores_hashes_inside_quoted_strings(value, expected):
    assert comment_suffix(value) == expected


@pytest.mark.parametrize(
    "value,index,expected",
    [
        ('a"', 1, False),
        ('\\"', 1, True),
        ('\\\\"', 2, False),
        ('\\\\\\"', 3, True),
        ('"', 0, False),
    ],
)
def test_is_escaped_counts_the_run_of_preceding_backslashes(value, index, expected):
    assert is_escaped(value, index) == expected


@pytest.mark.parametrize("delimiter", ['"""', "'''"])
def test_structural_lines_mark_only_lines_that_begin_outside_multiline_strings(delimiter):
    lines = [
        "[real]\n",
        f"text = {delimiter}\n",
        "[decoy]\n",
        f"still = 'text'{delimiter}\n",
        "[after]\n",
        f"inline = {delimiter}one line{delimiter}\n",
        "[last]\n",
    ]
    assert structural_lines(lines) == [True, True, False, False, True, True, True]


def test_structural_lines_honour_escaped_basic_delimiters_and_comments():
    lines = [
        'text = """\n',
        'escaped \\""" continues\n',
        '"""\n',
        '[table] # """ inside a comment does not open a string\n',
        "key = 1\n",
    ]
    assert structural_lines(lines) == [True, False, False, True, True]
    assert structural_lines(['single = \'lit """ eral\'\n', "[next]\n"]) == [True, True]


@pytest.mark.parametrize(
    "line,expected",
    [
        ("[roles]\n", ("roles",)),
        ("  [providers.linear.statuses]  # comment\n", ("providers", "linear", "statuses")),
        ('["quoted.segment".child]\n', ("quoted.segment", "child")),
        ("[[servers]]\n", ("servers",)),
        ("key = [1, 2]\n", None),
        ("[broken\n", None),
        ("# [comment]\n", None),
    ],
)
def test_table_path_parses_headers_the_way_tomllib_does(line, expected):
    assert table_path(line) == expected


def test_table_paths_skip_headers_inside_multiline_strings():
    text = '[a]\nx = """\n[b]\n"""\n[c]\n'
    assert table_paths(text) == [("a",), None, None, None, ("c",)]


def test_set_table_value_replaces_in_place_and_keeps_comments_and_layout():
    text = (
        "# heading\n"
        "[roles]\n"
        "  tracker   =   'linear'   # chosen   \n"
        '"specs" = "openspec"\n'
        "\n"
        "[other]\n"
        "tracker = 'untouched'\n"
    )
    edited = set_table_value(text, "roles", "tracker", "github-issues")
    assert edited == (
        "# heading\n"
        "[roles]\n"
        '  tracker   =   "github-issues"   # chosen   \n'
        '"specs" = "openspec"\n'
        "\n"
        "[other]\n"
        "tracker = 'untouched'\n"
    )
    assert tomllib.loads(edited)["roles"]["tracker"] == "github-issues"
    quoted = set_table_value(text, "roles", "specs", "none")
    assert '"specs" = "none"\n' in quoted
    assert tomllib.loads(quoted)["roles"] == {"tracker": "linear", "specs": "none"}


def test_set_table_value_appends_a_missing_key_at_the_end_of_its_table():
    text = "[roles]\ntracker = 'a'\n\n[next]\nk = 1\n"
    edited = set_table_value(text, "roles", "specs", "openspec")
    # The key lands immediately before the next header; authored spacing stays.
    assert edited == "[roles]\ntracker = 'a'\n\nspecs = \"openspec\"\n[next]\nk = 1\n"
    assert tomllib.loads(edited) == {
        "roles": {"tracker": "a", "specs": "openspec"},
        "next": {"k": 1},
    }
    unterminated = set_table_value("[roles]\ntracker = 'a'", "roles", "specs", "x")
    assert tomllib.loads(unterminated) == {"roles": {"tracker": "a", "specs": "x"}}


@pytest.mark.parametrize(
    "text,expected",
    [
        ("", '[roles]\ntracker = "x"\n'),
        ("schema = 4\n", 'schema = 4\n\n[roles]\ntracker = "x"\n'),
        ("schema = 4\n\n", 'schema = 4\n\n[roles]\ntracker = "x"\n'),
        ("schema = 4", 'schema = 4\n\n[roles]\ntracker = "x"\n'),
    ],
)
def test_set_table_value_appends_a_missing_table(text, expected):
    edited = set_table_value(text, "roles", "tracker", "x")
    assert edited == expected
    assert tomllib.loads(edited)["roles"] == {"tracker": "x"}


def test_set_table_value_targets_dotted_tables_and_ignores_decoys():
    text = (
        "[providers.linear]\n"
        'team_id = "old"\n'
        'note = """\n'
        "[providers.linear.statuses]\n"
        'closed = "decoy"\n'
        '"""\n'
        "[providers.linear.statuses]\n"
        'closed = "done" # keep\n'
    )
    edited = set_table_value(text, "providers.linear.statuses", "closed", "released")
    parsed = tomllib.loads(edited)
    assert parsed["providers"]["linear"]["statuses"] == {"closed": "released"}
    assert '[providers.linear.statuses]\nclosed = "decoy"' in edited
    assert edited.endswith('closed = "released" # keep\n')
    assert (
        tomllib.loads(set_table_value(edited, "providers.linear", "team_id", "new"))["providers"][
            "linear"
        ]["team_id"]
        == "new"
    )


def test_set_table_value_encodes_the_value_as_a_basic_string():
    edited = set_table_value("", "t", "k", 'quote " backslash \\ unicode é')
    assert tomllib.loads(edited)["t"]["k"] == 'quote " backslash \\ unicode é'
    assert "é" in edited
