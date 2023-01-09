#!/usr/local/bin/python3
"""A transpilation and minification tool for KerboScript (Extended)"""

# https://stackoverflow.com/questions/952914/how-to-make-a-flat-list-out-of-list-of-lists
flatten = lambda l: [item for sublist in l for item in sublist]


class ImportFileNotFoundError(FileNotFoundError):
    """Raised when an import statement cannot be expanded"""
    pass


class ImportNotFoundError(ImportError):
    """Raised when a from import statement fails to find specified function in given files"""
    pass


class CircularImportError(ImportError):
    """Raised when the compiler detects that it is in a circular reference import loop"""
    pass


def min_strip_comments(file_lines, *args, **kwargs):
    """Comments are only needed for weak Kerbals, remove them"""
    def comment_filter(line):
        found_comment = line.find("//")
        return found_comment >= 0, found_comment

    return_lines = []

    for line in file_lines:
        found, start = comment_filter(line)
        if not found or (found and start > 0):
            if start >= 0:
                return_lines.append(line[0:start])
            else:
                return_lines.append(line[0:])

    return return_lines


def min_remove_whitespace(file_lines, *args, **kwargs):
    """whitespace is only needed for weak Kerbals, remove them"""
    return (l.strip() for l in file_lines)


def min_remove_blank_lines(file_lines, *args, **kwargs):
    """Blank lines are only needed for weak Kerbals, remove them"""
    return (l for l in file_lines if l.strip())


def min_squash_to_oneline(file_lines, *args, **kwargs):
    """Translate list of lines to a single line"""
    return " ".join(file_lines)


def min_remove_useless_space(file_oneline):
    """Remove any extra spacing around things that don't have spacing requirements"""
    quote_chars = ['"']
    operators = [",", "*", "/", "^", "+", "-"]

    # bracketsen can also be reduced in the same way as operators are
    operators += ["{", "}", "(", ")", "[", "]"]

    # iterate over each character of the line and track if we are inside a
    # string, if not we can remove any spaces surrounding this operator
    space_locations = []
    operator_locations = []

    in_string = False
    string_strides = []
    for i, char in enumerate(file_oneline):
        # if we found a string character, increase depth or decrease depending
        # on what we were expecting to find
        #
        # this won't actually work if you have "'" or '"', but that's ok
        # because KerboScript only supports double quotes for strings
        if char in quote_chars:
            if not in_string:
                # starting a string
                string_strides.append([i])
            else:
                # closing a string
                string_strides[-1].append(i)

            in_string = not in_string
            continue

    # flatten string stride ranges into a single list so we can check operator
    # locations against that directly
    in_string_indices = flatten(range(b, e + 1) for b, e in string_strides)

    # find strides where an operator is surrounded by spaces
    space_strides = []
    for op in operator_locations:
        # don't mess with strings
        if op in in_string_indices:
            continue

        first_space, last_space = op, op

        # search forward for spaces
        for char in file_oneline[op + 1:]:
            if char != " ":
                break
            last_space += 1

        # search backward for spaces
        for char in reversed(file_oneline[0:op]):
            if char != " ":
                break
            first_space -= 1

        # if we found a surrounding space, mark it as a stride
        if first_space != op or last_space != op:
            fs = first_space if first_space is not op else op + 1
            ls = last_space if last_space is not op else op -1
            space_strides.append((fs, ls))

    # strides can be flattened to simply a list of indexes of space characters to filter out
    remove_indices = [
        x for x in
        flatten(map(lambda x: range(x[0], x[1] + 1), space_strides))
        if x not in operator_locations]

    # create a new string with all operator-space strides removed
    return "".join(c for (i, c) in enumerate(file_oneline) if i not in remove_indices)


