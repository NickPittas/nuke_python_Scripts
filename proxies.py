import nuke
import os
import re
import difflib

# A list of alternate file extensions to try if we can't find the exact/similar match
# with the read node's current extension. (Deduplicate if needed.)
KNOWN_EXTENSIONS = [".mov", ".mxf", ".png", ".tif", ".tiff", ".jpg", ".psd", ".exr"]

def parse_file_path(fullpath):
    """
    Parse the path into directory, filename_no_ext, version, padding, and extension.
    Version: 'v' + 2..8 digits (e.g. v01, v12345678)
    Padding: naive pattern of '#' or '%0Xd'
    """
    directory, base = os.path.split(fullpath)
    filename_no_ext, extension = os.path.splitext(base)

    # Extract version
    version = ""
    version_pattern = re.compile(r'(v\d{2,8})', re.IGNORECASE)
    match_version = version_pattern.search(filename_no_ext)
    if match_version:
        version = match_version.group(1)

    # Extract frame padding
    padding = ""
    padding_pattern = re.compile(r'(#+|%0\dd)', re.IGNORECASE)
    match_padding = padding_pattern.search(filename_no_ext)
    if match_padding:
        padding = match_padding.group(1)

    return {
        'directory': directory,
        'filename_no_ext': filename_no_ext,
        'version': version,
        'padding': padding,
        'extension': extension
    }

def force_forward_slashes(path_in):
    """Convert backslashes to forward slashes."""
    return path_in.replace('\\', '/')

def recursive_file_search(root_folder, target_filename):
    """
    Recursively search 'root_folder' for exact 'target_filename'.
    Returns a list of full paths (with forward slashes).
    """
    matches = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        if target_filename in filenames:
            full_path = os.path.join(dirpath, target_filename)
            matches.append(force_forward_slashes(full_path))
    return matches

def is_similar_filename(fullname_target, fullname_candidate):
    """
    Check if the two full filenames (including extension) differ by at most
    one contiguous block of up to 2 characters in the base name,
    and share the same extension.

    Example:
      "WTFB0010_ambient_beauty_LL1804k_ACEScg_v064.1001"
      vs
      "WTFB0010_ambient_beauty_LL1808k_ACEScg_v064.1001"
      => differs by 1 character => considered similar
    """
    t_name, t_ext = os.path.splitext(fullname_target)
    c_name, c_ext = os.path.splitext(fullname_candidate)

    # Must have same extension
    if t_ext.lower() != c_ext.lower():
        return False

    return _are_names_similar(t_name, c_name)

def _are_names_similar(name_a, name_b):
    """
    Using difflib, return True if 'name_a' and 'name_b' differ by at most
    one contiguous block of up to two characters.
    """
    seq = difflib.SequenceMatcher(None, name_a, name_b)
    opcodes = seq.get_opcodes()

    mismatch_blocks = 0
    largest_block_size = 0

    for tag, i1, i2, j1, j2 in opcodes:
        if tag != 'equal':
            mismatch_blocks += 1
            changes_in_a = i2 - i1
            changes_in_b = j2 - j1
            block_size = max(changes_in_a, changes_in_b)
            if block_size > largest_block_size:
                largest_block_size = block_size

            # If we have more than one separate mismatch block, it's not "similar" by our definition
            if mismatch_blocks > 1:
                return False

    # If we only have at most one mismatch block and that block is <= 2 chars, it's "similar"
    return (mismatch_blocks <= 1 and largest_block_size <= 2)

def recursive_similar_search(root_folder, target_filename):
    """
    Return a list of paths for files that are "similar" (same extension,
    differ by <= 2 chars in one contiguous block).
    """
    matches = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for f in filenames:
            if is_similar_filename(target_filename, f):
                full_path = os.path.join(dirpath, f)
                matches.append(force_forward_slashes(full_path))
    return matches

# --- Searching with ALTERNATE EXTENSIONS ---

def search_alternate_extensions_exact(root_folder, base_name_no_ext, exclude_ext):
    """
    Look for exact matches of 'base_name_no_ext + ext' for each ext in KNOWN_EXTENSIONS,
    except the exclude_ext. Return a list of found paths with forward slashes.
    """
    found = []
    for alt_ext in KNOWN_EXTENSIONS:
        # skip if it's the same as exclude_ext
        if alt_ext.lower() == exclude_ext.lower():
            continue

        candidate_filename = base_name_no_ext + alt_ext
        matches = recursive_file_search(root_folder, candidate_filename)
        found.extend(matches)
    return list(set(found))  # deduplicate if needed

