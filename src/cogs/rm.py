import csv
import ntpath
import re
import sys
import os

from cogs.exceptions import CogsError, RmError
from cogs.helpers import get_fields, get_sheets, validate_cogs_project


def rm(args):
    """Remove a table (TSV or CSV) from the COGS project. 
    This updates sheet.tsv and field.tsv and delete the according cached file."""
    
    validate_cogs_project()

    # Make sure the sheets exist
    sheets = get_sheets()
    
    paths = [sheet["Path"] for sheet in sheets.values()]
    if len(set(args.paths)-set(paths))>0:
        raise RmError(f"ERROR: unable to remove untracked file(s): {' '.join(set(args.paths)-set(paths))}.")

    sheets_to_remove = {title:sheet for title,sheet in sheets.items() if sheet["Path"] in args.paths}

    # Update sheet.tsv 
    
    with open(".cogs/sheet.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["ID", "Title", "Path", "Description"],
        )
        writer.writeheader()
        for title, sheet in sheets.items(): 
            if title not in sheets_to_remove.keys():
                sheet["Title"] = title
                writer.writerow(sheet)

    # Get the headers from all files and remove only the ones that are unique to the tracked file(s)

    fields_all = set()
    fields_candidates_for_removal = set()

    for title, sheet in sheets.items():
        with open(f".cogs/{title}.tsv", "r") as sheet_file:
            try:
                reader = csv.DictReader(sheet_file, delimiter="\t")
            except csv.Error as e:
                raise RmError(f"ERROR: unable to read {args.path} as a TSV\nCAUSE:{str(e)}")

            if title in sheets_to_remove.keys():
                fields_candidates_for_removal = fields_candidates_for_removal | set(reader.fieldnames)
            else:
                fields_all = fields_all | set(reader.fieldnames)
    
    fields_to_remove = fields_candidates_for_removal - fields_all
    
    original_fields = get_fields()
    
    with open(".cogs/field.tsv", "w") as f:
        writer = csv.DictWriter(
            f,
            delimiter="\t",
            lineterminator="\n",
            fieldnames=["Field", "Label", "Datatype", "Description"],
        )
        writer.writeheader()
        for field, items in original_fields.items():
            if items["Label"] not in fields_to_remove:
                items["Field"] = field
                writer.writerow(items)

    # We finally delete the cached copies

    for sheet_title in sheets_to_remove.keys():
        if "." in sheet_title or "/" in sheet_title:
            # We should probably use a proper way to make sure the file name is in .cogs
            raise RmError("ERROR: Invalid title for sheet, cannot contain . or /")
        os.remove(f".cogs/{sheet_title}.tsv")

def run(args):
    """Wrapper for rm function."""
    try:
        rm(args)
    except CogsError as e:
        print(str(e))
        sys.exit(1)