def ksx_expand_import(file_lines, include_files, *args, **kwargs):
    """Expand @ksx import statements to full file (not @ksx from...)"""
    def parse_ksx_import_statement(line):
        import re

        import_match_re = re.compile(r"@ksx import \((.*)\).")
        re.IGNORECASE = True

        return [l.strip().replace('"', '').replace("'", '')
                for l in import_match_re.match(line).group(1).split(',')]

    def match_statement_to_include_files(import_string, include_files):
        from pathlib import Path

        acc = []
        for imp in import_string:
            import_path = Path(imp)
            for f in include_files:
                include_path = Path(f)

                # Check for stem match (without file extenstion) 
                # or full name match (with file extension)
                if (
                    imp in (include_path.stem, include_path.name) 
                    or include_path.match(str(import_path))
                    or include_path.match(str(import_path) + '.ksx')
                    or include_path.match(str(import_path) + '.ks')
                ):
                    acc.append(f)
                    break

        if acc: return acc
        raise ImportFileNotFoundError("Could not match import statement to include path")

    acc, lineno = [], 0
    for l in file_lines:
        if line_has_ksx_directive(l) and l.split()[1].lower() == "import":
            stmt = parse_ksx_import_statement(l)
            for imp_file_path in match_statement_to_include_files(stmt, include_files):
                with open(imp_file_path, 'r') as imp_file:
                    import_lines = imp_file.readlines()
                    acc = acc[:lineno] + import_lines + acc[lineno:]
                    lineno += len(import_lines)
        else:
            acc.append(l)
            lineno += 1

    return acc


def ksx_expand_from_import(file_lines, include_files, *args, **kwargs):
    """Expand @ksx from (x) import (y) statements to function inlining"""
    def parse_ksx_import_statement(line):
        import re

        import_match_re = re.compile(r"@ksx from \((.*)\) import \((.*)\).")
        re.IGNORECASE = True

        matches = import_match_re.match(line)

        if matches:
            files = [l.strip().replace('"', '').replace("'", '')
                     for l in matches.group(1).split(',')]
            functions = [l.strip().replace('"', '').replace("'", '')
                         for l in matches.group(2).split(',')]

            return files, functions
        else:
            return [], []

    def match_statement_to_include_files(import_string, include_files):
        from pathlib import Path

        acc = []
        for imp in import_string:
            import_path = Path(imp)

            for f in include_files:

                include_path = Path(f)
                # Check for stem match (without file extenstion) 
                # or full name match (with file extension)
                if (
                    imp in (include_path.stem, include_path.name) 
                    or include_path.match(str(import_path))
                    or include_path.match(str(import_path) + '.ksx')
                    or include_path.match(str(import_path) + '.ks')
                ):
                    acc.append(f)
                    break

        if acc: return acc
        raise ImportFileNotFoundError("Could not match import statement to include path")

    def function_from_file(file_lines, function_name):
        function_start_index = None
        closing_bracket_index = None
        bracket_stack = 0

        acc = []

        for lineno, line in enumerate(file_lines):
            if line.strip().startswith('function {} '.format(function_name)):
                function_start_index = lineno

            if function_start_index is not None:
                acc.append(line)
                bracket_stack += (line.count('{') - line.count('}'))

                if closing_bracket_index is None and '}' in line and bracket_stack == 0:
                    closing_bracket_index = lineno

            if closing_bracket_index is not None:
                return acc

    def function_from_files(include_files, function_name):
        for f in include_files:
            with open(f, 'r') as fp:
                fff = function_from_file(fp.readlines(), function_name)
                if fff is not None:
                    return fff

    acc, lineno = [], 0
    for l in file_lines:
        if line_has_ksx_directive(l) and l.split()[1].lower() == "from":
            files, functions = parse_ksx_import_statement(l)
            files = [match_statement_to_include_files(files, include_files)]
            for func in functions:
                func_from_files = function_from_files(include_files, func)
                if func_from_files is None:
                    msg = "Could not find {} in files {}".format(func, files)
                    raise ImportNotFoundError(msg)

                acc = acc[:lineno] + func_from_files + acc[lineno:]
                lineno += len(func_from_files)
        else:
            acc.append(l)
            lineno += 1

    return acc


def ksx_remove_lines(file_lines, *args, **kwargs):
    """Remove any no-effect @ksx directives"""
    to_remove = ['depend', 'executed']
    def line_filter(line):
        l = line.strip().lower()
        return l.startswith("@ksx") and l.split(' ')[1] in to_remove

    return (f'{l.rstrip()}\n' for l in file_lines if not line_filter(l))