def search_alternate_extensions_similar(root_folder, base_name_no_ext, exclude_ext):
    """
    Search for "similar" matches ignoring extension:
      - The extension must be in KNOWN_EXTENSIONS (but can differ from exclude_ext).
      - The base names differ by <= 1 contiguous block of up to 2 chars.
    """
    matches = []
    for dirpath, dirnames, filenames in os.walk(root_folder):
        for f in filenames:
            # Split out candidate's extension
            c_name, c_ext = os.path.splitext(f)
            # Must be in known list
            if c_ext.lower() not in [e.lower() for e in KNOWN_EXTENSIONS]:
                continue
            # We only skip if it exactly matches exclude_ext, or maybe we allow it too?
            # Actually user says "do not restrict to the current extension," so let's allow it.

            # Compare base_name_no_ext to c_name via our "similar" definition
            if _are_names_similar(base_name_no_ext, c_name):
                full_path = os.path.join(dirpath, f)
                matches.append(force_forward_slashes(full_path))

    return list(set(matches))  # deduplicate

def ask_user_to_choose(paths_list, node_name):
    """
    If multiple paths match, show a Panel with a dropdown to let user pick one or none.
    Returns the chosen path (string) or None if canceled/skipped.
    """
    if not paths_list:
        return None

    # If there's exactly one match, just return it
    if len(paths_list) == 1:
        return paths_list[0]

    # Build a panel with a dropdown for multiple matches
    p = nuke.Panel("Multiple matches for node: {}".format(node_name))
    # Sort them (optional) so it’s easier to see
    paths_list_sorted = sorted(paths_list)
    dropdown_entries = ["<None>"] + paths_list_sorted

    p.addEnumerationPulldown("Choose a match:", " ".join(dropdown_entries))
    result = p.show()
    if not result:
        return None

    chosen = p.value("Choose a match:")
    if chosen == "<None>":
        return None

    return chosen

def main():
    """
    Main entry point:
      1) Prompt once for folder
      2) For each selected Read node:
         - exact match => pick => done
         - else similar match (same extension) => pick => done
         - else exact match with alternate known extensions => pick => done
         - else similar match ignoring extension => pick => done
         - else fail
      3) Summarize
    """
    sel_nodes = [n for n in nuke.selectedNodes() if n.Class() == "Read"]
    if not sel_nodes:
        nuke.message("No Read nodes selected.")
        return

    root_folder = nuke.getFilename("Select the folder to search in", default="")
    if not root_folder or not os.path.isdir(root_folder):
        nuke.message("Invalid folder selected. Aborting.")
        return

    root_folder = force_forward_slashes(root_folder)

    success_list = []
    fail_list = []

    for node in sel_nodes:
        file_path = node['file'].value()
        base_filename = os.path.basename(file_path)
        file_no_ext, file_ext = os.path.splitext(base_filename)

        chosen_path = None

        # Step 1) EXACT match with the same full name
        exact_matches = recursive_file_search(root_folder, base_filename)
        if exact_matches:
            chosen_path = ask_user_to_choose(exact_matches, node.name())

        # Step 2) If still not found, try "similar" with the same extension
        if not chosen_path:
            similar_matches = recursive_similar_search(root_folder, base_filename)
            if similar_matches:
                chosen_path = ask_user_to_choose(similar_matches, node.name())

        # Step 3) If still not found, try EXACT match with alternate known extensions
        if not chosen_path:
            alt_exact_matches = search_alternate_extensions_exact(
                root_folder, file_no_ext, file_ext
            )
            if alt_exact_matches:
                chosen_path = ask_user_to_choose(alt_exact_matches, node.name())

        # Step 4) If still not found, try SIMILAR ignoring extension
        if not chosen_path:
            alt_similar_matches = search_alternate_extensions_similar(
                root_folder, file_no_ext, file_ext
            )
            if alt_similar_matches:
                chosen_path = ask_user_to_choose(alt_similar_matches, node.name())

        # If we picked something
        if chosen_path:
            node['proxy'].setValue(chosen_path)
            success_list.append("{} -> {}".format(node.name(), chosen_path))
        else:
            fail_list.append(node.name())

    # Summarize
    msg = "Finished setting proxy paths.\n\n"
    if success_list:
        msg += "Successful matches:\n"
        for s in success_list:
            msg += "  {}\n".format(s)
    else:
        msg += "No successful matches.\n"

    msg += "\n"

    if fail_list:
        msg += "Failed / no match found for:\n"
        for f in fail_list:
            msg += "  {}\n".format(f)
    else:
        msg += "No failures.\n"

    nuke.message(msg)
