#!/usr/bin/env python3
"""cryo-handoff: find grid inventory PDFs in Dropbox by date."""
import os
import re
import shutil
import subprocess
import sys
from datetime import date, datetime, timedelta
from itertools import product
from pathlib import Path

TARGET_SUBPATH = Path("Grid_inventory_and_data_collection_sheets") / "User_Directories"
DROPBOX_FOLDER_NAME = "Harvard Cryo-EM Center"
OUTPUT_ROOT = Path(__file__).resolve().parent / "output"

def use_color():
    return sys.stdout.isatty() and not bool(os.environ.get("NO_COLOR"))

def colorize(text, code):
    return f"\033[{code}m{text}\033[0m" if use_color() else text

def find_dropbox_root():
    p = Path.home() / "Dropbox" / DROPBOX_FOLDER_NAME
    if p.is_dir(): return p
    try:
        r = subprocess.run(["mdfind", "-name", DROPBOX_FOLDER_NAME], capture_output=True, text=True, timeout=15)
        for x in r.stdout.splitlines():
            p = Path(x.strip())
            if p.is_dir() and p.name == DROPBOX_FOLDER_NAME: return p
    except (subprocess.SubprocessError, FileNotFoundError): pass
    return None

def prompt_for_path():
    while True:
        e = input("User_Directories path: ").strip()
        if not e:
            print("No directory entered. Exiting.")
            return None
        p = Path(e).expanduser()
        if p.is_dir():
            return p
        print("That directory was not found. Please check the path and try again.")

def _spotlight_user_directories():
    suffix = (Path(DROPBOX_FOLDER_NAME) / TARGET_SUBPATH).as_posix(); candidates = []
    try:
        r = subprocess.run(["mdfind", "-name", "User_Directories"], capture_output=True, text=True, timeout=15)
        for x in r.stdout.splitlines():
            p = Path(x.strip()).expanduser(); text = str(p.resolve()).replace("\\", "/")
            if p.is_dir() and re.search(r"/Dropbox(?: \\([^/]+\\))?/" + re.escape(suffix) + r"$", text): candidates.append(p.resolve())
    except (subprocess.SubprocessError, FileNotFoundError): pass
    return sorted(candidates, key=lambda p: str(p).casefold())[0] if candidates else None

def locate_search_root():
    conventional = Path.home() / "Dropbox" / DROPBOX_FOLDER_NAME / TARGET_SUBPATH
    if conventional.is_dir():
        print("Default directory ~/Dropbox/Harvard Cryo-EM Center/Grid_inventory_and_data_collection_sheets/User_Directories found; searching within it."); return conventional
    print("Default directory ~/Dropbox/Harvard Cryo-EM Center/Grid_inventory_and_data_collection_sheets/User_Directories not found; searching for Dropbox directory.")
    root = find_dropbox_root()
    if root is not None:
        search_root = root / TARGET_SUBPATH
        if search_root.is_dir(): print(f'"{DROPBOX_FOLDER_NAME}" Dropbox location: FOUND'); return search_root
    search_root = _spotlight_user_directories()
    if search_root is not None: print(f"User_Directories found by Spotlight: {search_root}"); return search_root
    print(f'"{DROPBOX_FOLDER_NAME}" Dropbox location: NOT FOUND')
    print("Could not find the expected User_Directories folder automatically.")
    print("Paste the full path to User_Directories, or press Enter to quit.")
    search_root = prompt_for_path()
    if search_root is None: sys.exit(1)
    return search_root

def prompt_for_date():
    while True:
        value = input("Enter date to search (YYYYMMDD), or press Enter for today: ").strip()
        if not value:
            return date.today()
        if re.fullmatch(r"[0-9]{8}", value):
            try:
                return datetime.strptime(value, "%Y%m%d").date()
            except ValueError:
                pass
        print("Invalid date format. Please enter YYYYMMDD (for example, 20260909), or press Enter for today.")