def walkpath_with_action(path, action):
    from os import walk

    acc = []
    for dirpath, dirnames, filenames in walk(path):
        acc.append(action(dirpath, dirnames, filenames))

    return acc


def find_all_ks_files(root_folder):
    """Find all files with a .ks extension in a given folder"""
    def file_action(dirpath, dirnames, filenames):
        from os.path import join

        acc = []
        for filename in (f for f in filenames if (f.endswith(".ks") or f.endswith(".ksx"))):
            acc.append(join(dirpath, filename))

        return acc

    return flatten(walkpath_with_action(root_folder, file_action))


def remove_directory_if_empty(directory):
    import os
    import errno

    try:
        os.rmdir(directory)
    except OSError as e:
        if e.errno == errno.ENOTEMPTY:
            pass


def nuke_minified_directory():
    """Remove everything in the minify directory that isn't tracked by git"""
    whitelist = ["README.md"]

    def remove_if_not_whitelisted(dirpath, dirnames, filenames):
        import os

        from os.path import join

        local_whitelist = [join(dirpath, x) for x in whitelist]
        for filename in (f for f in filenames if f not in whitelist + local_whitelist):
            os.remove(join(dirpath, filename))

        remove_directory_if_empty(dirpath)

    walkpath_with_action("./minified/", remove_if_not_whitelisted)


def file_has_ksx_extension(file_path):
    import os
    return os.path.splitext(file_path)[1] == ".ksx"


def line_has_ksx_directive(file_line, specifically=None):
    return file_line.lower().strip().startswith(
        "@ksx" if specifically is None else "@ksx {}".format(specifically))


def file_has_ksx_directive(file_lines, specifically=None):
    return any(line_has_ksx_directive(l, specifically) for l in file_lines)


def hash_file_contents(file_lines):
    import hashlib
    m = hashlib.sha256()

    for line in file_lines:
        m.update(line.encode('utf-8'))

    return m.hexdigest()


RECURSION_DESCENT_LIMIT = 6


def compile_recursive_descent(file_lines, *args, **kwargs):
    """Given a file and its lines, recursively compile until no ksx statements remain"""
    visited_files = kwargs.get('visited_files', set())

    # calculate a hash of the file_lines and check if we have already compiled
    # this one
    file_hash = hash_file_contents(file_lines)

    if len(visited_files) > RECURSION_DESCENT_LIMIT:
        msg = (
            "Compiler appears to be in a circular reference loop, "
            "this is currently non-recoverable and is a known issue.\n\n"
            "See: https://github.com/LeonardMH/kos-scripts/issues/7 \n\n"
            "In the meantime check your library for files which import a "
            "file, where that file imports the original (A->B->A).\n\n"
            "You might also attempt using the 'from x import y' syntax which "
            "has slightly narrower scope."
        )

        raise CircularImportError(msg)

    if file_hash in visited_files:
        # we have already compiled this file, no need to do so again
        return ""
    else:
        # we will now compile the file, mark that it has been visited
        visited_files.add(file_hash)

    # compile and split back out to individual lines
    file_oneline = compile_single_file_lines(file_lines, *args, **kwargs)
    file_lines = file_oneline.split('\n')

    # if there are no more ksx directives in the lines compiled we are done,
    # return the stringified compile result
    if not file_has_ksx_directive(file_lines):
        return file_oneline

    # if there are still more ksx directives in the lines compiled so far, run
    # again
    kwargs['visited_files'] = visited_files
    return compile_recursive_descent(file_lines, *args, **kwargs).rstrip() + '\n'


def compile_single_file_lines(file_lines, minifier_actions,
                              transpile_only=False,
                              include_paths=None,
                              **kwargs):
    # include_paths needs to be a list of directories, if it is coming in with
    # the default value of None then there are no included dirs
    if include_paths is None:
        include_paths = []

    include_files = flatten(find_all_ks_files(p) for p in include_paths)

    def allowed_filter(func, tags):
        return not (transpile_only and "transpile-only" not in tags)

    allowed_actions = {
        k: [x for x in v if allowed_filter(*x)]
        for (k, v) in minifier_actions.items()
    }

    for action_function, action_tags in allowed_actions["linewise"]:
        file_lines = action_function(file_lines, include_files)

    if not transpile_only:
        file_oneline = min_squash_to_oneline(file_lines)
        for action_function, action_tags in allowed_actions["oneline"]:
            file_oneline = action_function(file_oneline)
    else:
        file_oneline = "".join(file_lines)

    return file_oneline


def compile_single_file(file_path, minifier_actions, **kwargs):
    import os
    import shutil
    from pathlib import Path

    file_path = os.path.abspath(file_path)
    basepath, basename = [f(file_path) for f in (os.path.dirname, os.path.basename)]
    split_path = os.path.relpath(basepath).split('/')

    if split_path[0] == "source":
        root_no_source = os.path.join(*split_path[1:])
    else:
        root_no_source = os.path.join(*split_path)

    basename = "{}.ks".format(os.path.splitext(basename)[0])

    # minified files must match directory structure of files in source, ensure
    # directories exist
    target_path = kwargs.get('target_path', None)
    if target_path:
        dest_dir = Path(target_path).parent
        dest_path = target_path
    else:
        target_dir_rel = kwargs.get('override_target', './minified')
        dest_dir = os.path.join(target_dir_rel, root_no_source)
        dest_path = os.path.join(dest_dir, basename)

    os.makedirs(dest_dir, exist_ok=True)

    with open(file_path, 'r') as rf:
        file_lines = rf.readlines()

    # ksx statement expansion needs to happen recursively, and is best handled
    # by not performing other minification actions first
    actual_transpile_only = kwargs.get('transpile_only', False)
    kwargs['transpile_only'] = True
    file_oneline = compile_recursive_descent(file_lines, minifier_actions, **kwargs)
    kwargs['transpile_only'] = actual_transpile_only

    # do a final pass with non-recursive compiler to perform minification (I
    # suppose it could use the recursive version too?)
    if not actual_transpile_only:
        file_oneline = compile_single_file_lines(
            file_oneline.split('\n'),
            minifier_actions,
            **kwargs)

    with open(dest_path, 'w') as wf:
        wf.write(file_oneline)


def main_generate_parser():
    import argparse

    parser = argparse.ArgumentParser("ksx: KerboScript Extended transpiler")

    parser.add_argument(
        "--nuke",
        action='store_true',
        help="Clean out the 'minified' directory")
    parser.add_argument(
        "--transpile-only",
        action="store_true",
        help="Only perform transpilation from .ks to .ksx, no further optimizations")
    parser.add_argument(
        "--single-file",
        help="Specify a single file to transpile")
    parser.add_argument(
        "--output",
        help="Output transpiled file to target path")
    parser.add_argument(
        "--all-files",
        action='store_true',
        help="Transpile all .ks & .ksx files in the source directory")
    parser.add_argument(
        "--include", "-I",
        action="append",
        nargs="*",
        help="Extend include path for import mechanism",
    )

    return parser


TRANSPILER_ACTIONS = {
    "linewise": [
        [ksx_expand_import, ["transpile-only"]],
        [ksx_expand_from_import, ["transpile-only"]],
        [ksx_remove_lines, ["transpile-only"]],
        [min_strip_comments, ["minify-only"]],
        [min_remove_whitespace, ["minify-only"]],
        [min_remove_blank_lines, ["minify-only"]],
    ],
    "oneline": [
        [min_remove_useless_space, ["minify-only"]],
    ],
}


def main(args):
    # the internal lists also set execution order for rules
    if args.nuke:
        nuke_minified_directory()

    if args.single_file:
        files_to_compile = [args.single_file]
    elif args.all_files:
        files_to_compile = find_all_ks_files("./source/")
    else:
        files_to_compile = []

    for single_file in files_to_compile:
        compile_single_file(
            single_file,
            TRANSPILER_ACTIONS,
            transpile_only=args.transpile_only,
            include_paths=flatten(args.include or []),
            target_path=args.output or None,
        )

def cli():
    main(main_generate_parser().parse_args())

if __name__ == '__main__':
    cli()