def prompt_for_lookback():
    prompt = "Include earlier dates? Enter number of days to look back\n(Enter/0 = only the date above, 1 = also include 1 day before, etc.): "
    while True:
        value = input(prompt).strip()
        if not value:
            return 0
        if re.fullmatch(r"[0-9]+", value):
            return int(value)
        print("Invalid number of days. Please enter a whole number 0 or greater.")

def _sort_patterns(patterns): return sorted((x for x in patterns if x), key=lambda x: (-len(x), x))
def generate_year_patterns(d):
    years=(f"{d.year:04d}",f"{d.year%100:02d}"); months=(f"{d.month:02d}",str(d.month)); days=(f"{d.day:02d}",str(d.day)); seps=("-","_","."," ",""); patterns=set()
    for year,month,day,sep1,sep2 in product(years,months,days,seps,seps): patterns.update((f"{year}{sep1}{month}{sep2}{day}",f"{month}{sep1}{day}{sep2}{year}"))
    for year,month,day,sep1,sep2 in product(years,(d.strftime("%b"),d.strftime("%B")),days,seps,seps): patterns.update((f"{year}{sep1}{month}{sep2}{day}",f"{month}{sep1}{day}{sep2}{year}",f"{day}{sep1}{month}{sep2}{year}"))
    return _sort_patterns(patterns)
def generate_no_year_patterns(d):
    months=(f"{d.month:02d}",str(d.month)); days=(f"{d.day:02d}",str(d.day)); seps=("-","_","."," ",""); patterns=set()
    for month,day,sep in product(months,days,seps): patterns.add(f"{month}{sep}{day}")
    for month,day,sep in product((d.strftime("%b"),d.strftime("%B")),days,seps): patterns.update((f"{month}{sep}{day}",f"{day}{sep}{month}"))
    return _sort_patterns(patterns)
def generate_date_patterns(d): return _sort_patterns(set(generate_year_patterns(d)) | set(generate_no_year_patterns(d)))
def _compile_patterns(patterns,numeric_boundaries=False):
    expression="(?:"+"|".join(re.escape(p) for p in patterns)+")"
    if numeric_boundaries: expression=r"(?<![0-9])"+expression+r"(?![0-9])"
    return re.compile(expression,re.IGNORECASE)
def build_matcher(d): return re.compile(r"(?:"+"|".join(re.escape(p) for p in generate_year_patterns(d))+r"|(?<![0-9])(?:"+"|".join(re.escape(p) for p in generate_no_year_patterns(d))+r")(?![0-9]))",re.IGNORECASE)
_MONTH_RE=r"(?:jan(?:uary)?|feb(?:ruary)?|mar(?:ch)?|apr(?:il)?|may|jun(?:e)?|jul(?:y)?|aug(?:ust)?|sep(?:t(?:ember)?)?|oct(?:ober)?|nov(?:ember)?|dec(?:ember)?)"; _NUM_MONTH_RE=r"(?:0?[1-9]|1[0-2])"; _DAY_RE=r"(?:0?[1-9]|[12][0-9]|3[01])"; _YEAR_RE=r"(?:[0-9]{4}|[0-9]{2})"; _SEP_RE=r"[-_. ,]"
YEAR_QUALIFIED_DATE_RE=re.compile(rf"(?:[0-9]{{8}}|[0-9]{{6}}|{_YEAR_RE}{_SEP_RE}{_NUM_MONTH_RE}{_SEP_RE}{_DAY_RE}|{_NUM_MONTH_RE}{_SEP_RE}{_DAY_RE}{_SEP_RE}{_YEAR_RE}|{_YEAR_RE}(?:[-_. ,]*){_MONTH_RE}(?:[-_. ,]*){_DAY_RE}|{_MONTH_RE}(?:[-_. ,]*){_DAY_RE}(?:[-_. ,]*){_YEAR_RE}|{_DAY_RE}(?:[-_. ,]*){_MONTH_RE}(?:[-_. ,]*){_YEAR_RE})",re.IGNORECASE)
def search_pdfs_for_date(root,d):
    year_matcher=_compile_patterns(generate_year_patterns(d)); no_year_matcher=_compile_patterns(generate_no_year_patterns(d),numeric_boundaries=True); matches=[]
    for p in sorted((x for x in root.rglob("*") if x.is_file() and x.suffix.lower()==".pdf"),key=lambda x:str(x).casefold()):
        if year_matcher.search(p.name) or (not YEAR_QUALIFIED_DATE_RE.search(p.name) and no_year_matcher.search(p.name)): matches.append(p)
    return matches
def relative_display_path(root,path):
    try: relative=path.parent.relative_to(root)
    except ValueError: relative=path.parent
    return str(relative) if str(relative)!="." else "(root)"
def build_indexed_results(results):
    indexed=[]; i=1
    for d,paths in results.items():
        for p in paths: indexed.append((i,d,p)); i+=1
    return indexed
def print_indexed_table(root,indexed,dates_in_order):
    by_date={}
    for i,d,p in indexed: by_date.setdefault(d,[]).append((i,p))
    for d in dates_in_order:
        rows=by_date.get(d,[]); print(f"\nBelow are possible pdf inventory files for {d.strftime('%Y/%b/%d')}:")
        if not rows: print("  (no matches found)"); continue
        number_width=max([len(str(i)) for i,_ in rows]+[len("#")]); name_width=max([len(p.name) for _,p in rows]+[len("File name")]); print(f"{'#':<{number_width}}  {'File name':<{name_width}}  Directory")
        for i,p in rows:
            name=f"{p.name:<{name_width}}"; directory=relative_display_path(root,p); print(f"{i:<{number_width}}  {colorize(name,'96')}  {colorize(directory,'33')}")
def try_materialize(path):
    try:
        with open(path,"rb") as f:f.read(4096)
        return True
    except OSError as e: print(f"  [WARNING] Could not read {path.name}: {e}"); return False
def copy_selected(indexed,output_root):
    for _,d,p in indexed:
        try_materialize(p); folder=output_root/d.strftime("%Y_%b_%d"); folder.mkdir(parents=True,exist_ok=True); dest=folder/p.name
        try: shutil.copy2(p,dest); print(f"  [OK] {p.name} -> {dest}")
        except OSError as e: print(f"  [FAILED] {p.name}: {e}")
def interactive_review(root,results,output_root):
    dates_in_order=list(results); original=build_indexed_results(results); print_indexed_table(root,original,dates_in_order)
    if not original: print("\nNo files found. Exiting."); return
    current=original
    while True:
        choice=input("\nPress [c] to copy these files, [q] to quit, [s] to select/exclude: ").strip().lower()
        if choice=="c": print("\nCopying files..."); copy_selected(current,output_root); print(f"\nDone. {len(current)} file(s) copied."); return
        if choice=="q": print("Exiting without copying."); return
        if choice=="s":
            print("\nFull list:"); print_indexed_table(root,original,dates_in_order)
            raw=input("\nEnter numbers to exclude (comma-separated), or press Enter to keep all: ").strip()
            tokens = [x.strip() for x in raw.split(",") if x.strip()]
            if any(not re.fullmatch(r"[0-9]+", token) for token in tokens):
                print("Invalid exclusion list. Enter comma-separated file numbers, for example: 1, 3, 5.")
                continue
            excluded={int(token) for token in tokens}
            current=[(i,d,p) for i,d,p in original if i not in excluded]; print("\nUpdated list:"); print_indexed_table(root,current,dates_in_order)
        else: print("Invalid choice. Enter c to copy, q to quit, or s to select/exclude.")
def main():
    target=prompt_for_date()
    lookback=prompt_for_lookback()
    search_root=locate_search_root(); dates=[target-timedelta(days=i) for i in range(lookback+1)]; interactive_review(search_root,{d:search_pdfs_for_date(search_root,d) for d in dates},OUTPUT_ROOT)
if __name__=="__main__":main()
